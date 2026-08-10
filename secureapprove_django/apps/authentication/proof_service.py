"""SecureApprove Proof canonicalization, signing, encryption, and verification.

The public JWS intentionally contains no tenant, user, network, or business data.
The complete transaction and WebAuthn assertion are encrypted separately.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import math
import os
import sys
import uuid
from datetime import date, datetime, timezone as datetime_timezone
from decimal import Decimal
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)

SCHEMA = 'sap-proof-v1'
CHALLENGE_PREFIX = b'SecureApprove-Proof-v1'
ISSUER = 'https://secureapprove.com'
P256_ORDER = int('FFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551', 16)


class ProofUnavailable(RuntimeError):
    """Raised when Proof is mandatory but cannot be signed or encrypted."""


class InvalidProof(ValueError):
    """Raised when a public proof cannot be parsed or verified."""


def proofs_enabled() -> bool:
    return bool(getattr(settings, 'SECUREAPPROVE_PROOF_ENABLED', False))


def _b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode('ascii')


def _b64url_decode(value: str) -> bytes:
    if not isinstance(value, str):
        raise InvalidProof('Invalid base64url value.')
    return base64.urlsafe_b64decode(value + ('=' * ((4 - len(value) % 4) % 4)))


def _iso8601(value: datetime) -> str:
    if timezone.is_naive(value):
        value = timezone.make_aware(value, datetime_timezone.utc)
    return value.astimezone(datetime_timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _normalize(value: Any) -> Any:
    """Normalize supported values before RFC 8785-style deterministic JSON encoding."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError('Non-finite numbers cannot be canonicalized.')
        return format(Decimal(str(value)), 'f')
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return _iso8601(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return _b64url(value)
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError('Canonical JSON object keys must be strings.')
            normalized[key] = _normalize(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    raise ValueError(f'Unsupported canonical JSON type: {type(value).__name__}')


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _normalize(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
        allow_nan=False,
    ).encode('utf-8')


def canonical_json_value(value: Any) -> Any:
    """Return the normalized structure in a form safe for Django JSONField."""
    return json.loads(canonical_json_bytes(value).decode('utf-8'))


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def transaction_sha256(snapshot: dict) -> str:
    return sha256_hex(canonical_json_bytes(snapshot))


def build_bound_challenge(snapshot: dict, nonce: bytes) -> tuple[bytes, str]:
    digest = transaction_sha256(snapshot)
    if len(nonce) < 32:
        raise ValueError('Proof challenge nonce must contain at least 32 random bytes.')
    return CHALLENGE_PREFIX + nonce + bytes.fromhex(digest), digest


def assertion_private_evidence(credential_data: dict, credential_public_key: str) -> dict:
    response = credential_data.get('response') or {}
    client_data_json = response.get('clientDataJSON', '')
    authenticator_data = response.get('authenticatorData', '')
    signature = response.get('signature', '')
    auth_bytes = _b64url_decode(authenticator_data)
    if len(auth_bytes) < 37:
        raise ValueError('WebAuthn authenticatorData is incomplete.')
    flags = auth_bytes[32]
    client_data = json.loads(_b64url_decode(client_data_json).decode('utf-8'))
    return {
        'credential_id': credential_data.get('id', ''),
        'clientDataJSON': client_data_json,
        'authenticatorData': authenticator_data,
        'signature': signature,
        'credential_public_key': credential_public_key,
        'origin': client_data.get('origin'),
        'cross_origin': client_data.get('crossOrigin') is True,
        'top_origin': client_data.get('topOrigin'),
        'rp_id_hash': auth_bytes[:32].hex(),
        'flags': {
            'UP': bool(flags & 0x01),
            'UV': bool(flags & 0x04),
            'BE': bool(flags & 0x08),
            'BS': bool(flags & 0x10),
        },
    }


def assertion_sha256(evidence: dict) -> str:
    return sha256_hex(canonical_json_bytes({
        'credential_id': evidence.get('credential_id', ''),
        'clientDataJSON': evidence.get('clientDataJSON', ''),
        'authenticatorData': evidence.get('authenticatorData', ''),
        'signature': evidence.get('signature', ''),
        'credential_public_key': evidence.get('credential_public_key', ''),
    }))


def _local_private_key():
    if not settings.DEBUG and 'test' not in sys.argv and not any('pytest' in arg for arg in sys.argv):
        raise ProofUnavailable('Local Proof signer is not allowed in production.')
    seed = hashlib.sha256((settings.SECRET_KEY + ':secureapprove-proof-local-v1').encode()).digest()
    scalar = (int.from_bytes(seed, 'big') % (P256_ORDER - 1)) + 1
    return ec.derive_private_key(scalar, ec.SECP256R1())


def _public_jwk(public_key, kid: str) -> dict:
    numbers = public_key.public_numbers()
    return {
        'kty': 'EC',
        'crv': 'P-256',
        'use': 'sig',
        'alg': 'ES256',
        'kid': kid,
        'x': _b64url(numbers.x.to_bytes(32, 'big')),
        'y': _b64url(numbers.y.to_bytes(32, 'big')),
    }


def _kms_client(service='kms'):
    try:
        import boto3
    except ImportError as exc:
        raise ProofUnavailable('AWS SDK is unavailable.') from exc
    kwargs = {}
    region = getattr(settings, 'AWS_REGION', '')
    if region:
        kwargs['region_name'] = region
    return boto3.client(service, **kwargs)


def sync_active_signing_key():
    from apps.authentication.models import ProofSigningKey

    signer = getattr(settings, 'SECUREAPPROVE_PROOF_SIGNER', 'aws_kms')
    kid = getattr(settings, 'SECUREAPPROVE_PROOF_SIGNING_KID', '')
    if signer == 'local':
        kid = kid or 'secureapprove-proof-local-v1'
        key_arn = ''
        jwk = _public_jwk(_local_private_key().public_key(), kid)
    else:
        key_arn = getattr(settings, 'SECUREAPPROVE_PROOF_SIGNING_KEY_ARN', '')
        if not key_arn or not kid:
            raise ProofUnavailable('Proof signing key ARN and kid are required.')
        try:
            response = _kms_client().get_public_key(KeyId=key_arn)
            public_key = serialization.load_der_public_key(response['PublicKey'])
        except Exception as exc:
            _metric('kms_signing_key_failures')
            raise ProofUnavailable('AWS KMS signing key is unavailable.') from exc
        if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(public_key.curve, ec.SECP256R1):
            raise ProofUnavailable('Proof signing key must be ECC_NIST_P256.')
        jwk = _public_jwk(public_key, kid)

    existing_key = ProofSigningKey.objects.filter(kid=kid).first()
    if existing_key and existing_key.status == 'compromised':
        raise ProofUnavailable(
            'The configured proof signing kid is marked as compromised; rotate to a new kid.'
        )

    key, _ = ProofSigningKey.objects.update_or_create(
        kid=kid,
        defaults={
            'key_arn': key_arn,
            'algorithm': 'ES256',
            'public_jwk': jwk,
            'status': 'active',
        },
    )
    ProofSigningKey.objects.filter(status='active').exclude(pk=key.pk).update(
        status='retired', deactivated_at=timezone.now()
    )
    return key


def _active_signing_key():
    from apps.authentication.models import ProofSigningKey

    key = ProofSigningKey.objects.filter(status='active').order_by('-activated_at').first()
    expected_kid = getattr(settings, 'SECUREAPPROVE_PROOF_SIGNING_KID', '')
    if key and (not expected_kid or key.kid == expected_kid):
        return key
    return sync_active_signing_key()


def _sign_es256(signing_key, signing_input: bytes) -> bytes:
    signer = getattr(settings, 'SECUREAPPROVE_PROOF_SIGNER', 'aws_kms')
    if signer == 'local':
        der_signature = _local_private_key().sign(signing_input, ec.ECDSA(hashes.SHA256()))
    else:
        try:
            response = _kms_client().sign(
                KeyId=signing_key.key_arn,
                Message=signing_input,
                MessageType='RAW',
                SigningAlgorithm='ECDSA_SHA_256',
            )
            der_signature = response['Signature']
        except Exception as exc:
            _metric('kms_signing_failures')
            raise ProofUnavailable('AWS KMS could not sign the proof.') from exc
    r, s = decode_dss_signature(der_signature)
    return r.to_bytes(32, 'big') + s.to_bytes(32, 'big')


def _encode_jws(signing_key, payload: dict) -> tuple[str, dict]:
    protected = {'alg': 'ES256', 'kid': signing_key.kid, 'typ': 'JOSE'}
    signing_input = (
        _b64url(canonical_json_bytes(protected)) + '.' + _b64url(canonical_json_bytes(payload))
    ).encode('ascii')
    signature = _sign_es256(signing_key, signing_input)
    return signing_input.decode('ascii') + '.' + _b64url(signature), protected


def _encryption_aad(proof_id, tenant_id) -> bytes:
    return canonical_json_bytes({'proof_id': str(proof_id), 'schema': SCHEMA, 'tenant_id': str(tenant_id)})


def _encrypt_evidence(proof_id, tenant_id, evidence: dict) -> tuple[bytes, bytes, bytes]:
    backend = getattr(settings, 'SECUREAPPROVE_PROOF_ENCRYPTION_BACKEND', 'aws_kms')
    aad = _encryption_aad(proof_id, tenant_id)
    if backend == 'local':
        if not settings.DEBUG and 'test' not in sys.argv and not any('pytest' in arg for arg in sys.argv):
            raise ProofUnavailable('Local Proof encryption is not allowed in production.')
        data_key = hashlib.sha256((settings.SECRET_KEY + ':secureapprove-proof-evidence-v1').encode()).digest()
        encrypted_data_key = b'local-v1'
    else:
        key_arn = getattr(settings, 'SECUREAPPROVE_PROOF_ENCRYPTION_KEY_ARN', '')
        if not key_arn:
            raise ProofUnavailable('Proof encryption key ARN is required.')
        try:
            response = _kms_client().generate_data_key(
                KeyId=key_arn,
                KeySpec='AES_256',
                EncryptionContext={'proof_id': str(proof_id), 'schema': SCHEMA},
            )
            data_key = response['Plaintext']
            encrypted_data_key = response['CiphertextBlob']
        except Exception as exc:
            _metric('kms_encryption_failures')
            raise ProofUnavailable('AWS KMS could not create an evidence key.') from exc
    nonce = os.urandom(12)
    ciphertext = AESGCM(data_key).encrypt(nonce, canonical_json_bytes(evidence), aad)
    return ciphertext, nonce, encrypted_data_key


def decrypt_evidence(proof) -> dict:
    if not proof.has_private_evidence:
        raise InvalidProof('Private evidence has expired.')
    backend = getattr(settings, 'SECUREAPPROVE_PROOF_ENCRYPTION_BACKEND', 'aws_kms')
    if backend == 'local':
        data_key = hashlib.sha256((settings.SECRET_KEY + ':secureapprove-proof-evidence-v1').encode()).digest()
    else:
        try:
            response = _kms_client().decrypt(
                CiphertextBlob=bytes(proof.encrypted_data_key),
                KeyId=getattr(settings, 'SECUREAPPROVE_PROOF_ENCRYPTION_KEY_ARN', ''),
                EncryptionContext={'proof_id': str(proof.id), 'schema': SCHEMA},
            )
            data_key = response['Plaintext']
        except Exception as exc:
            raise InvalidProof('Private evidence could not be decrypted.') from exc
    plaintext = AESGCM(data_key).decrypt(
        bytes(proof.evidence_nonce),
        bytes(proof.evidence_ciphertext),
        _encryption_aad(proof.id, proof.tenant_id),
    )
    return json.loads(plaintext.decode('utf-8'))


def verify_private_evidence_integrity(proof, evidence: dict) -> dict:
    """Re-verify the retained transaction, ledger entry, and WebAuthn assertion.

    This is intentionally separate from public verification because the private
    snapshot can contain tenant and business data. Only the authorized evidence
    endpoint exposes this result.
    """
    checks = {
        'public_payload': False,
        'transaction_sha256': False,
        'webauthn_assertion_sha256': False,
        'ledger_entry_sha256': False,
        'challenge_binding': False,
        'rp_id_hash': False,
        'user_presence': False,
        'user_verification': False,
        'webauthn_signature': False,
    }
    try:
        private_public = evidence['public']
        transaction_snapshot = evidence['transaction']
        assertion = evidence['webauthn']
        checks['public_payload'] = private_public == proof.public_payload

        transaction_digest = transaction_sha256(transaction_snapshot)
        checks['transaction_sha256'] = hmac.compare_digest(
            transaction_digest, proof.transaction_sha256
        ) and hmac.compare_digest(
            transaction_digest, str(private_public.get('transaction_sha256', ''))
        )

        assertion_digest = assertion_sha256(assertion)
        checks['webauthn_assertion_sha256'] = hmac.compare_digest(
            assertion_digest, proof.webauthn_assertion_sha256
        ) and hmac.compare_digest(
            assertion_digest, str(private_public.get('webauthn_assertion_sha256', ''))
        )

        expected_ledger_digest = transaction_sha256({
            'proof_id': str(proof.id),
            'tenant_id': str(proof.tenant_id),
            'transaction_sha256': proof.transaction_sha256,
            'webauthn_assertion_sha256': proof.webauthn_assertion_sha256,
            'previous_ledger_sha256': proof.previous_ledger_sha256,
            'issued_at': proof.issued_at,
        })
        checks['ledger_entry_sha256'] = hmac.compare_digest(
            expected_ledger_digest, proof.ledger_entry_sha256
        ) and hmac.compare_digest(
            expected_ledger_digest, str(private_public.get('ledger_entry_sha256', ''))
        )

        client_data_raw = _b64url_decode(assertion['clientDataJSON'])
        client_data = json.loads(client_data_raw.decode('utf-8'))
        challenge = _b64url_decode(client_data['challenge'])
        checks['challenge_binding'] = (
            client_data.get('type') == 'webauthn.get'
            and challenge.startswith(CHALLENGE_PREFIX)
            and challenge.endswith(bytes.fromhex(proof.transaction_sha256))
            and client_data.get('origin') == assertion.get('origin')
        )

        authenticator_data = _b64url_decode(assertion['authenticatorData'])
        if len(authenticator_data) < 37:
            raise InvalidProof('WebAuthn authenticator data is incomplete.')
        rp_id_hash = authenticator_data[:32]
        expected_rp_id_hash = hashlib.sha256(
            getattr(settings, 'WEBAUTHN_RP_ID', 'localhost').encode('utf-8')
        ).digest()
        checks['rp_id_hash'] = (
            hmac.compare_digest(rp_id_hash, expected_rp_id_hash)
            and hmac.compare_digest(rp_id_hash.hex(), str(assertion.get('rp_id_hash', '')))
        )
        flags = authenticator_data[32]
        checks['user_presence'] = bool(flags & 0x01) and assertion.get('flags', {}).get('UP') is True
        checks['user_verification'] = bool(flags & 0x04) and assertion.get('flags', {}).get('UV') is True

        from webauthn.helpers import (
            decode_credential_public_key,
            decoded_public_key_to_cryptography,
            verify_signature,
        )
        decoded_public_key = decode_credential_public_key(
            _b64url_decode(assertion['credential_public_key'])
        )
        crypto_public_key = decoded_public_key_to_cryptography(decoded_public_key)
        verify_signature(
            public_key=crypto_public_key,
            signature_alg=decoded_public_key.alg,
            signature=_b64url_decode(assertion['signature']),
            data=authenticator_data + hashlib.sha256(client_data_raw).digest(),
        )
        checks['webauthn_signature'] = True
    except Exception as exc:
        logger.info('Private SecureApprove Proof evidence is invalid: proof=%s error=%s', proof.id, exc)

    return {
        'valid': all(checks.values()),
        'checks': checks,
    }


def _retention_date(issued_at: datetime, years: int) -> datetime:
    try:
        return issued_at.replace(year=issued_at.year + years)
    except ValueError:
        return issued_at.replace(month=2, day=28, year=issued_at.year + years)


def _metric(name: str):
    try:
        cache.incr(f'secureapprove_proof_metric:{name}')
    except ValueError:
        cache.set(f'secureapprove_proof_metric:{name}', 1, timeout=None)
    except Exception:
        logger.debug('Proof metric unavailable: %s', name, exc_info=True)


def issue_security_proof(
    *,
    tenant,
    subject_user,
    actor_user,
    event_type: str,
    decision: str,
    transaction_snapshot: dict,
    verification_result: dict,
    approval_audit=None,
    terms_audit=None,
):
    """Issue one proof. Caller must wrap the business update in transaction.atomic()."""
    from apps.authentication.models import ProofLedgerHead, SecurityProof

    if not proofs_enabled():
        return None
    if transaction.get_connection().in_atomic_block is False:
        raise RuntimeError('SecurityProof issuance requires transaction.atomic().')

    digest = transaction_sha256(transaction_snapshot)
    bound_digest = verification_result.get('transaction_sha256')
    if not bound_digest or bound_digest != digest:
        _metric('transaction_mismatch')
        raise ProofUnavailable('The signed transaction no longer matches the current content.')

    webauthn_evidence = verification_result.get('proof_evidence')
    if not webauthn_evidence or not webauthn_evidence.get('flags', {}).get('UV'):
        raise ProofUnavailable('WebAuthn user verification evidence is required.')
    assertion_digest = assertion_sha256(webauthn_evidence)

    head, _ = ProofLedgerHead.objects.get_or_create(tenant=tenant)
    head = ProofLedgerHead.objects.select_for_update().get(pk=head.pk)
    signing_key = _active_signing_key()
    proof_id = uuid.uuid4()
    issued_at = timezone.now()
    previous_hash = head.last_entry_sha256
    ledger_hash = transaction_sha256({
        'proof_id': str(proof_id),
        'tenant_id': str(tenant.pk),
        'transaction_sha256': digest,
        'webauthn_assertion_sha256': assertion_digest,
        'previous_ledger_sha256': previous_hash,
        'issued_at': issued_at,
    })
    public_payload = {
        'iss': ISSUER,
        'jti': str(proof_id),
        'schema': SCHEMA,
        'event_type': event_type,
        'decision': decision,
        'issued_at': _iso8601(issued_at),
        'transaction_sha256': digest,
        'webauthn_assertion_sha256': assertion_digest,
        'previous_ledger_sha256': previous_hash,
        'ledger_entry_sha256': ledger_hash,
    }
    jws, protected = _encode_jws(signing_key, public_payload)
    private_evidence = {
        'schema': SCHEMA,
        'transaction': transaction_snapshot,
        'webauthn': webauthn_evidence,
        'public': public_payload,
    }
    ciphertext, nonce, encrypted_key = _encrypt_evidence(proof_id, tenant.pk, private_evidence)
    years = int(getattr(tenant, 'proof_retention_years', 7))
    archive_status = 'pending' if getattr(settings, 'SECUREAPPROVE_PROOF_ARCHIVE_ENABLED', True) else 'disabled'
    proof = SecurityProof.objects.create(
        id=proof_id,
        tenant=tenant,
        subject_user=subject_user,
        actor_user=actor_user,
        approval_audit=approval_audit,
        terms_audit=terms_audit,
        event_type=event_type,
        decision=decision,
        transaction_sha256=digest,
        webauthn_assertion_sha256=assertion_digest,
        previous_ledger_sha256=previous_hash,
        ledger_entry_sha256=ledger_hash,
        signing_key=signing_key,
        protected_header=protected,
        public_payload=public_payload,
        jws=jws,
        evidence_ciphertext=ciphertext,
        evidence_nonce=nonce,
        encrypted_data_key=encrypted_key,
        evidence_expires_at=_retention_date(issued_at, years),
        archive_status=archive_status,
        issued_at=issued_at,
    )
    head.last_entry_sha256 = ledger_hash
    head.entry_count += 1
    head.save(update_fields=['last_entry_sha256', 'entry_count', 'updated_at'])
    _metric('issued')

    if archive_status == 'pending':
        def enqueue_archive():
            from apps.authentication.tasks import archive_security_proof
            archive_security_proof.delay(str(proof.id))
        transaction.on_commit(enqueue_archive)
    return proof


def verify_compact_jws(jws: str) -> dict:
    from apps.authentication.models import ProofSigningKey

    if not isinstance(jws, str) or len(jws.encode('utf-8')) > 16384:
        raise InvalidProof('Proof exceeds the 16 KB limit.')
    parts = jws.split('.')
    if len(parts) != 3:
        raise InvalidProof('Proof must be a compact JWS.')
    try:
        decoded_parts = [_b64url_decode(part) for part in parts]
        if any(_b64url(decoded) != encoded for decoded, encoded in zip(decoded_parts, parts)):
            raise InvalidProof('Proof base64url encoding is not canonical.')
        header = json.loads(decoded_parts[0].decode('utf-8'))
        payload = json.loads(decoded_parts[1].decode('utf-8'))
        signature = decoded_parts[2]
    except InvalidProof:
        raise
    except Exception as exc:
        raise InvalidProof('Proof encoding is invalid.') from exc
    if header.get('alg') != 'ES256' or header.get('typ') != 'JOSE' or not header.get('kid'):
        raise InvalidProof('Proof header is invalid.')
    if payload.get('iss') != ISSUER or payload.get('schema') != SCHEMA:
        raise InvalidProof('Proof issuer or schema is invalid.')
    key = ProofSigningKey.objects.filter(kid=header['kid']).first()
    if not key:
        raise InvalidProof('Unknown signing key.')
    if len(signature) != 64:
        raise InvalidProof('ES256 signature has an invalid length.')
    jwk = key.public_jwk
    try:
        public_numbers = ec.EllipticCurvePublicNumbers(
            int.from_bytes(_b64url_decode(jwk['x']), 'big'),
            int.from_bytes(_b64url_decode(jwk['y']), 'big'),
            ec.SECP256R1(),
        )
        der_signature = encode_dss_signature(
            int.from_bytes(signature[:32], 'big'),
            int.from_bytes(signature[32:], 'big'),
        )
        public_numbers.public_key().verify(
            der_signature,
            f'{parts[0]}.{parts[1]}'.encode('ascii'),
            ec.ECDSA(hashes.SHA256()),
        )
    except Exception as exc:
        raise InvalidProof('Proof signature is invalid.') from exc
    return {'header': header, 'payload': payload, 'key': key}


def verification_result_for_proof(proof) -> dict:
    """Return the minimal, PII-free public verification result for a stored proof."""
    try:
        verified = verify_compact_jws(proof.jws)
    except InvalidProof as exc:
        _metric('verification_invalid')
        return {
            'valid': False,
            'signature_valid': False,
            'status': 'altered',
            'proof_id': str(proof.id),
            'detail': str(exc),
        }
    payload = verified['payload']
    matches_record = (
        payload == proof.public_payload
        and payload.get('jti') == str(proof.id)
        and payload.get('transaction_sha256') == proof.transaction_sha256
        and payload.get('ledger_entry_sha256') == proof.ledger_entry_sha256
    )
    if not matches_record:
        _metric('verification_invalid')
        return {
            'valid': False,
            'signature_valid': True,
            'status': 'altered',
            'proof_id': str(proof.id),
            'detail': 'The signed payload does not match the registered proof.',
        }
    key_compromised = verified['key'].status == 'compromised'
    evidence_status = 'expired' if not proof.has_private_evidence else 'retained'
    status = 'key_compromised' if key_compromised else ('evidence_expired' if evidence_status == 'expired' else 'valid')
    _metric('verified')
    return {
        'valid': not key_compromised,
        'signature_valid': True,
        'status': status,
        'proof_id': str(proof.id),
        'schema': proof.schema,
        'event_type': proof.event_type,
        'decision': proof.decision,
        'issued_at': _iso8601(proof.issued_at),
        'transaction_sha256': proof.transaction_sha256,
        'webauthn_assertion_sha256': proof.webauthn_assertion_sha256,
        'ledger_entry_sha256': proof.ledger_entry_sha256,
        'archive_status': proof.archive_status,
        'evidence_status': evidence_status,
        'signing_key_status': verified['key'].status,
    }


def verification_result_for_jws(jws: str) -> dict:
    from apps.authentication.models import SecurityProof

    try:
        verified = verify_compact_jws(jws)
    except InvalidProof as exc:
        _metric('verification_invalid')
        return {'valid': False, 'signature_valid': False, 'status': 'altered', 'detail': str(exc)}
    proof_id = verified['payload'].get('jti')
    try:
        parsed_id = uuid.UUID(str(proof_id))
    except (TypeError, ValueError):
        return {'valid': False, 'signature_valid': True, 'status': 'unknown'}
    proof = SecurityProof.objects.select_related('signing_key').filter(pk=parsed_id).first()
    if not proof or proof.jws != jws:
        return {'valid': False, 'signature_valid': True, 'status': 'unknown', 'proof_id': str(parsed_id)}
    return verification_result_for_proof(proof)


def proof_api_payload(proof, request=None) -> dict:
    path = reverse('landing:proof_verify_id', kwargs={'proof_id': proof.id})
    if request:
        verify_url = request.build_absolute_uri(path)
    else:
        verify_url = f"{ISSUER}{path if path.startswith('/') else '/' + path}"
    return {
        'id': str(proof.id),
        'schema': proof.schema,
        'jws': proof.jws,
        'verify_url': verify_url,
        'issued_at': _iso8601(proof.issued_at),
        'transaction_sha256': proof.transaction_sha256,
        'archive_status': proof.archive_status,
    }
