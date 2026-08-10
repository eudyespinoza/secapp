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

    required = {
        'SECUREAPPROVE_PROOF_SIGNING_KEY_ARN': 'the AWS KMS asymmetric signing key ARN',
        'SECUREAPPROVE_PROOF_SIGNING_KID': 'the public signing key identifier',
        'SECUREAPPROVE_PROOF_ENCRYPTION_KEY_ARN': 'the AWS KMS evidence key ARN',
        'SECUREAPPROVE_PROOF_ARCHIVE_BUCKET': 'the Object Lock archive bucket',
        'AWS_REGION': 'the AWS region',
    }
    for setting_name, purpose in required.items():
        if not getattr(settings, setting_name, ''):
            errors.append(Error(
                f'{setting_name} is required when SecureApprove Proof is enabled in production.',
                hint=f'Configure {purpose}.',
                id='secureapprove.E001',
            ))
    if getattr(settings, 'SECUREAPPROVE_PROOF_SIGNER', '') != 'aws_kms':
        errors.append(Error(
            'Production SecureApprove Proof signing must use AWS KMS.',
            id='secureapprove.E002',
        ))
    if getattr(settings, 'SECUREAPPROVE_PROOF_ENCRYPTION_BACKEND', '') != 'aws_kms':
        errors.append(Error(
            'Production SecureApprove Proof evidence encryption must use AWS KMS.',
            id='secureapprove.E003',
        ))
    if not getattr(settings, 'SECUREAPPROVE_PROOF_ARCHIVE_ENABLED', False):
        errors.append(Error(
            'Production SecureApprove Proof issuance requires the WORM archive.',
            id='secureapprove.E004',
        ))
    return errors
