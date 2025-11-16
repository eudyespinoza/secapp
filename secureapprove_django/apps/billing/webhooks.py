# billing/webhooks.py
import json
import logging
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import mercadopago

from decimal import Decimal

from apps.tenants.models import Tenant
from apps.billing.models import Plan, Subscription, Payment
from apps.billing.services import BillingService

logger = logging.getLogger(__name__)
User = get_user_model()

@method_decorator(csrf_exempt, name='dispatch')
class MercadoPagoWebhookView(View):
    """
    Handle MercadoPago webhook notifications for NEW USER SUBSCRIPTIONS
    
    This webhook handles the complete flow:
    1. User pays for subscription (no account yet)
    2. MercadoPago sends webhook
    3. System creates: User → Tenant → Subscription
    4. User can login and setup WebAuthn
    """
    
    def post(self, request):
        try:
            webhook_data = json.loads(request.body)
            
            action = webhook_data.get('action')
            data = webhook_data.get('data', {})
            payment_id = data.get('id')
            
            if not payment_id:
                logger.warning("Webhook received without payment ID")
                return HttpResponseBadRequest("Missing payment ID")
            
            if action in ['payment.created', 'payment.updated']:
                return self._process_payment(payment_id)
            else:
                logger.info(f"Unhandled webhook action: {action}")
                return HttpResponse("OK")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return HttpResponseBadRequest("Invalid JSON")
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return HttpResponseBadRequest("Processing error")
    
    def _process_payment(self, payment_id):
        """Process payment and create complete account setup"""
        try:
            mp = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
            payment_response = mp.payment().get(payment_id)
            
            if payment_response["status"] != 200:
                logger.error(f"Failed to fetch payment {payment_id}")
                return HttpResponseBadRequest("Payment not found")
            
            payment_data = payment_response["response"]
            payment_status = payment_data.get('status')
            metadata = payment_data.get('metadata', {})
            payer_email = metadata.get('customer_email') or payment_data.get('payer', {}).get('email')
            plan_name = metadata.get('plan_name')
            
            logger.info(f"Payment {payment_id}: status={payment_status}, email={payer_email}, plan={plan_name}")
            
            if not payer_email or not plan_name:
                logger.error(f"Payment {payment_id} missing email or plan")
                return HttpResponseBadRequest("Missing required metadata")
            
            if payment_status != 'approved':
                logger.info(f"Payment {payment_id} status is {payment_status}, skipping")
                return HttpResponse("OK")
            
            # Check if already processed
            if Payment.objects.filter(mp_payment_id=str(payment_id)).exists():
                logger.info(f"Payment {payment_id} already processed")
                return HttpResponse("OK")
            
            # Create complete account
            return self._create_account_from_payment(payment_data, payer_email, plan_name)
            
        except Exception as e:
            logger.error(f"Error processing payment {payment_id}: {str(e)}", exc_info=True)
            return HttpResponse("OK")  # Return OK to avoid MP retries
    
    def _create_account_from_payment(self, payment_data, email, plan_name):
        """Create user, tenant, and subscription from approved payment"""
        try:
            # 1. Get or create user
            user, user_created = User.objects.get_or_create(
                email=email.lower(),
                defaults={
                    'username': email.lower(),
                    'name': email.split('@')[0],
                    'role': 'tenant_admin',
                    'is_active': True,
                }
            )
            logger.info(f"{'Created' if user_created else 'Found'} user: {user.email}")
            
            # 2. Get plan
            try:
                plan = Plan.objects.get(name=plan_name, is_active=True)
            except Plan.DoesNotExist:
                logger.error(f"Plan not found: {plan_name}")
                return HttpResponseBadRequest("Plan not found")
            
            # 3. Create tenant if needed, using current Tenant model fields
            if not user.tenant:
                base_key = email.split('@')[0].lower()
                base_key = ''.join(ch for ch in base_key if ch.isalnum() or ch == '-')
                if not base_key:
                    base_key = f"tenant-{user.id}".lower()

                key = base_key
                suffix = 1
                while Tenant.objects.filter(key=key).exists():
                    suffix += 1
                    key = f"{base_key}-{suffix}"

                # Seats from metadata (fallback 2)
                metadata = payment_data.get('metadata', {}) or {}
                seats_val = metadata.get('seats') or 2
                try:
                    seats = int(seats_val)
                except (TypeError, ValueError):
                    seats = 2
                if seats < 2:
                    seats = 2

                # Approver limit based on plan
                if plan.name == 'starter':
                    approver_limit = 2
                elif plan.name == 'growth':
                    approver_limit = 6
                else:
                    # scale or other plans -> treat as "unlimited" approvers
                    approver_limit = 0

                tenant = Tenant.objects.create(
                    key=key,
                    name=f"{user.name or key}",
                    plan_id=plan.name,
                    seats=seats,
                    approver_limit=approver_limit,
                    is_active=True,
                    status='active',
                    billing={
                        'provider': 'mercadopago',
                        'customerId': str(payment_data.get('payer', {}).get('id', '')),
                        'paymentId': str(payment_data.get('id', '')),
                    },
                    metadata={},
                )
                user.tenant = tenant
                user.role = 'tenant_admin'
                user.save(update_fields=['tenant', 'role'])
                logger.info(f"Created tenant: {tenant.key}")
            else:
                tenant = user.tenant
                logger.info(f"User already has tenant: {tenant.key}")
            
            # 4. Create or update subscription using BillingService helpers
            billing_service = BillingService()
            subscription, created = Subscription.objects.get_or_create(
                tenant=tenant,
                defaults={
                    'plan': plan,
                    'status': 'trialing',
                    'billing_cycle': 'monthly',
                    'current_period_start': timezone.now(),
                    'current_period_end': timezone.now() + timedelta(days=30),
                },
            )

            # Ensure plan and status reflect active paid subscription
            subscription.plan = plan
            subscription.status = 'active'
            subscription.trial_end = None
            subscription.save()

            logger.info(f"{'Created' if created else 'Updated'} subscription for tenant {tenant.key}")

            # 5. Create payment record
            amount = payment_data.get('transaction_amount', 0) or 0
            try:
                amount_decimal = Decimal(str(amount))
            except Exception:
                amount_decimal = Decimal("0.00")

            payment_record = Payment.objects.create(
                subscription=subscription,
                mp_payment_id=str(payment_data.get('id')),
                external_reference=payment_data.get('external_reference', ''),
                amount=amount_decimal,
                currency=payment_data.get('currency_id', 'USD') or 'USD',
                status='approved',
                payment_method=payment_data.get('payment_method_id', ''),
                metadata=payment_data,
            )
            
            logger.info(f"✅ Complete account created for {user.email}")
            self._send_welcome_email(user, subscription, tenant)
            
            return HttpResponse("OK")
            
        except Exception as e:
            logger.error(f"Error creating account: {str(e)}", exc_info=True)
            return HttpResponse("OK")
    
    def _send_welcome_email(self, user, subscription, tenant):
        """Send welcome email"""
        logger.info(f"TODO: Send welcome email to {user.email} for tenant {tenant.slug}")


@csrf_exempt
@require_http_methods(["POST"])
def mercadopago_webhook(request):
    """Function-based webhook handler"""
    webhook_view = MercadoPagoWebhookView()
    return webhook_view.post(request)
