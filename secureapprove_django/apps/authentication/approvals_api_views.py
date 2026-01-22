import hashlib
import logging
import secrets
import uuid
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import TermsAcceptanceAudit, TermsApprovalSession
from apps.authentication.webauthn_service import webauthn_service
from apps.authentication.approvals_api_serializers import (
    TermsConfirmRequestSerializer,
    TermsTokenRequestSerializer,
)
from apps.authentication.models import User

logger = logging.getLogger(__name__)


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _user_snapshot(user: User) -> dict:
    tenant = getattr(user, 'tenant', None)
    return {
        'id': user.id,
        'email': user.email,
        'name': user.get_full_name(),
        'role': getattr(user, 'role', None),
        'username': getattr(user, 'username', None),
        'tenant_id': getattr(user, 'tenant_id', None),
        'tenant_key': getattr(tenant, 'key', None) if tenant else None,
        'tenant_name': getattr(tenant, 'name', None) if tenant else None,
    }


class TermsApprovalTokenView(APIView):
    """Tenant-authenticated endpoint: create a short-lived approval token + WebAuthn options."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TermsTokenRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Tenant context is derived from the authenticated user.
        if not getattr(request.user, 'tenant_id', None):
            return Response({'detail': 'Authenticated user has no tenant.'}, status=400)

        # Only tenant admins (or the subject user) can request tokens.
        if not request.user.can_admin_tenant():
            return Response({'detail': 'Insufficient permissions.'}, status=403)

        subject_user = get_object_or_404(User, pk=data['user_id'])

        if subject_user.tenant_id != request.user.tenant_id:
            return Response({'detail': 'User does not belong to your tenant.'}, status=403)

        if not subject_user.has_webauthn_credentials:
            return Response({'detail': 'User has no WebAuthn credentials.'}, status=400)

        purpose = data['purpose']
        document_type = data['document_type']
        document_version = data['document_version']
        document_hash = data['document_hash']

        # Short-lived, one-time opaque token (store only hash)
        raw_token = secrets.token_urlsafe(48)
        token_hash = _sha256_hex(raw_token)

        expires_at = timezone.now() + timedelta(seconds=120)

        session_id = uuid.uuid4()

        # Create session now (UUID assigned immediately)
        session = TermsApprovalSession(
            id=session_id,
            tenant=request.user.tenant,
            subject_user=subject_user,
            created_by=request.user,
            purpose=purpose,
            document_type=document_type,
            document_version=document_version,
            document_hash=document_hash,
            context_data=data.get('context', {}) or {},
            approval_id=f"terms_{session_id}",
            token_hash=token_hash,
            expires_at=expires_at,
        )

        # Build context for cryptographic binding
        context_data = {
            'purpose': purpose,
            'document_type': document_type,
            'document_version': document_version,
            'document_hash': document_hash,
            'subject_user_id': str(subject_user.id),
            'tenant_id': str(request.user.tenant_id),
        }
        extra = session.context_data or {}
        if isinstance(extra, dict) and extra:
            context_data['extra'] = extra

        # Save before generating options to ensure session exists
        session.save()

        options = webauthn_service.generate_approval_challenge(
            user=subject_user,
            approval_id=session.approval_id,
            context_data=context_data,
        )

        session.challenge_id = options.get('challengeId', '')
        session.save(update_fields=['challenge_id'])

        return Response(
            {
                'approval_token': raw_token,
                'expires_at': session.expires_at.isoformat(),
                'webauthn_options': options,
                'purpose': purpose,
                'document_type': document_type,
                'document_version': document_version,
                'document_hash': document_hash,
            },
            status=201,
        )


class TermsApprovalConfirmView(APIView):
    """Public endpoint that consumes a short-lived token and verifies WebAuthn assertion."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TermsConfirmRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        token_hash = _sha256_hex(data['approval_token'])

        try:
            session = TermsApprovalSession.objects.select_related('tenant', 'subject_user', 'created_by').get(
                token_hash=token_hash
            )
        except TermsApprovalSession.DoesNotExist:
            return Response({'detail': 'Invalid or expired token.'}, status=400)

        ip = _get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        if session.is_consumed:
            return Response({'detail': 'Token already used.'}, status=409)

        if session.is_expired:
            TermsAcceptanceAudit.objects.create(
                tenant=session.tenant,
                user=session.subject_user,
                initiated_by=session.created_by,
                session=session,
                purpose=session.purpose,
                document_type=session.document_type,
                document_version=session.document_version,
                document_hash=session.document_hash,
                status='expired',
                ip_address=ip,
                user_agent=user_agent,
                user_snapshot=_user_snapshot(session.subject_user),
                context_data=session.context_data or {},
                error_message='Approval token expired',
            )
            return Response({'detail': 'Token expired.'}, status=400)

        # Consume the token now (one-time semantics, prevents concurrent replay).
        # WebAuthn challenge itself is also one-time in cache, but we harden at DB level.
        with transaction.atomic():
            updated = TermsApprovalSession.objects.filter(
                pk=session.pk,
                consumed_at__isnull=True,
            ).update(consumed_at=timezone.now())

        if updated != 1:
            return Response({'detail': 'Token already used.'}, status=409)

        # Build context_data exactly as in token issuance
        context_data = {
            'purpose': session.purpose,
            'document_type': session.document_type,
            'document_version': session.document_version,
            'document_hash': session.document_hash,
            'subject_user_id': str(session.subject_user_id),
            'tenant_id': str(session.tenant_id),
        }
        extra = session.context_data or {}
        if isinstance(extra, dict) and extra:
            context_data['extra'] = extra

        approved = data['approved']
        webauthn_response = data['webauthn_response']

        try:
            verification_result = webauthn_service.verify_approval_response(
                user=session.subject_user,
                approval_id=session.approval_id,
                credential_data=webauthn_response,
                context_data=context_data,
            )
        except ValueError as e:
            TermsAcceptanceAudit.objects.create(
                tenant=session.tenant,
                user=session.subject_user,
                initiated_by=session.created_by,
                session=session,
                purpose=session.purpose,
                document_type=session.document_type,
                document_version=session.document_version,
                document_hash=session.document_hash,
                status='failed',
                ip_address=ip,
                user_agent=user_agent,
                user_snapshot=_user_snapshot(session.subject_user),
                context_data=context_data,
                error_message=str(e),
            )
            return Response({'detail': 'WebAuthn verification failed.'}, status=400)

        if not verification_result.get('verified'):
            TermsAcceptanceAudit.objects.create(
                tenant=session.tenant,
                user=session.subject_user,
                initiated_by=session.created_by,
                session=session,
                purpose=session.purpose,
                document_type=session.document_type,
                document_version=session.document_version,
                document_hash=session.document_hash,
                status='failed',
                ip_address=ip,
                user_agent=user_agent,
                user_snapshot=_user_snapshot(session.subject_user),
                context_data=context_data,
                error_message='Verification returned false',
                credential_id=verification_result.get('credential_id', ''),
                challenge_id=verification_result.get('challenge_id', ''),
            )
            return Response({'detail': 'WebAuthn verification failed.'}, status=400)

        status = 'success' if approved else 'cancelled'

        audit = TermsAcceptanceAudit.objects.create(
            tenant=session.tenant,
            user=session.subject_user,
            initiated_by=session.created_by,
            session=session,
            purpose=session.purpose,
            document_type=session.document_type,
            document_version=session.document_version,
            document_hash=session.document_hash,
            status=status,
            credential_id=verification_result.get('credential_id', ''),
            challenge_id=verification_result.get('challenge_id', ''),
            ip_address=ip,
            user_agent=user_agent,
            user_snapshot=_user_snapshot(session.subject_user),
            context_data=context_data,
        )

        logger.info(
            "Terms approval confirmed: tenant=%s user=%s status=%s",
            session.tenant_id,
            session.subject_user_id,
            status,
        )

        return Response(
            {
                'success': True,
                'approved': approved,
                'status': status,
                'audit_id': str(audit.id),
            },
            status=200,
        )
