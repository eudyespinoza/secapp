# billing/api.py
"""
API endpoints for billing operations
Provides JSON API for frontend integration
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.conf import settings
import mercadopago

from .models import Plan, Subscription, Payment
from .services import BillingService

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def create_payment_preference(request):
    """
    Create MercadoPago payment preference
    
    This API endpoint is called when user clicks "Subscribe" button
    Returns MercadoPago preference ID for payment processing
    """
    try:
        data = json.loads(request.body)
        plan_name = data.get('plan_name')
        
        if not plan_name:
            return JsonResponse({'error': 'Plan name required'}, status=400)
        
        # Get plan
        try:
            plan = Plan.objects.get(name=plan_name)
        except Plan.DoesNotExist:
            return JsonResponse({'error': 'Plan not found'}, status=404)
        
        # Check if user already has active subscription
        existing_subscription = Subscription.objects.filter(
            user=request.user,
            status__in=['active', 'pending']
        ).first()
        
        if existing_subscription:
            return JsonResponse({
                'error': 'User already has an active subscription'
            }, status=400)
        
        # Create subscription record
        billing_service = BillingService()
        subscription = billing_service.create_subscription(request.user, plan)
        
        # Create payment preference
        preference_data = billing_service.create_payment_preference(subscription)
        
        return JsonResponse({
            'success': True,
            'preference_id': preference_data['id'],
            'subscription_id': str(subscription.id),
            'init_point': preference_data.get('init_point')
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error creating payment preference: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@require_http_methods(["GET"])
@login_required
def get_subscription_status(request):
    """Get current user's subscription status"""
    try:
        subscription = Subscription.objects.filter(user=request.user).first()
        
        if not subscription:
            return JsonResponse({
                'has_subscription': False,
                'status': None
            })
        
        return JsonResponse({
            'has_subscription': True,
            'status': subscription.status,
            'plan': subscription.plan.name,
            'created_at': subscription.created_at.isoformat(),
            'tenant_created': hasattr(request.user, 'owned_tenant') and request.user.owned_tenant is not None
        })
        
    except Exception as e:
        logger.error(f"Error getting subscription status: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@require_http_methods(["GET"])
def get_plans(request):
    """Get available subscription plans"""
    try:
        plans = Plan.objects.filter(is_active=True).order_by('monthly_price')
        
        plans_data = []
        for plan in plans:
            plans_data.append({
                'id': str(plan.id),
                'name': plan.name,
                'display_name': plan.display_name,
                'monthly_price': float(plan.monthly_price),
                'description': plan.description,
                'features': plan.features,
                'max_users': plan.max_users,
                'max_requests_per_month': plan.max_requests_per_month
            })
        
        return JsonResponse({
            'success': True,
            'plans': plans_data
        })
        
    except Exception as e:
        logger.error(f"Error getting plans: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)