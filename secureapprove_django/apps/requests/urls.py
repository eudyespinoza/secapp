# ==================================================
# SecureApprove Django - Request URLs
# ==================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, dashboard_views
from .api_extensions import bulk_action_requests, export_requests

# API Router
router = DefaultRouter()
router.register(r'api/requests', views.ApprovalRequestViewSet, basename='request-api')

app_name = 'requests'

urlpatterns = [
    # Dashboard (default route)
    path('', dashboard_views.dashboard, name='dashboard'),
    
    # Web interface
    path('list/', views.request_list, name='list'),
    path('new/', views.create_request, name='create'),
    path('<int:pk>/', views.request_detail, name='detail'),
    path('<int:pk>/approve/', views.approve_request, name='approve'),
    path('<int:pk>/reject/', views.reject_request, name='reject'),
    
    # AJAX endpoints
    path('api/category-fields/', views.get_category_fields, name='category-fields'),
    
    # Dashboard API endpoints
    path('api/dashboard/stats/', dashboard_views.dashboard_api_stats, name='dashboard-stats'),
    path('api/dashboard/pending/', dashboard_views.pending_approvals_api, name='pending-approvals'),
    path('api/dashboard/my-summary/', dashboard_views.my_requests_summary_api, name='my-summary'),
    
    # Enhanced API endpoints
    path('api/bulk-action/', bulk_action_requests, name='bulk-action'),
    path('api/export/', export_requests, name='export'),
    
    # DRF API
    path('', include(router.urls)),
]