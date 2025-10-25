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

from apps.tenants.services import TenantService
from apps.billing.models import Plan, Subscription, Payment
from apps.billing.services import BillingService

logger = logging.getLogger(__name__)
User = get_user_model()

@method_decorator(csrf_exempt, name='dispatch')
class MercadoPagoWebhookView(View):
    """
    Handle MercadoPago webhook notifications
    
    This webhook is critical for the tenant creation flow:
    1. User registers (no tenant created)
    2. User subscribes to plan (subscription created, pending)
    3. Payment is processed by MercadoPago
    4. Webhook receives notification → creates tenant
    5. User can now access their multi-tenant account
    """
    
    def post(self, request):
        try:
            # Parse webhook data
            webhook_data = json.loads(request.body)
            
            # Validate webhook signature if configured
            if hasattr(settings, 'MERCADOPAGO_WEBHOOK_SECRET'):
                if not self._validate_signature(request, webhook_data):
                    logger.warning("Invalid webhook signature")
                    return HttpResponseBadRequest("Invalid signature")
            
            # Extract payment information
            action = webhook_data.get('action')
            data = webhook_data.get('data', {})
            payment_id = data.get('id')
            
            if not payment_id:
                logger.warning("Webhook received without payment ID")
                return HttpResponseBadRequest("Missing payment ID")
            
            # Process based on action type
            if action == 'payment.created':
                return self._handle_payment_created(payment_id)
            elif action == 'payment.updated':
                return self._handle_payment_updated(payment_id)
            else:
                logger.info(f"Unhandled webhook action: {action}")
                return HttpResponse("OK")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook payload")
            return HttpResponseBadRequest("Invalid JSON")
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return HttpResponseBadRequest("Processing error")
    
    def _validate_signature(self, request, webhook_data):
        """Validate MercadoPago webhook signature"""
        # Implementation depends on MercadoPago's signature verification
        # This is a placeholder - actual implementation needed
        return True
    
    def _handle_payment_created(self, payment_id):
        """Handle new payment creation"""
        logger.info(f"Processing payment creation: {payment_id}")
        return self._process_payment(payment_id)
    
    def _handle_payment_updated(self, payment_id):
        """Handle payment status updates"""
        logger.info(f"Processing payment update: {payment_id}")
        return self._process_payment(payment_id)
    
    def _process_payment(self, payment_id):
        """
        Core payment processing logic
        
        This is where the critical tenant creation happens:
        - Fetch payment details from MercadoPago
        - Find associated subscription
        - Update payment status
        - If payment approved → create tenant for user
        """
        try:
            # Initialize MercadoPago SDK
            mp = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
            
            # Fetch payment details
            payment_response = mp.payment().get(payment_id)
            
            if payment_response["status"] != 200:
                logger.error(f"Failed to fetch payment {payment_id}: {payment_response}")
                return HttpResponseBadRequest("Payment not found")
            
            payment_data = payment_response["response"]
            
            # Extract payment information
            status = payment_data.get('status')
            external_reference = payment_data.get('external_reference')
            
            if not external_reference:
                logger.error(f"Payment {payment_id} missing external_reference")
                return HttpResponseBadRequest("Missing external reference")
            
            # Find associated payment record
            try:
                payment_record = Payment.objects.get(external_reference=external_reference)
            except Payment.DoesNotExist:
                logger.error(f"Payment record not found for reference: {external_reference}")
                return HttpResponseBadRequest("Payment record not found")
            
            # Update payment status
            payment_record.mercadopago_payment_id = payment_id
            payment_record.status = self._map_payment_status(status)
            payment_record.save()
            
            logger.info(f"Updated payment {payment_id} status to {payment_record.status}")
            
            # Handle successful payment - CREATE TENANT
            if payment_record.status == 'completed':
                return self._handle_successful_payment(payment_record)
            elif payment_record.status == 'failed':
                return self._handle_failed_payment(payment_record)
            
            return HttpResponse("OK")
            
        except Exception as e:
            logger.error(f"Error processing payment {payment_id}: {str(e)}")
            return HttpResponseBadRequest("Processing error")
    
    def _handle_successful_payment(self, payment_record):
        """
        Handle successful payment - THIS IS WHERE TENANTS ARE CREATED
        
        Critical flow:
        1. Activate subscription
        2. Create tenant for user (if not exists)
        3. Assign user as tenant admin
        4. Send welcome email
        """
        try:
            subscription = payment_record.subscription
            user = subscription.user
            
            logger.info(f"Processing successful payment for user {user.email}")
            
            # Activate subscription
            subscription.status = 'active'
            subscription.save()
            
            # CREATE TENANT - This is the key step!
            tenant_service = TenantService()
            
            # Check if user already has a tenant (shouldn't happen in normal flow)
            if hasattr(user, 'owned_tenant') and user.owned_tenant:
                logger.warning(f"User {user.email} already has tenant: {user.owned_tenant.slug}")
                tenant = user.owned_tenant
            else:
                # Create new tenant for the user
                tenant_data = {
                    'name': f"{user.first_name or user.email.split('@')[0]}'s Organization",
                    'slug': f"tenant-{user.id}",  # Simple slug generation
                    'description': f"Organization for {user.email}",
                    'owner': user
                }
                
                tenant = tenant_service.create_tenant(tenant_data)
                logger.info(f"Created tenant {tenant.slug} for user {user.email}")
            
            # Update subscription with tenant
            subscription.tenant = tenant
            subscription.save()
            
            # Send welcome email (placeholder)
            self._send_welcome_email(user, subscription, tenant)
            
            logger.info(f"Successfully activated subscription and created tenant for {user.email}")
            return HttpResponse("OK")
            
        except Exception as e:
            logger.error(f"Error handling successful payment: {str(e)}")
            # Don't return error to MercadoPago - log for manual review
            return HttpResponse("OK")
    
    def _handle_failed_payment(self, payment_record):
        """Handle failed payment"""
        try:
            subscription = payment_record.subscription
            
            # Mark subscription as failed
            subscription.status = 'payment_failed'
            subscription.save()
            
            # Send failure notification (placeholder)
            self._send_payment_failure_email(subscription.user, subscription)
            
            logger.info(f"Handled failed payment for user {subscription.user.email}")
            return HttpResponse("OK")
            
        except Exception as e:
            logger.error(f"Error handling failed payment: {str(e)}")
            return HttpResponse("OK")
    
    def _map_payment_status(self, mercadopago_status):
        """Map MercadoPago status to our internal status"""
        status_mapping = {
            'approved': 'completed',
            'pending': 'pending',
            'rejected': 'failed',
            'cancelled': 'failed',
            'refunded': 'refunded',
            'charged_back': 'failed'
        }
        return status_mapping.get(mercadopago_status, 'pending')
    
    def _send_welcome_email(self, user, subscription, tenant):
        """Send welcome email to new tenant owner"""
        # Placeholder for email sending
        logger.info(f"Would send welcome email to {user.email} for tenant {tenant.slug}")
        pass
    
    def _send_payment_failure_email(self, user, subscription):
        """Send payment failure notification"""
        # Placeholder for email sending
        logger.info(f"Would send payment failure email to {user.email}")
        pass


@csrf_exempt
@require_http_methods(["POST"])
def mercadopago_webhook(request):
    """
    Simple function-based webhook handler
    Alternative to class-based view above
    """
    webhook_view = MercadoPagoWebhookView()
    return webhook_view.post(request)