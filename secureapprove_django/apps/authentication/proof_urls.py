from django.urls import path

from apps.authentication.proof_views import (
    ProofEvidenceView,
    ProofVerifyByIdView,
    ProofVerifyJWSView,
)

app_name = 'proofs'

urlpatterns = [
    path('verify/', ProofVerifyJWSView.as_view(), name='verify_jws'),
    path('<uuid:proof_id>/verify/', ProofVerifyByIdView.as_view(), name='verify_id'),
    path('<uuid:proof_id>/evidence/', ProofEvidenceView.as_view(), name='evidence'),
]
