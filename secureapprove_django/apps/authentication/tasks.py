import base64
import hashlib
import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=12)
def archive_security_proof(self, proof_id):
    """Archive a public JWS in the Object Lock Compliance bucket."""
    from apps.authentication.models import SecurityProof
    from apps.authentication.proof_service import _s3_client

    proof = SecurityProof.objects.filter(pk=proof_id).first()
    if not proof or proof.archive_status in {'archived', 'disabled'}:
        return

    bucket = getattr(settings, 'SECUREAPPROVE_PROOF_ARCHIVE_BUCKET', '')
    if not bucket:
        proof.archive_status = 'failed'
        proof.archive_error = 'Archive bucket is not configured.'
        proof.save(update_fields=['archive_status', 'archive_error'])
        raise self.retry(
            exc=RuntimeError('SecureApprove Proof archive bucket is not configured.'),
            countdown=min(300, 2 ** min(self.request.retries + 1, 8)),
        )

    object_key = f"proofs/{proof.issued_at:%Y/%m/%d}/{proof.id}.jws"
    body = proof.jws.encode('utf-8')
    retain_until = timezone.now() + timedelta(
        days=getattr(settings, 'SECUREAPPROVE_PROOF_ARCHIVE_RETENTION_DAYS', 3650)
    )
    try:
        response = _s3_client().put_object(
            Bucket=bucket,
            Key=object_key,
            Body=body,
            ContentType='application/jose',
            ContentMD5=base64.b64encode(hashlib.md5(body, usedforsecurity=False).digest()).decode('ascii'),
            ObjectLockMode='COMPLIANCE',
            ObjectLockRetainUntilDate=retain_until,
            Metadata={
                'schema': proof.schema,
                'ledger-entry-sha256': proof.ledger_entry_sha256,
            },
        )
    except Exception as exc:
        status = 'delayed' if timezone.now() - proof.created_at >= timedelta(minutes=5) else 'failed'
        SecurityProof.objects.filter(pk=proof.pk).update(
            archive_status=status,
            archive_error=str(exc)[:2000],
        )
        logger.exception('SecureApprove Proof archive failed: proof=%s', proof.id)
        raise self.retry(exc=exc, countdown=min(300, 2 ** min(self.request.retries + 1, 8)))

    SecurityProof.objects.filter(pk=proof.pk).update(
        archive_status='archived',
        archive_object_key=object_key,
        archive_version_id=response.get('VersionId', ''),
        archived_at=timezone.now(),
        archive_error='',
    )


@shared_task
def monitor_delayed_proof_archives():
    from apps.authentication.models import SecurityProof

    cutoff = timezone.now() - timedelta(minutes=5)
    delayed = SecurityProof.objects.filter(
        archive_status__in=['pending', 'failed'],
        created_at__lte=cutoff,
    )
    count = delayed.update(archive_status='delayed')
    if count:
        logger.critical('SecureApprove Proof archive delay exceeds five minutes: count=%s', count)
    return count


@shared_task
def purge_expired_proof_evidence():
    """Cryptographically erase envelope-encrypted evidence while retaining public proof data."""
    from apps.authentication.models import SecurityProof

    now = timezone.now()
    queryset = SecurityProof.objects.filter(
        evidence_expires_at__lte=now,
        evidence_purged_at__isnull=True,
    )
    count = queryset.update(
        evidence_ciphertext=None,
        evidence_nonce=None,
        encrypted_data_key=None,
        evidence_purged_at=now,
    )
    if count:
        logger.info('Purged expired SecureApprove Proof evidence: count=%s', count)
    return count
