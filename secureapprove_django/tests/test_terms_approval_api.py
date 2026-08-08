import base64
import json
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import TermsAcceptanceAudit, TermsApprovalSession, User
from apps.authentication.webauthn_service import webauthn_service
from apps.tenants.models import Tenant


class TermsApprovalAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        previous_origins = list(webauthn_service.allowed_origins)
        self.addCleanup(setattr, webauthn_service, 'allowed_origins', previous_origins)
        webauthn_service.allowed_origins = ['https://secureapprove.com']
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

    @staticmethod
    def _client_data(top_origin='https://client.example'):
        value = json.dumps({
            'type': 'webauthn.get',
            'challenge': 'Y2hhbGxlbmdl',
            'origin': 'https://secureapprove.com',
            'crossOrigin': True,
            'topOrigin': top_origin,
        }).encode('utf-8')
        return base64.urlsafe_b64encode(value).decode('ascii').rstrip('=')

    def _assertion(self, top_origin='https://client.example'):
        return {
            'id': 'x',
            'rawId': 'y',
            'type': 'public-key',
            'response': {
                'clientDataJSON': self._client_data(top_origin),
                'authenticatorData': 'authenticator-data',
                'signature': 'signature',
                'userHandle': None,
            },
        }

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
                'decision': 'approve',
                'parent_origin': 'https://client.example',
                'document_type': 'terms',
                'document_version': '2026-01',
                'document_hash': 'a' * 64,
                'context': {'source': 'signup'},
            },
            format='json',
        )

        self.assertEqual(token_resp.status_code, 201)
        self.assertEqual(token_resp['Cache-Control'], 'no-store, max-age=0')
        approval_token = token_resp.json()['approval_token']

        confirm_resp = self.client.post(
            '/api/approvals/terms/confirm/',
            {
                'approval_token': approval_token,
                'approved': False,
                'webauthn_response': self._assertion(),
            },
            format='json',
        )

        self.assertEqual(confirm_resp.status_code, 200, confirm_resp.content)
        self.assertTrue(confirm_resp.json()['success'])
        self.assertTrue(confirm_resp.json()['approved'])
        self.assertEqual(confirm_resp.json()['status'], 'approved')
        self.assertTrue(confirm_resp.json()['verification_passed'])

        self.assertEqual(TermsAcceptanceAudit.objects.count(), 1)
        audit = TermsAcceptanceAudit.objects.first()
        self.assertEqual(audit.status, 'success')
        self.assertEqual(audit.user_id, self.subject.id)
        self.assertEqual(audit.tenant_id, self.tenant.id)

        session = TermsApprovalSession.objects.first()
        self.assertIsNotNone(session.consumed_at)
        self.assertEqual(session.result_status, 'approved')

        self.client.force_authenticate(user=self.admin)
        status_resp = self.client.get(f'/api/approvals/terms/status/{session.id}/')
        self.assertEqual(status_resp.status_code, 200)
        self.assertEqual(status_resp['Cache-Control'], 'no-store, max-age=0')
        self.assertTrue(status_resp.json()['authenticated'])
        self.assertTrue(status_resp.json()['verification_passed'])
        self.assertEqual(status_resp.json()['transaction']['decision'], 'approve')
        self.assertTrue(status_resp.json()['transaction']['verificationPassed'])

    @patch('apps.authentication.approvals_api_views.webauthn_service.verify_approval_response')
    def test_confirm_rejects_unexpected_top_origin(self, mock_verify):
        self.client.force_authenticate(user=self.admin)
        token_resp = self.client.post(
            '/api/approvals/terms/token/',
            {
                'user_id': self.subject.id,
                'purpose': 'terms_acceptance',
                'decision': 'approve',
                'parent_origin': 'https://client.example',
                'document_type': 'terms',
                'document_version': '2026-01',
                'document_hash': 'b' * 64,
            },
            format='json',
        )
        self.client.force_authenticate(user=None)

        confirm_resp = self.client.post(
            '/api/approvals/terms/confirm/',
            {
                'approval_token': token_resp.json()['approval_token'],
                'webauthn_response': self._assertion('https://attacker.example'),
            },
            format='json',
        )

        self.assertEqual(confirm_resp.status_code, 400)
        self.assertFalse(mock_verify.called)
        session = TermsApprovalSession.objects.get()
        self.assertEqual(session.result_status, 'failed')
        self.assertIsNotNone(session.consumed_at)
        self.assertEqual(TermsAcceptanceAudit.objects.get().status, 'failed')

    def test_token_requires_sha256_document_hash_and_parent_origin(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            '/api/approvals/terms/token/',
            {
                'user_id': self.subject.id,
                'document_type': 'terms',
                'document_version': '2026-01',
                'document_hash': '',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_parent_origin_is_canonicalized_and_rejects_browser_ambiguous_input(self):
        from apps.authentication.approvals_api_serializers import normalize_parent_origin
        from rest_framework.serializers import ValidationError

        self.assertEqual(normalize_parent_origin('https://client.example:443/'), 'https://client.example')
        self.assertEqual(normalize_parent_origin('http://localhost:80'), 'http://localhost')
        with self.assertRaises(ValidationError):
            normalize_parent_origin('https://client.example\\@attacker.example')

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
            document_hash='c' * 64,
            decision='approve',
            parent_origin='https://client.example',
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
                'webauthn_response': self._assertion(),
            },
            format='json',
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(TermsAcceptanceAudit.objects.count(), 1)
        audit = TermsAcceptanceAudit.objects.first()
        self.assertEqual(audit.status, 'expired')
        self.assertEqual(audit.session_id, session.id)
        session.refresh_from_db()
        self.assertEqual(session.result_status, 'expired')
        self.assertIsNotNone(session.consumed_at)

    def test_fallback_credential_endpoint_is_disabled(self):
        response = self.client.post(
            '/en/auth/webauthn/fallback/',
            {'userId': self.subject.id},
            format='json',
        )
        self.assertEqual(response.status_code, 410)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_embed_response_delegates_webauthn_only_to_requested_parent(self):
        response = self.client.get(
            '/en/embed/secureapprove/',
            {
                'parent_origin': 'https://client.example',
                'nonce': 'a' * 32,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Permissions-Policy'], 'publickey-credentials-get=*')
        self.assertIn('frame-ancestors https://client.example', response['Content-Security-Policy'])
        self.assertEqual(response['Cache-Control'], 'no-store, max-age=0')

    def test_embed_rejects_invalid_parent_origin(self):
        response = self.client.get(
            '/en/embed/secureapprove/',
            {
                'parent_origin': 'https://client.example/path',
                'nonce': 'a' * 32,
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_integration_guide_renders_server_verified_login_exchange(self):
        self.client.force_authenticate(user=None)
        self.client.force_login(self.admin)
        response = self.client.get('/en/dashboard/integrations/iframe/')

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertContains(response, 'pendingSecureApprove')
        self.assertContains(response, 'secureapprove_transaction_mismatch')
        self.assertContains(response, 'transaction.parentOrigin === pending.parentOrigin')
        self.assertContains(response, '/api/secureapprove/session')
        self.assertContains(response, 'Iframe code ready to copy')
        self.assertContains(response, 'id="frontendSnippet"')
        self.assertContains(response, 'Object.values(cfg)')
        self.assertIn('<\\/script>', content)
        self.assertNotIn('`<script src="${q(c.loaderUrl)}"></script>', content)
        self.assertLess(content.index('id="frontendSnippet"'), content.index('id="cfgEnvironment"'))
