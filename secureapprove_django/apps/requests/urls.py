# ==================================================
# SecureApprove Django - Request URLs
# ==================================================

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, dashboard_views, webauthn_views
from .api_extensions import bulk_action_requests, export_requests
from apps.chat.views import ChatPageView

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
    
    # Attachment download (bypasses nginx for forced download)
    path('attachments/<int:attachment_id>/download/', views.download_request_attachment, name='download-attachment'),
    
    # WebAuthn step-up authentication for approvals
    path('<int:approval_id>/webauthn/options/', webauthn_views.approval_webauthn_options, name='approval-webauthn-options'),
    path('<int:approval_id>/webauthn/verify/', webauthn_views.approval_webauthn_verify, name='approval-webauthn-verify'),
    
    # WebAuthn step-up authentication for request creation
    path('new/webauthn/options/', webauthn_views.create_request_webauthn_options, name='create-webauthn-options'),
    path('new/webauthn/verify/', webauthn_views.create_request_webauthn_verify, name='create-webauthn-verify'),

    # Chat UI entrypoint (template)
    path('chat/', ChatPageView.as_view(), name='chat'),
    
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
