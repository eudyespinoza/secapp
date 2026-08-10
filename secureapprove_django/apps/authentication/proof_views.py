from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.authentication.models import ProofSigningKey, SecurityProof
from apps.authentication.proof_service import (
    InvalidProof,
    decrypt_evidence,
    verify_private_evidence_integrity,
    verification_result_for_jws,
    verification_result_for_proof,
)


class ProofAPIView(APIView):
    throttle_classes = [ScopedRateThrottle]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store, max-age=0'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


def proof_jwks(request):
    keys = []
    for key in ProofSigningKey.objects.order_by('-activated_at'):
        jwk = dict(key.public_jwk)
        jwk['secureapprove_status'] = key.status
        keys.append(jwk)
    response = JsonResponse({'keys': keys})
    response['Cache-Control'] = 'public, max-age=300, stale-while-revalidate=3600'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


class ProofVerifyByIdView(ProofAPIView):
    permission_classes = [AllowAny]
    throttle_scope = 'proof_verify'

    def get(self, request, proof_id):
        proof = SecurityProof.objects.select_related('signing_key').filter(pk=proof_id).first()
        if not proof:
            return Response({'valid': False, 'status': 'unknown'}, status=404)
        return Response(verification_result_for_proof(proof))


class ProofVerifyJWSView(ProofAPIView):
    permission_classes = [AllowAny]
    throttle_scope = 'proof_verify'

    def post(self, request):
        content_length = request.META.get('CONTENT_LENGTH')
        if content_length:
            try:
                if int(content_length) > 16896:
                    return Response({'valid': False, 'status': 'altered', 'detail': 'Request is too large.'}, status=413)
            except (TypeError, ValueError):
                return Response({'valid': False, 'status': 'altered', 'detail': 'Invalid request size.'}, status=400)
        jws = request.data.get('jws') if isinstance(request.data, dict) else None
        if not isinstance(jws, str):
            return Response({'valid': False, 'status': 'altered', 'detail': 'A compact JWS is required.'}, status=400)
        if len(jws.encode('utf-8')) > 16384:
            return Response({'valid': False, 'status': 'altered', 'detail': 'Proof exceeds the 16 KB limit.'}, status=413)
        return Response(verification_result_for_jws(jws.strip()))


class ProofEvidenceView(ProofAPIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = 'proof_evidence'

    def get(self, request, proof_id):
        proof = get_object_or_404(
            SecurityProof.objects.select_related('tenant', 'subject_user', 'actor_user'),
            pk=proof_id,
        )
        same_tenant = getattr(request.user, 'tenant_id', None) == proof.tenant_id
        is_involved = request.user.pk in {proof.subject_user_id, proof.actor_user_id}
        is_admin = same_tenant and request.user.can_admin_tenant()
        if not (request.user.is_superuser or is_involved or is_admin):
            return Response({'detail': 'Insufficient permissions.'}, status=403)
        try:
            evidence = decrypt_evidence(proof)
        except InvalidProof as exc:
            return Response({
                'proof_id': str(proof.id),
                'status': 'evidence_expired',
                'detail': str(exc),
            }, status=410)
        payload = {
            'proof_id': str(proof.id),
            'schema': proof.schema,
            'integrity': verify_private_evidence_integrity(proof, evidence),
            'evidence': evidence,
        }
        response = Response(payload)
        if request.GET.get('download') == '1':
            response['Content-Disposition'] = f'attachment; filename="secureapprove-proof-{proof.id}.json"'
        return response
