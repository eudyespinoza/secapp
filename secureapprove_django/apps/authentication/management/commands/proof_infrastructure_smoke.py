import base64
import hashlib
import uuid
from datetime import timedelta
from types import SimpleNamespace

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.authentication.proof_service import (
    ISSUER,
    SCHEMA,
    _encode_jws,
    _encrypt_evidence,
    _kms_client,
    decrypt_evidence,
    sync_active_signing_key,
    verify_compact_jws,
)


class Command(BaseCommand):
    help = 'Smoke-test Proof KMS signing, verification, envelope encryption, and WORM storage.'

    def add_arguments(self, parser):
        parser.add_argument('--skip-archive', action='store_true')

    def handle(self, *args, **options):
        if not getattr(settings, 'SECUREAPPROVE_PROOF_ENABLED', False):
            raise CommandError('SECUREAPPROVE_PROOF_ENABLED must be true for the smoke test.')

        proof_id = uuid.uuid4()
        issued_at = timezone.now()
        signing_key = sync_active_signing_key()
        payload = {
            'iss': ISSUER,
            'jti': str(proof_id),
            'schema': SCHEMA,
            'event_type': 'approval_request',
            'decision': 'approve',
            'issued_at': issued_at.isoformat(),
            'transaction_sha256': '1' * 64,
            'webauthn_assertion_sha256': '2' * 64,
            'previous_ledger_sha256': '',
            'ledger_entry_sha256': '3' * 64,
        }
        jws, _ = _encode_jws(signing_key, payload)
        verify_compact_jws(jws)

        evidence = {'schema': SCHEMA, 'smoke_test': str(proof_id)}
        ciphertext, nonce, encrypted_key = _encrypt_evidence(proof_id, 'smoke-test', evidence)
        envelope = SimpleNamespace(
            id=proof_id,
            tenant_id='smoke-test',
            evidence_ciphertext=ciphertext,
            evidence_nonce=nonce,
            encrypted_data_key=encrypted_key,
            evidence_purged_at=None,
            has_private_evidence=True,
        )
        if decrypt_evidence(envelope) != evidence:
            raise CommandError('Envelope encryption round-trip failed.')

        if getattr(settings, 'SECUREAPPROVE_PROOF_ARCHIVE_ENABLED', False) and not options['skip_archive']:
            bucket = getattr(settings, 'SECUREAPPROVE_PROOF_ARCHIVE_BUCKET', '')
            if not bucket:
                raise CommandError('SECUREAPPROVE_PROOF_ARCHIVE_BUCKET is required.')
            body = jws.encode('utf-8')
            response = _kms_client('s3').put_object(
                Bucket=bucket,
                Key=f'proofs/smoke-tests/{proof_id}.jws',
                Body=body,
                ContentType='application/jose',
                ContentMD5=base64.b64encode(
                    hashlib.md5(body, usedforsecurity=False).digest()
                ).decode('ascii'),
                ObjectLockMode='COMPLIANCE',
                ObjectLockRetainUntilDate=issued_at + timedelta(
                    days=getattr(settings, 'SECUREAPPROVE_PROOF_ARCHIVE_RETENTION_DAYS', 3650)
                ),
                Metadata={'schema': SCHEMA, 'purpose': 'infrastructure-smoke-test'},
            )
            if not response.get('VersionId'):
                raise CommandError('WORM archive write did not return an S3 version ID.')

        self.stdout.write(self.style.SUCCESS(
            f'SecureApprove Proof infrastructure smoke test passed (kid={signing_key.kid}).'
        ))
