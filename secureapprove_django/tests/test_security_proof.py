import base64
import json
import math
import sys
import uuid
from datetime import datetime, timezone as datetime_timezone
from decimal import Decimal
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from django.db import transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import (
    ApprovalAudit,
    ProofLedgerHead,
    ProofSigningKey,
    SecurityProof,
    User,
)
from apps.authentication.proof_service import (
    CHALLENGE_PREFIX,
    InvalidProof,
    ProofUnavailable,
    assertion_private_evidence,
    assertion_sha256,
    build_bound_challenge,
    canonical_json_bytes,
    canonical_json_value,
    decrypt_evidence,
    issue_security_proof,
    sha256_hex,
    sync_active_signing_key,
    transaction_sha256,
    verification_result_for_jws,
    verification_result_for_proof,
    verify_private_evidence_integrity,
    verify_compact_jws,
)
from apps.authentication.checks import secureapprove_proof_configuration_check
from apps.authentication.tasks import purge_expired_proof_evidence
from apps.authentication.webauthn_service import webauthn_service
from apps.requests.models import ApprovalRequest
from apps.tenants.models import Tenant


PROOF_SETTINGS = override_settings(
    DEBUG=False,
    SECUREAPPROVE_PROOF_ENABLED=True,
    SECUREAPPROVE_PROOF_SIGNER='local',
    SECUREAPPROVE_PROOF_ENCRYPTION_BACKEND='local',
    SECUREAPPROVE_PROOF_SIGNING_KID='secureapprove-proof-test-v1',
    SECUREAPPROVE_PROOF_ARCHIVE_ENABLED=False,
)


@PROOF_SETTINGS
class ProofTestBase(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(key=f'tenant-{uuid.uuid4().hex[:8]}', name='Proof Tenant')
        self.admin = User.objects.create_user(
            username=f'admin-{uuid.uuid4().hex[:8]}', email=f'admin-{uuid.uuid4().hex[:8]}@example.test',
            password='test-pass', tenant=self.tenant, role='tenant_admin', name='Admin',
        )
        self.subject = User.objects.create_user(
            username=f'user-{uuid.uuid4().hex[:8]}', email=f'user-{uuid.uuid4().hex[:8]}@example.test',
            password='test-pass', tenant=self.tenant, role='requester', name='Subject',
        )
        self.request_obj = ApprovalRequest.objects.create(
            tenant=self.tenant,
            requester=self.subject,
            title='Treasury transfer',
            description='Approve the immutable treasury batch.',
            category='expense',
            priority='high',
            amount=Decimal('1250.50'),
            metadata={'batch': 'B-42'},
        )

    def snapshot(self, suffix=''):
        return {
            'schema': 'sap-proof-v1',
            'event_type': 'approval_request',
            'request': {
                'id': str(self.request_obj.pk),
                'tenant_id': str(self.tenant.pk),
                'title': self.request_obj.title + suffix,
                'amount': '1250.50',
                'created_at': self.request_obj.created_at,
            },
            'decision': 'approve',
        }

    @staticmethod
    def evidence(suffix=''):
        return {
            'credential_id': 'credential-' + suffix,
            'clientDataJSON': 'client-' + suffix,
            'authenticatorData': 'auth-' + suffix,
            'signature': 'signature-' + suffix,
            'credential_public_key': 'public-key-' + suffix,
            'origin': 'https://secureapprove.com',
            'rp_id_hash': 'ab' * 32,
            'flags': {'UP': True, 'UV': True, 'BE': False, 'BS': False},
        }

    def issue(self, suffix=''):
        snapshot = self.snapshot(suffix)
        with transaction.atomic():
            audit = ApprovalAudit.objects.create(
                approval_request=self.request_obj,
                user=self.admin,
                credential_id='credential-' + suffix,
                challenge_id='challenge-' + suffix,
                action='approve',
                status='success',
                context_data=canonical_json_value(snapshot),
            )
            proof = issue_security_proof(
                tenant=self.tenant,
                subject_user=self.subject,
                actor_user=self.admin,
                event_type='approval_request',
                decision='approve',
                transaction_snapshot=snapshot,
                verification_result={
                    'transaction_sha256': transaction_sha256(snapshot),
                    'proof_evidence': self.evidence(suffix),
                },
                approval_audit=audit,
            )
        return proof


@PROOF_SETTINGS
class ProofCanonicalizationTests(ProofTestBase):
    def test_canonical_object_order_is_deterministic(self):
        self.assertEqual(canonical_json_bytes({'b': 2, 'a': 1}), canonical_json_bytes({'a': 1, 'b': 2}))

    def test_decimal_is_normalized_without_float_rounding(self):
        self.assertEqual(canonical_json_bytes({'amount': Decimal('6500000.00')}), b'{"amount":"6500000.00"}')

    def test_datetime_is_normalized_to_utc(self):
        value = datetime(2026, 1, 2, 3, 4, 5, tzinfo=datetime_timezone.utc)
        self.assertIn(b'2026-01-02T03:04:05.000000Z', canonical_json_bytes({'at': value}))

    def test_non_string_object_key_is_rejected(self):
        with self.assertRaises(ValueError):
            canonical_json_bytes({1: 'invalid'})

    def test_non_finite_number_is_rejected(self):
        with self.assertRaises(ValueError):
            canonical_json_bytes({'amount': math.nan})

    def test_one_byte_change_changes_transaction_digest(self):
        self.assertNotEqual(transaction_sha256(self.snapshot()), transaction_sha256(self.snapshot('x')))

    def test_challenge_contains_prefix_nonce_and_digest(self):
        challenge, digest = build_bound_challenge(self.snapshot(), b'n' * 32)
        self.assertTrue(challenge.startswith(CHALLENGE_PREFIX + b'n' * 32))
        self.assertTrue(challenge.endswith(bytes.fromhex(digest)))

    def test_short_challenge_nonce_is_rejected(self):
        with self.assertRaises(ValueError):
            build_bound_challenge(self.snapshot(), b'short')

    def test_assertion_hash_changes_on_signature_change(self):
        self.assertNotEqual(assertion_sha256(self.evidence('a')), assertion_sha256(self.evidence('b')))

    def test_assertion_evidence_extracts_uv_and_rp_hash(self):
        client = base64.urlsafe_b64encode(json.dumps({'origin': 'https://secureapprove.com'}).encode()).decode().rstrip('=')
        auth = base64.urlsafe_b64encode((b'r' * 32) + bytes([0x05]) + b'c' * 4).decode().rstrip('=')
        evidence = assertion_private_evidence({
            'id': 'cred',
            'response': {'clientDataJSON': client, 'authenticatorData': auth, 'signature': 'sig'},
        }, 'public')
        self.assertTrue(evidence['flags']['UP'])
        self.assertTrue(evidence['flags']['UV'])
        self.assertEqual(evidence['rp_id_hash'], (b'r' * 32).hex())


@PROOF_SETTINGS
class ProofCryptographyTests(ProofTestBase):
    def test_local_signing_key_is_p256_jwk(self):
        key = sync_active_signing_key()
        self.assertEqual(key.public_jwk['crv'], 'P-256')
        self.assertEqual(key.public_jwk['alg'], 'ES256')

    def test_issue_creates_compact_es256_jws(self):
        proof = self.issue('one')
        self.assertEqual(len(proof.jws.split('.')), 3)
        self.assertEqual(verify_compact_jws(proof.jws)['payload']['jti'], str(proof.id))

    def test_der_signature_is_encoded_as_64_byte_jose_signature(self):
        proof = self.issue('raw')
        signature = proof.jws.split('.')[2]
        raw = base64.urlsafe_b64decode(signature + '=' * ((4 - len(signature) % 4) % 4))
        self.assertEqual(len(raw), 64)

    def test_tampered_jws_is_invalid(self):
        proof = self.issue('tamper')
        altered = proof.jws[:-1] + ('A' if proof.jws[-1] != 'A' else 'B')
        with self.assertRaises(InvalidProof):
            verify_compact_jws(altered)

    def test_private_evidence_round_trip(self):
        proof = self.issue('decrypt')
        evidence = decrypt_evidence(proof)
        self.assertEqual(evidence['transaction'], json.loads(canonical_json_bytes(self.snapshot('decrypt'))))
        self.assertTrue(evidence['webauthn']['flags']['UV'])

    def test_proofs_are_chained_per_tenant(self):
        first = self.issue('first')
        second = self.issue('second')
        self.assertEqual(second.previous_ledger_sha256, first.ledger_entry_sha256)
        self.assertEqual(ProofLedgerHead.objects.get(tenant=self.tenant).entry_count, 2)

    def test_transaction_mismatch_prevents_issue(self):
        snapshot = self.snapshot()
        with transaction.atomic(), self.assertRaises(Exception):
            issue_security_proof(
                tenant=self.tenant, subject_user=self.subject, actor_user=self.admin,
                event_type='approval_request', decision='approve', transaction_snapshot=snapshot,
                verification_result={'transaction_sha256': '0' * 64, 'proof_evidence': self.evidence()},
            )

    def test_uv_is_mandatory(self):
        snapshot = self.snapshot()
        evidence = self.evidence()
        evidence['flags']['UV'] = False
        with transaction.atomic(), self.assertRaises(Exception):
            issue_security_proof(
                tenant=self.tenant, subject_user=self.subject, actor_user=self.admin,
                event_type='approval_request', decision='approve', transaction_snapshot=snapshot,
                verification_result={'transaction_sha256': transaction_sha256(snapshot), 'proof_evidence': evidence},
            )

    def test_retention_is_captured_at_issue_time(self):
        self.tenant.proof_retention_years = 1
        self.tenant.save(update_fields=['proof_retention_years'])
        proof = self.issue('retention')
        self.tenant.proof_retention_years = 10
        self.tenant.save(update_fields=['proof_retention_years'])
        self.assertEqual(proof.evidence_expires_at.year, proof.issued_at.year + 1)

    def test_purge_keeps_public_jws_verifiable(self):
        proof = self.issue('purge')
        SecurityProof.objects.filter(pk=proof.pk).update(evidence_expires_at=timezone.now())
        purge_expired_proof_evidence.run()
        proof.refresh_from_db()
        self.assertFalse(proof.has_private_evidence)
        self.assertTrue(verification_result_for_proof(proof)['signature_valid'])

    def test_retired_key_still_verifies_old_proof(self):
        proof = self.issue('old-key')
        proof.signing_key.status = 'retired'
        proof.signing_key.save(update_fields=['status'])
        self.assertTrue(verification_result_for_proof(proof)['valid'])

    def test_compromised_key_is_reported(self):
        proof = self.issue('compromised')
        proof.signing_key.status = 'compromised'
        proof.signing_key.save(update_fields=['status'])
        result = verification_result_for_proof(proof)
        self.assertFalse(result['valid'])
        self.assertEqual(result['status'], 'key_compromised')

    def test_compromised_kid_cannot_be_reactivated(self):
        key = sync_active_signing_key()
        key.status = 'compromised'
        key.save(update_fields=['status'])
        with self.assertRaises(ProofUnavailable):
            sync_active_signing_key()
        key.refresh_from_db()
        self.assertEqual(key.status, 'compromised')

    def test_proof_survives_functional_audit_deletion(self):
        proof = self.issue('retained')
        proof.approval_audit.delete()
        proof.refresh_from_db()
        self.assertIsNone(proof.approval_audit_id)
        self.assertTrue(verification_result_for_proof(proof)['signature_valid'])


@PROOF_SETTINGS
class ProofPublicApiIntegrationTests(ProofTestBase):
    def setUp(self):
        super().setUp()
        self.proof = self.issue('api')
        self.client = Client()

    def test_jwks_contains_active_and_historical_public_keys(self):
        response = self.client.get('/.well-known/secureapprove-proof-jwks.json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['keys'][0]['kty'], 'EC')

    def test_verify_by_id_returns_valid_minimal_result(self):
        response = self.client.get(f'/api/proofs/{self.proof.id}/verify/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['valid'])

    def test_public_verify_response_contains_no_pii(self):
        body = self.client.get(f'/api/proofs/{self.proof.id}/verify/').content.decode()
        self.assertNotIn(self.admin.email, body)
        self.assertNotIn(self.subject.email, body)
        self.assertNotIn(self.tenant.name, body)
        self.assertNotIn('1250.50', body)

    def test_unknown_id_is_not_enumerable(self):
        response = self.client.get(f'/api/proofs/{uuid.uuid4()}/verify/')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'valid': False, 'status': 'unknown'})

    def test_post_verifies_compact_jws(self):
        response = self.client.post('/api/proofs/verify/', {'jws': self.proof.jws}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['valid'])

    def test_post_rejects_modified_jws(self):
        altered = self.proof.jws[:-2] + 'aa'
        response = self.client.post('/api/proofs/verify/', {'jws': altered}, content_type='application/json')
        self.assertFalse(response.json()['valid'])
        self.assertEqual(response.json()['status'], 'altered')

    def test_post_rejects_more_than_16_kb(self):
        response = self.client.post('/api/proofs/verify/', {'jws': 'a' * 17000}, content_type='application/json')
        self.assertIn(response.status_code, {413, 400})

    def test_evidence_requires_authentication(self):
        response = self.client.get(f'/api/proofs/{self.proof.id}/evidence/')
        self.assertIn(response.status_code, {401, 403})

    def test_involved_subject_can_read_evidence(self):
        self.client.force_login(self.subject)
        response = self.client.get(f'/api/proofs/{self.proof.id}/evidence/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('evidence', response.json())

    def test_tenant_admin_can_download_evidence(self):
        self.client.force_login(self.admin)
        response = self.client.get(f'/api/proofs/{self.proof.id}/evidence/?download=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])

    def test_cross_tenant_user_cannot_read_evidence(self):
        other_tenant = Tenant.objects.create(key='other-proof', name='Other')
        outsider = User.objects.create_user(username='outsider', email='outsider@example.test', password='pass', tenant=other_tenant)
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(f'/api/proofs/{self.proof.id}/evidence/').status_code, 403)

    def test_expired_evidence_returns_gone(self):
        SecurityProof.objects.filter(pk=self.proof.pk).update(
            evidence_ciphertext=None, evidence_nonce=None, encrypted_data_key=None, evidence_purged_at=timezone.now()
        )
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(f'/api/proofs/{self.proof.id}/evidence/').status_code, 410)

    def test_one_byte_private_content_change_is_invalid(self):
        evidence = decrypt_evidence(self.proof)
        evidence['transaction']['request']['title'] += 'x'
        result = verify_private_evidence_integrity(self.proof, evidence)
        self.assertFalse(result['valid'])
        self.assertFalse(result['checks']['transaction_sha256'])

    def test_human_verifier_renders_result(self):
        response = self.client.get(f'/en/verify/{self.proof.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Valid proof')

    @override_settings(SECUREAPPROVE_PROOF_MARKETING_ENABLED=True)
    def test_landing_promotes_proof_without_fake_statistics(self):
        response = self.client.get('/en/')
        self.assertContains(response, 'Every approval, bound to the exact content')
        self.assertContains(response, 'Vault Transit')
        self.assertContains(response, 'MinIO Object Lock')
        self.assertContains(response, 'Exact content binding')
        self.assertNotContains(response, 'Seguridad avanzada')
        self.assertNotContains(response, '99.9%')

    @override_settings(SECUREAPPROVE_PROOF_MARKETING_ENABLED=True)
    def test_proof_marketing_is_translated_to_spanish_and_portuguese(self):
        spanish = self.client.get('/es/')
        self.assertContains(spanish, 'Seguridad verificable, no promesas')
        self.assertContains(spanish, 'Vinculación al contenido exacto')
        portuguese = self.client.get('/pt-br/')
        self.assertContains(portuguese, 'Segurança verificável, não promessas')
        self.assertContains(portuguese, 'Vinculação ao conteúdo exato')

    def test_verifier_has_accessible_live_region_and_responsive_breakpoint(self):
        response = self.client.get('/en/verify/')
        self.assertContains(response, 'aria-live="polite"')
        self.assertContains(response, 'id="theme-toggle"')
        self.assertContains(response, '[data-theme="dark"]')
        self.assertContains(response, '@media(max-width:768px)')

    def test_verifier_navigation_is_translated(self):
        self.assertContains(self.client.get('/es/verify/'), 'Volver al inicio')
        self.assertContains(self.client.get('/pt-br/verify/'), 'Voltar ao início')


@PROOF_SETTINGS
class ProofFlowIntegrationTests(ProofTestBase):
    def setUp(self):
        super().setUp()
        previous_origins = list(webauthn_service.allowed_origins)
        self.addCleanup(setattr, webauthn_service, 'allowed_origins', previous_origins)
        webauthn_service.allowed_origins = ['https://secureapprove.com']

    @staticmethod
    def _iframe_assertion():
        client_data = base64.urlsafe_b64encode(json.dumps({
            'type': 'webauthn.get',
            'challenge': 'test',
            'origin': 'https://secureapprove.com',
            'crossOrigin': True,
            'topOrigin': 'https://client.example',
        }).encode()).decode().rstrip('=')
        return {
            'id': 'credential', 'rawId': 'credential', 'type': 'public-key',
            'response': {
                'clientDataJSON': client_data,
                'authenticatorData': 'authenticator',
                'signature': 'signature',
                'userHandle': None,
            },
        }

    @staticmethod
    def _verification_for_context(*args, **kwargs):
        context = kwargs['context_data']
        return {
            'verified': True,
            'credential_id': 'credential',
            'challenge_id': 'challenge',
            'transaction_sha256': transaction_sha256(context),
            'proof_evidence': ProofTestBase.evidence('flow'),
        }

    def _enable_subject_passkey(self):
        self.subject.webauthn_credentials = [{
            'credential_id': 'Y3JlZGVudGlhbA==',
            'credential_public_key': 'cHVibGlj',
            'sign_count': 0,
            'is_active': True,
        }]
        self.subject.save(update_fields=['webauthn_credentials'])

    @patch('apps.authentication.approvals_api_views.webauthn_service.generate_approval_challenge')
    @patch('apps.authentication.approvals_api_views.webauthn_service.verify_approval_response')
    def test_iframe_confirmation_emits_and_status_returns_proof(self, mock_verify, mock_generate):
        self._enable_subject_passkey()
        mock_generate.return_value = {'challengeId': 'challenge', 'challenge': 'test', 'allowCredentials': []}
        mock_verify.side_effect = self._verification_for_context
        client = APIClient()
        client.force_authenticate(self.admin)
        token = client.post('/api/approvals/terms/token/', {
            'user_id': self.subject.pk,
            'purpose': 'terms_acceptance',
            'decision': 'approve',
            'parent_origin': 'https://client.example',
            'document_type': 'terms',
            'document_version': '2026-08',
            'document_hash': 'a' * 64,
            'context': {'reference': 'terms-2026-08'},
        }, format='json')
        client.force_authenticate(user=None)
        confirm = client.post('/api/approvals/terms/confirm/', {
            'approval_token': token.json()['approval_token'],
            'webauthn_response': self._iframe_assertion(),
        }, format='json')
        self.assertEqual(confirm.status_code, 200, confirm.content)
        self.assertIn('proof', confirm.json())
        session_id = confirm.json()['transaction_id']
        client.force_authenticate(self.admin)
        status = client.get(f'/api/approvals/terms/status/{session_id}/')
        self.assertEqual(status.json()['transaction']['proof']['id'], confirm.json()['proof']['id'])

    @patch('apps.requests.webauthn_views.webauthn_service.verify_approval_response')
    def test_dashboard_approval_emits_proof_atomically(self, mock_verify):
        mock_verify.side_effect = self._verification_for_context
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('requests:approval-webauthn-verify', kwargs={'approval_id': self.request_obj.pk}),
            data=json.dumps({'action': 'approve', 'response': {'id': 'credential'}}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn('proof', response.json())
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, 'approved')
        self.assertTrue(SecurityProof.objects.filter(approval_audit__approval_request=self.request_obj).exists())

    @patch('apps.requests.webauthn_views.issue_security_proof', side_effect=ProofUnavailable('kms down'))
    @patch('apps.requests.webauthn_views.webauthn_service.verify_approval_response')
    def test_dashboard_kms_failure_rolls_back_business_decision(self, mock_verify, _mock_issue):
        mock_verify.side_effect = self._verification_for_context
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('requests:approval-webauthn-verify', kwargs={'approval_id': self.request_obj.pk}),
            data=json.dumps({'action': 'approve', 'response': {'id': 'credential'}}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error'], 'proof_signing_unavailable')
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, 'pending')
        self.assertFalse(SecurityProof.objects.exists())

    @patch('apps.authentication.approvals_api_views.issue_security_proof', side_effect=ProofUnavailable('kms down'))
    @patch('apps.authentication.approvals_api_views.webauthn_service.generate_approval_challenge')
    @patch('apps.authentication.approvals_api_views.webauthn_service.verify_approval_response')
    def test_iframe_kms_failure_consumes_token_without_approval(self, mock_verify, mock_generate, _mock_issue):
        self._enable_subject_passkey()
        mock_generate.return_value = {'challengeId': 'challenge', 'challenge': 'test', 'allowCredentials': []}
        mock_verify.side_effect = self._verification_for_context
        client = APIClient()
        client.force_authenticate(self.admin)
        token = client.post('/api/approvals/terms/token/', {
            'user_id': self.subject.pk,
            'purpose': 'terms_acceptance',
            'decision': 'approve',
            'parent_origin': 'https://client.example',
            'document_type': 'terms',
            'document_version': '2026-08',
            'document_hash': 'b' * 64,
        }, format='json')
        client.force_authenticate(user=None)
        response = client.post('/api/approvals/terms/confirm/', {
            'approval_token': token.json()['approval_token'],
            'webauthn_response': self._iframe_assertion(),
        }, format='json')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['error'], 'proof_signing_unavailable')
        self.assertEqual(SecurityProof.objects.count(), 0)


VAULT_PROOF_SETTINGS = override_settings(
    DEBUG=False,
    SECUREAPPROVE_PROOF_ENABLED=True,
    SECUREAPPROVE_PROOF_SIGNER='vault_transit',
    SECUREAPPROVE_PROOF_ENCRYPTION_BACKEND='vault_transit',
    SECUREAPPROVE_PROOF_SIGNING_KID='secureapprove-proof-vault',
    SECUREAPPROVE_VAULT_ADDR='http://vault-proxy:8100',
    SECUREAPPROVE_VAULT_TRANSIT_MOUNT='transit',
    SECUREAPPROVE_VAULT_SIGNING_KEY='secureapprove-proof-signing',
    SECUREAPPROVE_VAULT_ENCRYPTION_KEY='secureapprove-proof-evidence',
    SECUREAPPROVE_PROOF_ARCHIVE_ENABLED=True,
    SECUREAPPROVE_PROOF_ARCHIVE_BUCKET='secureapprove-proofs',
)


@VAULT_PROOF_SETTINGS
class VaultTransitProofTests(ProofTestBase):
    def setUp(self):
        super().setUp()
        # The suite can reuse a PostgreSQL test database after infrastructure
        # smoke tests. Vault kids are immutable, so each mocked key needs a
        # clean signing-key registry.
        ProofSigningKey.objects.all().delete()
        self.vault_private_key = ec.generate_private_key(ec.SECP256R1())
        self.vault_version = 1
        self.data_key = b'v' * 32

    def vault_response(self, method, path, payload=None):
        if path == 'transit/keys/secureapprove-proof-signing':
            public_pem = self.vault_private_key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode('ascii')
            return {
                'latest_version': self.vault_version,
                'keys': {str(self.vault_version): {'public_key': public_pem}},
            }
        if path == 'transit/sign/secureapprove-proof-signing/sha2-256':
            signing_input = base64.b64decode(payload['input'], validate=True)
            der = self.vault_private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
            r, s = decode_dss_signature(der)
            raw = r.to_bytes(32, 'big') + s.to_bytes(32, 'big')
            encoded = base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')
            self.assertEqual(payload['key_version'], self.vault_version)
            return {'signature': f'vault:v{self.vault_version}:{encoded}'}
        if path == 'transit/datakey/plaintext/secureapprove-proof-evidence':
            self.assertEqual(payload['bits'], 256)
            self.assertTrue(payload['context'])
            return {
                'plaintext': base64.b64encode(self.data_key).decode('ascii'),
                'ciphertext': 'vault:v1:wrapped-data-key',
            }
        if path == 'transit/decrypt/secureapprove-proof-evidence':
            self.assertEqual(payload['ciphertext'], 'vault:v1:wrapped-data-key')
            self.assertTrue(payload['context'])
            return {'plaintext': base64.b64encode(self.data_key).decode('ascii')}
        raise AssertionError(f'Unexpected Vault request: {method} {path}')

    @patch('apps.authentication.proof_service._vault_request')
    def test_vault_issues_and_decrypts_a_verifiable_proof(self, vault_request):
        vault_request.side_effect = self.vault_response
        proof = self.issue('vault')
        self.assertEqual(proof.signing_key.kid, 'secureapprove-proof-vault-v1')
        self.assertEqual(
            proof.signing_key.key_arn,
            'vault:transit:secureapprove-proof-signing:v1',
        )
        self.assertTrue(verify_compact_jws(proof.jws)['payload'])
        self.assertEqual(decrypt_evidence(proof)['transaction'], canonical_json_value(self.snapshot('vault')))

    @patch('apps.authentication.proof_service._vault_request')
    def test_vault_signatures_use_64_byte_jose_marshalling(self, vault_request):
        vault_request.side_effect = self.vault_response
        proof = self.issue('vault-jose')
        raw = base64.urlsafe_b64decode(
            proof.jws.split('.')[2] + '=' * ((4 - len(proof.jws.split('.')[2]) % 4) % 4)
        )
        self.assertEqual(len(raw), 64)

    @patch('apps.authentication.proof_service._vault_request')
    def test_vault_kid_cannot_be_rebound_to_different_key_material(self, vault_request):
        vault_request.side_effect = self.vault_response
        sync_active_signing_key()
        self.vault_private_key = ec.generate_private_key(ec.SECP256R1())
        with self.assertRaises(ProofUnavailable):
            sync_active_signing_key()

    @patch('apps.authentication.proof_service._vault_request')
    def test_vault_rotation_is_detected_before_the_next_proof(self, vault_request):
        vault_request.side_effect = self.vault_response
        previous_key = sync_active_signing_key()
        self.vault_version = 2
        self.vault_private_key = ec.generate_private_key(ec.SECP256R1())
        proof = self.issue('rotated')
        previous_key.refresh_from_db()
        self.assertEqual(previous_key.status, 'retired')
        self.assertEqual(proof.signing_key.kid, 'secureapprove-proof-vault-v2')
        self.assertTrue(verify_compact_jws(proof.jws)['payload'])

    def test_production_configuration_accepts_vault_and_worm(self):
        with patch.object(sys, 'argv', ['manage.py', 'check', '--deploy']):
            proof_messages = [
                message for message in secureapprove_proof_configuration_check(None)
                if message.id.startswith('secureapprove.')
            ]
        self.assertEqual(proof_messages, [])

    @override_settings(SECUREAPPROVE_PROOF_SIGNER='local')
    def test_production_configuration_rejects_debug_signer(self):
        with patch.object(sys, 'argv', ['manage.py', 'check', '--deploy']):
            messages = secureapprove_proof_configuration_check(None)
        self.assertIn('secureapprove.E002', {message.id for message in messages})
