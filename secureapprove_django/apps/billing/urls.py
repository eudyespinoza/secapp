# ==================================================
# SecureApprove Django - Billing URLs
# ==================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, api

# API Router
router = DefaultRouter()
router.register(r'plans', views.PlanViewSet, basename='plan')
router.register(r'subscriptions', views.SubscriptionViewSet, basename='subscription')

app_name = 'billing'

urlpatterns = [
    # Web interface
    path('', views.billing_dashboard, name='dashboard'),
    path('plans/', views.select_plan, name='select_plan'),
    path('subscribe/<str:plan_name>/', views.subscribe_to_plan, name='subscribe'),
    path('change-plan/', views.change_plan, name='change_plan'),
    path('cancel/', views.cancel_subscription, name='cancel'),
    path('invoices/', views.invoices, name='invoices'),
    path('invoices/<uuid:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    
    # Payment result pages
    path('success/', views.payment_success, name='payment_success'),
    path('failure/', views.payment_failure, name='payment_failure'),
    path('pending/', views.payment_pending, name='payment_pending'),
    
    # API endpoints
    path('api/create-subscription/', views.create_subscription_api, name='create_subscription_api'),
    path('api/payment-preference/', api.create_payment_preference, name='create_payment_preference'),
    path('api/subscription-status/', api.get_subscription_status, name='subscription_status'),
    path('api/plans/', api.get_plans, name='api_plans'),
    
    # Webhooks
    path('webhooks/mercadopago/', views.mercadopago_webhook, name='mercadopago_webhook'),
    
    # DRF API
    path('api/', include(router.urls)),
]