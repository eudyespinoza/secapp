from django.urls import path

from apps.authentication.approvals_api_views import (
    TermsApprovalConfirmView,
    TermsApprovalTokenView,
)

urlpatterns = [
    path('terms/token/', TermsApprovalTokenView.as_view(), name='terms-approval-token'),
    path('terms/confirm/', TermsApprovalConfirmView.as_view(), name='terms-approval-confirm'),
]
