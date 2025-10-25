# ==================================================
# SecureApprove Django - Billing Views
# ==================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.translation import gettext as _
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import json
import logging

from .models import Plan, Subscription, Payment, Invoice
from .services import get_billing_service, get_mp_service
from .serializers import PlanSerializer, SubscriptionSerializer, PaymentSerializer

logger = logging.getLogger(__name__)

# ==================================================
# Web Views (Django Templates)
# ==================================================

@login_required
def billing_dashboard(request):
    """Main billing dashboard"""
    
    tenant = request.user.tenant
    subscription = getattr(tenant, 'subscription', None)
    
    context = {
        'subscription': subscription,
        'plans': Plan.objects.filter(is_active=True).order_by('order'),
    }
    
    if subscription:
        # Get usage stats
        usage_stats = get_billing_service().get_usage_stats(subscription)
        context['usage_stats'] = usage_stats
        
        # Check limits
        limits_check = get_billing_service().check_limits(subscription)
        context['limits_check'] = limits_check
        
        # Recent payments
        recent_payments = Payment.objects.filter(
            subscription=subscription
        ).order_by('-created_at')[:5]
        context['recent_payments'] = recent_payments
        
        # Recent invoices
        recent_invoices = Invoice.objects.filter(
            subscription=subscription
        ).order_by('-issue_date')[:5]
        context['recent_invoices'] = recent_invoices
    
    return render(request, 'billing/dashboard.html', context)

@login_required
def select_plan(request):
    """Plan selection page"""
    
    plans = Plan.objects.filter(is_active=True).order_by('order')
    current_subscription = getattr(request.user.tenant, 'subscription', None)
    
    context = {
        'plans': plans,
        'current_subscription': current_subscription,
    }
    
    return render(request, 'billing/select_plan.html', context)

def subscribe_to_plan(request, plan_name):
    """Subscribe to a specific plan"""
    plan = get_object_or_404(Plan, name=plan_name, is_active=True)
    
    context = {
        'plan': plan,
        'user': request.user if request.user.is_authenticated else None
    }
    
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            context['error'] = _('Email is required')
            return render(request, 'billing/subscribe.html', context)
        
        # Create checkout preference using the service that already exists
        try:
            checkout_data = get_mp_service().create_preference({
                'planId': plan.name,
                'seats': 10,
                'customerEmail': email
            })
            
            if checkout_data.get('success'):
                # Redirect to MercadoPago
                init_point = checkout_data.get('init_point') or checkout_data.get('sandbox_init_point')
                if init_point:
                    return redirect(init_point)
            
            context['error'] = checkout_data.get('error', _('Failed to create checkout session'))
            
        except Exception as e:
            logger.error(f"Error creating checkout: {str(e)}")
            context['error'] = _('Failed to create checkout session')
    
    return render(request, 'billing/subscribe.html', context)


@login_required
@require_http_methods(["POST"])
def change_plan(request):
    """Change subscription plan"""
    
    subscription = get_object_or_404(Subscription, tenant=request.user.tenant)
    new_plan_id = request.POST.get('plan_id')
    
    try:
        new_plan = Plan.objects.get(id=new_plan_id, is_active=True)
    except Plan.DoesNotExist:
        messages.error(request, _('Invalid plan selected.'))
        return redirect('billing:dashboard')
    
    result = get_billing_service().change_plan(subscription, new_plan.name)
    
    if result['success']:
        if 'upgrade_charge' in result:
            # Redirect to payment for upgrade
            return redirect(result['upgrade_charge']['init_point'])
        else:
            messages.success(request, _('Plan changed successfully.'))
    else:
        messages.error(request, result['error'])
    
    return redirect('billing:dashboard')

@login_required
@require_http_methods(["POST"])
def cancel_subscription(request):
    """Cancel subscription"""
    
    subscription = get_object_or_404(Subscription, tenant=request.user.tenant)
    reason = request.POST.get('reason', '')
    
    result = get_billing_service().cancel_subscription(subscription, reason)
    
    if result['success']:
        messages.success(request, _('Subscription cancelled successfully.'))
    else:
        messages.error(request, _('Failed to cancel subscription.'))
    
    return redirect('billing:dashboard')

def payment_success(request):
    """Payment success page"""
    return render(request, 'billing/payment_success.html')

def payment_failure(request):
    """Payment failure page"""
    return render(request, 'billing/payment_failure.html')

def payment_pending(request):
    """Payment pending page"""
    return render(request, 'billing/payment_pending.html')

def mercadopago_webhook(request):
    """MercadoPago webhook handler - delegate to webhooks module"""
    from .webhooks import MercadoPagoWebhookView
    webhook_view = MercadoPagoWebhookView()
    return webhook_view.post(request)

@login_required
def invoices(request):
    """List invoices"""
    
    subscription = get_object_or_404(Subscription, tenant=request.user.tenant)
    invoices = Invoice.objects.filter(subscription=subscription).order_by('-issue_date')
    
    context = {
        'invoices': invoices,
        'subscription': subscription,
    }
    
    return render(request, 'billing/invoices.html', context)

@login_required
def invoice_detail(request, invoice_id):
    """Invoice detail view"""
    
    invoice = get_object_or_404(
        Invoice,
        id=invoice_id,
        subscription__tenant=request.user.tenant
    )
    
    context = {
        'invoice': invoice,
    }
    
    return render(request, 'billing/invoice_detail.html', context)

# ==================================================
# API Views (Django REST Framework)
# ==================================================

class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet for Plans"""
    
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Plan.objects.filter(is_active=True).order_by('order')

class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet for Subscriptions"""
    
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Subscription.objects.filter(tenant=self.request.user.tenant)
    
    @action(detail=True, methods=['post'])
    def change_plan(self, request, pk=None):
        """Change subscription plan via API"""
        
        subscription = self.get_object()
        new_plan_name = request.data.get('plan_name')
        
        if not new_plan_name:
            return Response(
                {'error': 'plan_name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = get_billing_service().change_plan(subscription, new_plan_name)
        
        if result['success']:
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        else:
            return Response(
                {'error': result['error']},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel subscription via API"""
        
        subscription = self.get_object()
        reason = request.data.get('reason', '')
        
        result = get_billing_service().cancel_subscription(subscription, reason)
        
        if result['success']:
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Failed to cancel subscription'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def usage_stats(self, request, pk=None):
        """Get usage statistics"""
        
        subscription = self.get_object()
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        if year:
            year = int(year)
        if month:
            month = int(month)
        
        usage_stats = get_billing_service().get_usage_stats(subscription, year, month)
        
        return Response({
            'year': usage_stats.year,
            'month': usage_stats.month,
            'requests_created': usage_stats.requests_created,
            'requests_approved': usage_stats.requests_approved,
            'requests_rejected': usage_stats.requests_rejected,
            'approval_rate': usage_stats.approval_rate,
            'active_users': usage_stats.active_users,
            'total_users': usage_stats.total_users,
            'api_calls': usage_stats.api_calls,
        })
    
    @action(detail=True, methods=['get'])
    def limits_check(self, request, pk=None):
        """Check subscription limits"""
        
        subscription = self.get_object()
        limits_check = get_billing_service().check_limits(subscription)
        
        return Response(limits_check)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_subscription_api(request):
    """Create subscription via API"""
    
    plan_name = request.data.get('plan_name')
    billing_cycle = request.data.get('billing_cycle', 'monthly')
    
    if not plan_name:
        return Response(
            {'error': 'plan_name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    tenant = request.user.tenant
    result = get_billing_service().create_subscription(tenant, plan_name, billing_cycle)
    
    if result['success']:
        subscription = result['subscription']
        
        # Create payment preference
        preference_result = get_mp_service().create_preference(subscription, billing_cycle)
        
        if preference_result['success']:
            return Response({
                'subscription_id': subscription.id,
                'payment_url': preference_result['init_point'],
                'preference_id': preference_result['preference_id']
            })
        else:
            return Response(
                {'error': 'Failed to create payment preference'},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        return Response(
            {'error': result['error']},
            status=status.HTTP_400_BAD_REQUEST
        )

# ==================================================
# Webhook Handlers
# ==================================================

@csrf_exempt
@require_http_methods(["POST"])
def mercadopago_webhook(request):
    """Handle MercadoPago webhook notifications"""
    
    try:
        webhook_data = json.loads(request.body)
        logger.info(f"MercadoPago webhook received: {webhook_data}")
        
        result = get_mp_service().process_webhook(webhook_data)
        
        if result['success']:
            return HttpResponse(status=200)
        else:
            logger.error(f"Webhook processing failed: {result['error']}")
            return HttpResponse(status=400)
            
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return HttpResponse(status=500)