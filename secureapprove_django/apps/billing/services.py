# ==================================================
# SecureApprove Django - Billing Services
# ==================================================

import mercadopago
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from .models import Plan, Subscription, Payment, UsageMetrics, Invoice

logger = logging.getLogger(__name__)

class MercadoPagoService:
    """Service for MercadoPago API integration"""
    
    def __init__(self):
        # Lazy initialization - only create SDK when needed
        self._sdk = None
    
    @property
    def sdk(self):
        """Lazy initialization of MercadoPago SDK"""
        if self._sdk is None:
            try:
                import mercadopago
                access_token = getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', 'TEST-demo-token')
                self._sdk = mercadopago.SDK(access_token)
            except Exception as e:
                logger.warning(f"Could not initialize MercadoPago SDK: {e}")
                # Return a mock SDK for testing
                self._sdk = None
        return self._sdk
    
    def create_preference(self, subscription, billing_cycle='monthly'):
        """Create a payment preference for subscription"""
        
        if not self.sdk:
            # Mock response for testing
            return {
                'id': f'mock-preference-{subscription.id}',
                'external_reference': str(subscription.id),
                'init_point': 'https://mock-payment-url.com'
            }
        
        plan = subscription.plan
        amount = plan.monthly_price if billing_cycle == 'monthly' else plan.yearly_price_calculated
        
        preference_data = {
            "items": [{
                "title": f"{plan.display_name} - {billing_cycle.title()} Subscription",
                "description": plan.description,
                "category_id": "services",
                "quantity": 1,
                "unit_price": float(amount),
                "currency_id": "USD"
            }],
            "payer": {
                "name": subscription.tenant.name,
                "email": subscription.tenant.admin_email,
            },
            "external_reference": str(subscription.id),
            "notification_url": f"{settings.SITE_URL}/api/billing/webhooks/mercadopago/",
            "back_urls": {
                "success": f"{settings.SITE_URL}/billing/success/",
                "failure": f"{settings.SITE_URL}/billing/failure/",
                "pending": f"{settings.SITE_URL}/billing/pending/"
            },
            "auto_return": "approved",
            "payment_methods": {
                "excluded_payment_types": [],
                "installments": 12 if billing_cycle == 'yearly' else 1
            }
        }
        
        try:
            preference_response = self.sdk.preference().create(preference_data)
            
            if preference_response["status"] == 201:
                preference_id = preference_response["response"]["id"]
                
                # Create payment record
                payment = Payment.objects.create(
                    subscription=subscription,
                    amount=amount,
                    currency='USD',
                    status='pending',
                    mp_preference_id=preference_id,
                    external_reference=str(subscription.id)
                )
                
                return {
                    'success': True,
                    'preference_id': preference_id,
                    'payment_id': payment.id,
                    'init_point': preference_response["response"]["init_point"]
                }
            else:
                logger.error(f"MercadoPago preference creation failed: {preference_response}")
                return {
                    'success': False,
                    'error': 'Failed to create payment preference'
                }
                
        except Exception as e:
            logger.error(f"MercadoPago error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_payment_info(self, payment_id):
        """Get payment information from MercadoPago"""
        try:
            payment_response = self.sdk.payment().get(payment_id)
            
            if payment_response["status"] == 200:
                return {
                    'success': True,
                    'payment': payment_response["response"]
                }
            else:
                return {
                    'success': False,
                    'error': 'Payment not found'
                }
                
        except Exception as e:
            logger.error(f"MercadoPago get_payment error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_webhook(self, webhook_data):
        """Process MercadoPago webhook notification"""
        try:
            if webhook_data.get('type') == 'payment':
                payment_id = webhook_data.get('data', {}).get('id')
                
                if not payment_id:
                    return {'success': False, 'error': 'No payment ID in webhook'}
                
                # Get payment info from MercadoPago
                payment_info = self.get_payment_info(payment_id)
                
                if not payment_info['success']:
                    return payment_info
                
                mp_payment = payment_info['payment']
                external_reference = mp_payment.get('external_reference')
                
                if not external_reference:
                    return {'success': False, 'error': 'No external reference'}
                
                # Find subscription
                try:
                    subscription = Subscription.objects.get(id=external_reference)
                except Subscription.DoesNotExist:
                    return {'success': False, 'error': 'Subscription not found'}
                
                # Update payment status
                payment = Payment.objects.filter(
                    subscription=subscription,
                    mp_preference_id=mp_payment.get('preference_id')
                ).first()
                
                if payment:
                    payment.mp_payment_id = payment_id
                    payment.status = self._map_mp_status(mp_payment.get('status'))
                    payment.payment_method = mp_payment.get('payment_method_id', '')
                    payment.metadata = mp_payment
                    
                    if payment.status == 'approved':
                        payment.paid_at = timezone.now()
                        
                        # Update subscription
                        self._activate_subscription(subscription, payment)
                    
                    payment.save()
                    
                    return {'success': True, 'payment_updated': True}
                
                return {'success': True, 'payment_not_found': True}
            
            return {'success': True, 'not_payment_webhook': True}
            
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _map_mp_status(self, mp_status):
        """Map MercadoPago status to our payment status"""
        status_map = {
            'approved': 'approved',
            'pending': 'pending',
            'rejected': 'rejected',
            'cancelled': 'cancelled',
            'refunded': 'refunded'
        }
        return status_map.get(mp_status, 'pending')
    
    def _activate_subscription(self, subscription, payment):
        """Activate subscription after successful payment"""
        now = timezone.now()
        
        # Calculate next billing period
        if subscription.billing_cycle == 'monthly':
            next_period = now + timedelta(days=30)
        else:  # yearly
            next_period = now + timedelta(days=365)
        
        subscription.status = 'active'
        subscription.current_period_start = now
        subscription.current_period_end = next_period
        subscription.trial_end = None
        subscription.save()
        
        # Create invoice
        self._create_invoice(subscription, payment)
    
    def _create_invoice(self, subscription, payment):
        """Create invoice for successful payment"""
        
        subtotal = payment.amount
        tax_amount = Decimal('0.00')  # Add tax calculation if needed
        total_amount = subtotal + tax_amount
        
        invoice = Invoice.objects.create(
            subscription=subscription,
            payment=payment,
            status='paid',
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            issue_date=timezone.now().date(),
            due_date=timezone.now().date(),
            paid_date=timezone.now().date(),
            period_start=subscription.current_period_start.date(),
            period_end=subscription.current_period_end.date()
        )
        
        return invoice

class BillingService:
    """Main billing service"""
    
    def __init__(self):
        # Lazy initialization of MercadoPago service
        self._mp_service = None
    
    @property 
    def mp_service(self):
        """Lazy initialization of MercadoPago service"""
        if self._mp_service is None:
            self._mp_service = MercadoPagoService()
        return self._mp_service
    
    def create_subscription(self, tenant, plan_name, billing_cycle='monthly'):
        """Create a new subscription for a tenant"""
        
        try:
            plan = Plan.objects.get(name=plan_name, is_active=True)
        except Plan.DoesNotExist:
            return {'success': False, 'error': 'Plan not found'}
        
        # Check if tenant already has a subscription
        if hasattr(tenant, 'subscription'):
            return {'success': False, 'error': 'Tenant already has a subscription'}
        
        # Create subscription
        now = timezone.now()
        trial_end = now + timedelta(days=14)  # 14 day trial
        
        subscription = Subscription.objects.create(
            tenant=tenant,
            plan=plan,
            billing_cycle=billing_cycle,
            status='trialing',
            current_period_start=now,
            current_period_end=trial_end,
            trial_end=trial_end
        )
        
        return {'success': True, 'subscription': subscription}
    
    def change_plan(self, subscription, new_plan_name):
        """Change subscription plan"""
        
        try:
            new_plan = Plan.objects.get(name=new_plan_name, is_active=True)
        except Plan.DoesNotExist:
            return {'success': False, 'error': 'Plan not found'}
        
        old_plan = subscription.plan
        subscription.plan = new_plan
        subscription.save()
        
        # If upgrading, prorate and charge immediately
        if new_plan.monthly_price > old_plan.monthly_price:
            # Calculate prorated amount
            days_remaining = (subscription.current_period_end - timezone.now()).days
            daily_rate_old = old_plan.monthly_price / 30
            daily_rate_new = new_plan.monthly_price / 30
            prorated_amount = (daily_rate_new - daily_rate_old) * days_remaining
            
            if prorated_amount > 0:
                # Create immediate charge for upgrade
                preference = self.mp_service.create_preference(subscription, 'prorated')
                return {'success': True, 'upgrade_charge': preference}
        
        return {'success': True, 'plan_changed': True}
    
    def cancel_subscription(self, subscription, reason=''):
        """Cancel a subscription"""
        
        subscription.status = 'cancelled'
        subscription.cancelled_at = timezone.now()
        subscription.save()
        
        # Log cancellation reason
        logger.info(f"Subscription {subscription.id} cancelled: {reason}")
        
        return {'success': True}
    
    def get_usage_stats(self, subscription, year=None, month=None):
        """Get usage statistics for a subscription"""
        
        if not year or not month:
            now = timezone.now()
            year, month = now.year, now.month
        
        metrics, created = UsageMetrics.objects.get_or_create(
            subscription=subscription,
            year=year,
            month=month,
            defaults={
                'requests_created': 0,
                'requests_approved': 0,
                'requests_rejected': 0,
                'api_calls': 0,
                'active_users': 0,
                'total_users': 0
            }
        )
        
        if created:
            # Calculate actual metrics
            self._update_usage_metrics(metrics)
        
        return metrics
    
    def _update_usage_metrics(self, metrics):
        """Update usage metrics with actual data"""
        
        from apps.requests.models import ApprovalRequest
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        subscription = metrics.subscription
        tenant = subscription.tenant
        
        # Date range for the month
        start_date = datetime(metrics.year, metrics.month, 1)
        if metrics.month == 12:
            end_date = datetime(metrics.year + 1, 1, 1)
        else:
            end_date = datetime(metrics.year, metrics.month + 1, 1)
        
        # Request metrics
        requests_qs = ApprovalRequest.objects.filter(
            tenant=tenant,
            created_at__gte=start_date,
            created_at__lt=end_date
        )
        
        metrics.requests_created = requests_qs.count()
        metrics.requests_approved = requests_qs.filter(status='approved').count()
        metrics.requests_rejected = requests_qs.filter(status='rejected').count()
        
        # User metrics
        metrics.total_users = User.objects.filter(tenant=tenant).count()
        metrics.active_users = User.objects.filter(
            tenant=tenant,
            last_login__gte=start_date,
            last_login__lt=end_date
        ).count()
        
        metrics.save()
    
    def check_limits(self, subscription):
        """Check if subscription is within plan limits"""
        
        plan = subscription.plan
        tenant = subscription.tenant
        
        # Check user limits
        if not plan.can_create_user(tenant):
            return {
                'within_limits': False,
                'limit_type': 'users',
                'current': tenant.users.count(),
                'limit': plan.max_users
            }
        
        # Check approver limits
        if not plan.can_create_approver(tenant):
            return {
                'within_limits': False,
                'limit_type': 'approvers',
                'current': tenant.users.filter(role__in=['admin', 'approver']).count(),
                'limit': plan.max_approvers
            }
        
        # Check request limits
        if not plan.can_create_request(tenant):
            now = timezone.now()
            from apps.requests.models import ApprovalRequest
            current_requests = ApprovalRequest.objects.filter(
                tenant=tenant,
                created_at__year=now.year,
                created_at__month=now.month
            ).count()
            
            return {
                'within_limits': False,
                'limit_type': 'requests',
                'current': current_requests,
                'limit': plan.max_requests_per_month
            }
        
        return {'within_limits': True}

# Service instances - Lazy initialization to avoid startup errors
# billing_service = BillingService()
# mp_service = MercadoPagoService()

def get_billing_service():
    """Get billing service instance (lazy initialization)"""
    return BillingService()

def get_mp_service():
    """Get MercadoPago service instance (lazy initialization)"""
    return MercadoPagoService()