from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import TermsAcceptanceAudit, TermsApprovalSession, User
from apps.tenants.models import Tenant


class TermsApprovalAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(key='tenant-test', name='Tenant Test')

        self.admin = User.objects.create_user(
            email='admin@tenant.test',
            username='admin',
            password='pass12345',
            name='Admin User',
            tenant=self.tenant,
            role='tenant_admin',
        )

        self.subject = User.objects.create_user(
            email='user@tenant.test',
            username='user',
            password='pass12345',
            name='Subject User',
            tenant=self.tenant,
            role='requester',
        )

        # Mark user as having WebAuthn credentials
        self.subject.webauthn_credentials = [
            {
                'credential_id': 'Y3JlZA==',
                'credential_public_key': 'cGs=',
                'sign_count': 0,
                'is_active': True,
            }
        ]
        self.subject.save(update_fields=['webauthn_credentials'])

    @patch('apps.authentication.approvals_api_views.webauthn_service.generate_approval_challenge')
    @patch('apps.authentication.approvals_api_views.webauthn_service.verify_approval_response')
    def test_terms_flow_success(self, mock_verify, mock_generate):
        mock_generate.return_value = {
            'challenge': 'Y2hhbGxlbmdl',
            'timeout': 60000,
            'rpId': 'example.com',
            'allowCredentials': [],
            'userVerification': 'required',
            'challengeId': 'challenge-1',
        }
        mock_verify.return_value = {
            'verified': True,
            'credential_id': 'cred-1',
            'challenge_id': 'challenge-1',
        }

        self.client.force_authenticate(user=self.admin)
        token_resp = self.client.post(
            '/api/approvals/terms/token/',
            {
                'user_id': self.subject.id,
                'purpose': 'terms_acceptance',
                'document_type': 'terms',
                'document_version': '2026-01',
                'document_hash': 'hash-abc',
                'context': {'source': 'signup'},
            },
            format='json',
        )

        self.assertEqual(token_resp.status_code, 201)
        approval_token = token_resp.json()['approval_token']

        confirm_resp = self.client.post(
            '/api/approvals/terms/confirm/',
            {
                'approval_token': approval_token,
                'approved': True,
                'webauthn_response': {'id': 'x', 'rawId': 'y', 'type': 'public-key', 'response': {}},
            },
            format='json',
        )

        self.assertEqual(confirm_resp.status_code, 200)
        self.assertTrue(confirm_resp.json()['success'])

        self.assertEqual(TermsAcceptanceAudit.objects.count(), 1)
        audit = TermsAcceptanceAudit.objects.first()
        self.assertEqual(audit.status, 'success')
        self.assertEqual(audit.user_id, self.subject.id)
        self.assertEqual(audit.tenant_id, self.tenant.id)

        session = TermsApprovalSession.objects.first()
        self.assertIsNotNone(session.consumed_at)

    def test_confirm_expired_creates_audit(self):
        # Create an expired session with a known token
        approval_token = 'tok-test'
        token_hash = __import__('hashlib').sha256(approval_token.encode('utf-8')).hexdigest()

        session = TermsApprovalSession.objects.create(
            tenant=self.tenant,
            subject_user=self.subject,
            created_by=self.admin,
            purpose='terms_acceptance',
            document_type='terms',
            document_version='2026-01',
            document_hash='hash-abc',
            context_data={'source': 'signup'},
            approval_id='terms_expired',
            challenge_id='challenge-exp',
            token_hash=token_hash,
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        resp = self.client.post(
            '/api/approvals/terms/confirm/',
            {
                'approval_token': approval_token,
                'approved': True,
                'webauthn_response': {'id': 'x', 'rawId': 'y', 'type': 'public-key', 'response': {}},
            },
            format='json',
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(TermsAcceptanceAudit.objects.count(), 1)
        audit = TermsAcceptanceAudit.objects.first()
        self.assertEqual(audit.status, 'expired')
        self.assertEqual(audit.session_id, session.id)
