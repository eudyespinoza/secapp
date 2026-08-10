import sys

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register


@register(Tags.security)
def secureapprove_proof_configuration_check(app_configs, **kwargs):
    errors = []
    enabled = getattr(settings, 'SECUREAPPROVE_PROOF_ENABLED', False)
    marketing = getattr(settings, 'SECUREAPPROVE_PROOF_MARKETING_ENABLED', False)

    if marketing and not enabled:
        errors.append(Warning(
            'SecureApprove Proof marketing is enabled while proof issuance is disabled.',
            hint='Enable issuance only after KMS and WORM smoke tests pass, or disable marketing.',
            id='secureapprove.W001',
        ))
    # Test classes use override_settings(DEBUG=False) to exercise fail-closed
    # behavior. Django imports those classes before running system checks, so
    # production configuration checks must not treat the test runner as a real
    # deployment startup.
    running_tests = 'test' in sys.argv
    if not enabled or settings.DEBUG or running_tests:
        return errors

    signer = getattr(settings, 'SECUREAPPROVE_PROOF_SIGNER', '')
    encryption_backend = getattr(settings, 'SECUREAPPROVE_PROOF_ENCRYPTION_BACKEND', '')
    required = {
        'SECUREAPPROVE_PROOF_SIGNING_KID': 'the public signing key identifier',
        'SECUREAPPROVE_PROOF_ARCHIVE_BUCKET': 'the Object Lock archive bucket',
    }
    if signer == 'aws_kms':
        required.update({
            'SECUREAPPROVE_PROOF_SIGNING_KEY_ARN': 'the AWS KMS asymmetric signing key ARN',
            'AWS_REGION': 'the AWS region',
        })
    elif signer == 'vault_transit':
        required.update({
            'SECUREAPPROVE_VAULT_ADDR': 'the dedicated Vault Proxy URL',
            'SECUREAPPROVE_VAULT_SIGNING_KEY': 'the Vault Transit ecdsa-p256 key name',
            'SECUREAPPROVE_VAULT_TRANSIT_MOUNT': 'the Vault Transit mount name',
        })
    else:
        errors.append(Error(
            'Production SecureApprove Proof signing must use AWS KMS or Vault Transit.',
            id='secureapprove.E002',
        ))

    if encryption_backend == 'aws_kms':
        required.update({
            'SECUREAPPROVE_PROOF_ENCRYPTION_KEY_ARN': 'the AWS KMS evidence key ARN',
            'AWS_REGION': 'the AWS region',
        })
    elif encryption_backend == 'vault_transit':
        required.update({
            'SECUREAPPROVE_VAULT_ADDR': 'the dedicated Vault Proxy URL',
            'SECUREAPPROVE_VAULT_ENCRYPTION_KEY': 'the derived Vault Transit evidence key name',
            'SECUREAPPROVE_VAULT_TRANSIT_MOUNT': 'the Vault Transit mount name',
        })
    else:
        errors.append(Error(
            'Production SecureApprove Proof evidence encryption must use AWS KMS or Vault Transit.',
            id='secureapprove.E003',
        ))
    for setting_name, purpose in required.items():
        if not getattr(settings, setting_name, ''):
            errors.append(Error(
                f'{setting_name} is required when SecureApprove Proof is enabled in production.',
                hint=f'Configure {purpose}.',
                id='secureapprove.E001',
            ))
    if not getattr(settings, 'SECUREAPPROVE_PROOF_ARCHIVE_ENABLED', False):
        errors.append(Error(
            'Production SecureApprove Proof issuance requires the WORM archive.',
            id='secureapprove.E004',
        ))
    return errors
