import base64
import hashlib
import json
import logging
import secrets
import uuid
from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.approvals_api_serializers import (
    TermsConfirmRequestSerializer,
    TermsTokenRequestSerializer,
    normalize_parent_origin,
)
from apps.authentication.models import TermsAcceptanceAudit, TermsApprovalSession, User
from apps.authentication.webauthn_service import webauthn_service

logger = logging.getLogger(__name__)


class NoStoreAPIView(APIView):
    """Prevent browsers and intermediaries from caching tokens or identity results."""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store, max-age=0'
        response['Pragma'] = 'no-cache'
        return response


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


def _approval_context(session: TermsApprovalSession) -> dict:
    context_data = {
        'purpose': session.purpose,
        'decision': session.decision,
        'parent_origin': session.parent_origin,
        'document_type': session.document_type,
        'document_version': session.document_version,
        'document_hash': session.document_hash,
        'subject_user_id': str(session.subject_user_id),
        'tenant_id': str(session.tenant_id),
    }
    extra = session.context_data or {}
    if isinstance(extra, dict) and extra:
        context_data['extra'] = extra
    return context_data


def _transaction_payload(session: TermsApprovalSession, audit=None) -> dict:
    completed = session.result_status in {'approved', 'rejected'}
    return {
        'id': str(session.id),
        'state': session.result_status,
        'decision': session.decision,
        'approved': session.decision == 'approve' if completed else None,
        'parentOrigin': session.parent_origin,
        'purpose': session.purpose,
        'document': {
            'type': session.document_type,
            'version': session.document_version,
            'sha256': session.document_hash,
        },
        'tenant': {
            'id': str(session.tenant_id),
            'key': session.tenant.key,
            'name': session.tenant.name,
        },
        'subject': {
            'id': str(session.subject_user_id),
            'email': session.subject_user.email,
            'name': session.subject_user.get_full_name(),
        },
        'context': session.context_data or {},
        'expiresAt': session.expires_at.isoformat(),
        'completedAt': session.completed_at.isoformat() if session.completed_at else None,
        'auditId': str(audit.id) if audit else None,
        'verificationPassed': completed,
        'assurance': {
            'method': 'webauthn',
            'userVerification': 'required',
        },
    }


def create_terms_approval_session(*, created_by: User, subject_user: User, data: dict):
    """Create the immutable server-side transaction and its one-time WebAuthn challenge."""
    raw_token = secrets.token_urlsafe(48)
    session_id = uuid.uuid4()
    session = TermsApprovalSession.objects.create(
        id=session_id,
        tenant=created_by.tenant,
        subject_user=subject_user,
        created_by=created_by,
        purpose=data['purpose'],
        decision=data['decision'],
        parent_origin=data['parent_origin'],
        document_type=data['document_type'],
        document_version=data['document_version'],
        document_hash=data['document_hash'],
        context_data=data.get('context', {}) or {},
        approval_id=f'terms_{session_id}',
        token_hash=_sha256_hex(raw_token),
        expires_at=timezone.now() + timedelta(seconds=120),
    )

    try:
        options = webauthn_service.generate_approval_challenge(
            user=subject_user,
            approval_id=session.approval_id,
            context_data=_approval_context(session),
        )
    except Exception:
        session.delete()
        raise

    session.challenge_id = options.get('challengeId', '')
    session.save(update_fields=['challenge_id'])
    return session, raw_token, options


def _decode_client_data(webauthn_response: dict) -> dict:
    try:
        encoded = webauthn_response['response']['clientDataJSON']
        if not isinstance(encoded, str) or len(encoded) > 16384:
            raise ValueError
        padded = encoded + ('=' * ((4 - len(encoded) % 4) % 4))
        decoded = base64.urlsafe_b64decode(padded.encode('ascii'))
        if len(decoded) > 8192:
            raise ValueError
        client_data = json.loads(decoded.decode('utf-8'))
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('Invalid WebAuthn clientDataJSON.') from exc

    if not isinstance(client_data, dict):
        raise ValueError('Invalid WebAuthn clientDataJSON.')
    return client_data


def _validate_embedded_origin(session: TermsApprovalSession, webauthn_response: dict) -> dict:
    """Validate the RP caller and the browser-authenticated top-level embedding origin."""
    client_data = _decode_client_data(webauthn_response)
    try:
        caller_origin = normalize_parent_origin(client_data.get('origin', ''))
        expected_parent = normalize_parent_origin(session.parent_origin)
        allowed_callers = {
            normalize_parent_origin(origin)
            for origin in webauthn_service.allowed_origins
        }
    except Exception as exc:
        raise ValueError('Invalid WebAuthn origin.') from exc

    if caller_origin not in allowed_callers:
        raise ValueError('Unexpected WebAuthn caller origin.')

    cross_origin = client_data.get('crossOrigin') is True
    top_origin_value = client_data.get('topOrigin')

    if caller_origin == expected_parent:
        if cross_origin:
            try:
                top_origin = normalize_parent_origin(top_origin_value)
            except Exception as exc:
                raise ValueError('Missing or invalid WebAuthn top origin.') from exc
            if top_origin != expected_parent:
                raise ValueError('Unexpected WebAuthn top origin.')
    else:
        if not cross_origin:
            raise ValueError('Cross-origin WebAuthn context was not declared by the browser.')
        try:
            top_origin = normalize_parent_origin(top_origin_value)
        except Exception as exc:
            raise ValueError('Missing or invalid WebAuthn top origin.') from exc
        if top_origin != expected_parent:
            raise ValueError('Unexpected WebAuthn top origin.')

    return {
        'caller_origin': caller_origin,
        'cross_origin': cross_origin,
        'top_origin': top_origin_value or caller_origin,
    }


def _create_audit(session, request, *, status, context_data, error_message='', verification_result=None):
    verification_result = verification_result or {}
    return TermsAcceptanceAudit.objects.create(
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
        ip_address=_get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        user_snapshot=_user_snapshot(session.subject_user),
        context_data=context_data,
        error_message=error_message,
    )


class TermsApprovalTokenView(NoStoreAPIView):
    """Create a short-lived transaction bound to a user, document, decision, and host origin."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TermsTokenRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if not getattr(request.user, 'tenant_id', None):
            return Response({'detail': 'Authenticated user has no tenant.'}, status=400)
        if not request.user.can_admin_tenant():
            return Response({'detail': 'Insufficient permissions.'}, status=403)

        subject_user = get_object_or_404(User, pk=data['user_id'])
        if subject_user.tenant_id != request.user.tenant_id:
            return Response({'detail': 'User does not belong to your tenant.'}, status=403)
        if not subject_user.has_webauthn_credentials:
            return Response({'detail': 'User has no WebAuthn credentials.'}, status=400)

        session, raw_token, options = create_terms_approval_session(
            created_by=request.user,
            subject_user=subject_user,
            data=data,
        )
        return Response(
            {
                'approval_token': raw_token,
                'webauthn_options': options,
                'transaction': _transaction_payload(session),
            },
            status=201,
        )


class TermsApprovalConfirmView(NoStoreAPIView):
    """Consume a one-time token and persist an origin-bound WebAuthn result atomically."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TermsConfirmRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        token_hash = _sha256_hex(data['approval_token'])

        with transaction.atomic():
            try:
                session = (
                    TermsApprovalSession.objects
                    .select_for_update()
                    .select_related('tenant', 'subject_user', 'created_by')
                    .get(token_hash=token_hash)
                )
            except TermsApprovalSession.DoesNotExist:
                return Response({'detail': 'Invalid or expired token.'}, status=400)

            if session.is_consumed:
                return Response({'detail': 'Token already used.'}, status=409)

            now = timezone.now()
            context_data = _approval_context(session)

            if session.is_expired:
                session.consumed_at = now
                session.completed_at = now
                session.result_status = 'expired'
                session.save(update_fields=['consumed_at', 'completed_at', 'result_status'])
                _create_audit(
                    session,
                    request,
                    status='expired',
                    context_data=context_data,
                    error_message='Approval token expired',
                )
                return Response({'detail': 'Token expired.'}, status=400)

            try:
                embedded_origin = _validate_embedded_origin(session, data['webauthn_response'])
                context_data['webauthn_context'] = embedded_origin
                verification_result = webauthn_service.verify_approval_response(
                    user=session.subject_user,
                    approval_id=session.approval_id,
                    credential_data=data['webauthn_response'],
                    context_data=_approval_context(session),
                )
                if not verification_result.get('verified'):
                    raise ValueError('Verification returned false')
            except ValueError as exc:
                session.consumed_at = now
                session.completed_at = now
                session.result_status = 'failed'
                session.save(update_fields=['consumed_at', 'completed_at', 'result_status'])
                _create_audit(
                    session,
                    request,
                    status='failed',
                    context_data=context_data,
                    error_message=str(exc),
                )
                return Response({'detail': 'WebAuthn verification failed.'}, status=400)

            result_status = 'approved' if session.decision == 'approve' else 'rejected'
            session.consumed_at = now
            session.completed_at = now
            session.result_status = result_status
            session.save(update_fields=['consumed_at', 'completed_at', 'result_status'])

            audit = _create_audit(
                session,
                request,
                status='success',
                context_data=context_data,
                verification_result=verification_result,
            )

        logger.info(
            'Terms approval confirmed: tenant=%s user=%s result=%s',
            session.tenant_id,
            session.subject_user_id,
            result_status,
        )
        return Response(
            {
                'success': True,
                'approved': session.decision == 'approve',
                'status': result_status,
                'authenticated': result_status == 'approved',
                'verification_passed': True,
                'transaction_id': str(session.id),
                'audit_id': str(audit.id),
            },
            status=200,
        )


class TermsApprovalStatusView(NoStoreAPIView):
    """Authoritative server-to-server result used by the integrating backend."""

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        if not getattr(request.user, 'tenant_id', None):
            return Response({'detail': 'Authenticated user has no tenant.'}, status=400)

        session = get_object_or_404(
            TermsApprovalSession.objects.select_related('tenant', 'subject_user'),
            pk=session_id,
            tenant_id=request.user.tenant_id,
        )
        if not request.user.can_admin_tenant() and request.user.pk != session.subject_user_id:
            return Response({'detail': 'Insufficient permissions.'}, status=403)

        audit = session.audits.order_by('-performed_at').first()
        return Response({
            'transaction': _transaction_payload(session, audit),
            'authenticated': session.result_status == 'approved',
            'verification_passed': session.result_status in {'approved', 'rejected'},
        })
