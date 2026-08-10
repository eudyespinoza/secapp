# SecureApprove Proof operations runbook

## Annual asymmetric-key rotation

AWS KMS does not automatically rotate asymmetric keys. Once per year:

1. Create a new `ECC_NIST_P256 / SIGN_VERIFY` key and alias target through a reviewed CloudFormation change.
2. Grant only `kms:Sign`, `kms:GetPublicKey`, and `kms:DescribeKey` to the application role.
3. Set `SECUREAPPROVE_PROOF_SIGNING_KEY_ARN` and a new immutable `SECUREAPPROVE_PROOF_SIGNING_KID`.
4. Run `python manage.py sync_proof_signing_key` before enabling issuance on any web or worker instance.
5. Run signing, public verification, iframe, and dashboard smoke tests.
6. Deploy the new configuration. The command retires the previous database key record but never deletes its public JWK.
7. Verify a proof signed by the previous key and one signed by the new key.

Do not schedule deletion of an old KMS key until its retention and incident requirements have been reviewed. Public JWK rows and archived JWS objects are permanent verification dependencies.

## Incident behavior

- KMS signing or encryption failure: new approvals return `503 proof_signing_unavailable`; do not bypass Proof.
- Archive delay over five minutes: the monitor marks proofs `delayed` and emits a critical log. Issued proofs remain locally verifiable while Celery retries.
- Suspected signing-key compromise: set `ProofSigningKey.status=compromised`, block new approvals, rotate the key, and keep the public JWK. The verifier reports `key_compromised` for affected proofs.
- Rollback: disable new issuance and marketing, but keep migrations, verifier routes, JWS records, public keys, and S3 objects available.
