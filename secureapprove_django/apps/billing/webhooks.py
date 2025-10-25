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
import mercadopago

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
            if Payment.objects.filter(mercadopago_payment_id=str(payment_id)).exists():
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
            
            # 3. Create tenant if needed
            if not user.tenant:
                tenant_slug = f"{email.split('@')[0]}-{user.id}".lower().replace('.', '-')[:50]
                tenant = Tenant.objects.create(
                    name=f"{user.name}'s Organization",
                    slug=tenant_slug,
                    description=f"Organization for {user.email}",
                    owner=user,
                    is_active=True
                )
                user.tenant = tenant
                user.role = 'tenant_admin'
                user.save()
                logger.info(f"Created tenant: {tenant.slug}")
            else:
                tenant = user.tenant
                logger.info(f"User already has tenant: {tenant.slug}")
            
            # 4. Create or update subscription
            subscription, sub_created = Subscription.objects.get_or_create(
                tenant=tenant,
                defaults={
                    'plan': plan,
                    'status': 'active',
                    'billing_cycle': 'monthly',
                }
            )
            
            if not sub_created:
                subscription.status = 'active'
                subscription.plan = plan
                subscription.save()
            
            logger.info(f"{'Created' if sub_created else 'Updated'} subscription")
            
            # 5. Create payment record
            payment_record = Payment.objects.create(
                subscription=subscription,
                mercadopago_payment_id=str(payment_data.get('id')),
                external_reference=payment_data.get('external_reference', ''),
                amount=payment_data.get('transaction_amount', 0),
                currency='USD',
                status='completed',
                payment_method=payment_data.get('payment_method_id', ''),
                metadata=payment_data
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
