# SecureApprove Proof operations runbook

## Production architecture

- Django sends Transit requests only to the dedicated Vault Proxy on the private `proof_vault_client` network.
- Vault Proxy authenticates with AppRole, renews its periodic token, overwrites any caller-supplied token, and requires `X-Vault-Request: true`.
- The AppRole can read the signing public key, sign with one ECDSA P-256 key, create encrypted data keys, and decrypt those data keys. It cannot export or rotate either Transit key.
- Private WebAuthn evidence is encrypted with a fresh AES-256-GCM data key. Vault Transit wraps that key with a proof- and tenant-specific derivation context.
- Celery writes only the public, PII-free JWS to MinIO. The bucket has versioning and Object Lock COMPLIANCE enabled for ten years by default.

The production server is a single physical failure domain. Vault Raft and MinIO protect key custody and immutability from application compromise, but they do not provide host-level high availability. Replicate encrypted Vault snapshots, PostgreSQL backups, and the MinIO volume to a second machine before claiming disaster recovery.

## First installation

1. Keep Proof and its marketing disabled.
2. Generate host-owned credentials and TLS material:

   ```sh
   sh infra/vault/generate-tls.sh ./secrets/vault/tls
   sh infra/minio/generate-secrets.sh ./secrets/minio
   ```

3. Start Vault only: `docker compose up -d vault`.
4. Initialize, unseal, and configure Transit/AppRole: `sh infra/vault/bootstrap-vault.sh`.
5. Move `secrets/vault/init.json` to encrypted offline custody. The file contains the initial root token and all Shamir shares. Do not leave all recovery shares on the application host.
6. Start Vault Proxy, MinIO, and its idempotent bucket bootstrap:

   ```sh
   docker compose up -d vault_proxy minio
   docker compose run --rm minio_init
   ```

7. Start the application with `SECUREAPPROVE_PROOF_ENABLED=True`, but keep marketing disabled.
8. Run `python manage.py sync_proof_signing_key` and `python manage.py proof_infrastructure_smoke` inside the web container.
9. Verify the smoke JWS, COMPLIANCE retention, dashboard approval, iframe approval, and archive worker.
10. Enable `SECUREAPPROVE_PROOF_MARKETING_ENABLED=True` only after all checks pass.

## Vault restart and recovery

Vault starts sealed. New approvals fail closed until three Shamir shares unseal it. Existing public proofs remain verifiable from stored JWKs while Vault is sealed.

For routine recovery, provide three shares from separate custodians with `vault operator unseal`. The bootstrap script may use a local `init.json` during the initial deployment only; offline custody is the production target.

Take a Raft snapshot after every key or policy change and at least daily:

```sh
docker compose exec -T vault vault operator raft snapshot save /vault/data/backup.snap
```

Copy snapshots to encrypted storage outside the server. Test restore and unseal quarterly.

## Signing-key rotation

Vault Transit versions asymmetric keys without exporting private material.

1. Block new approvals or enter a short maintenance window.
2. Rotate: `vault write -f transit/keys/secureapprove-proof-signing/rotate`.
3. Run `python manage.py sync_proof_signing_key` in the web container. The application derives a new immutable `kid` ending in `-vN` and retires the previous database row.
4. Run the infrastructure smoke test and issue one dashboard and one iframe proof.
5. Verify one proof from the previous key version and one from the new version.
6. Never delete old Transit versions or public JWK rows while their proofs must verify.

Rotate at least annually and immediately after suspected compromise. Evidence-key rotation is independent; Transit ciphertext embeds its key version, so retained evidence continues to decrypt.

## MinIO operations

- The application credential is limited to `proofs/*` and cannot delete objects or bypass retention.
- The root credential is used only by the one-shot bootstrap job and operators.
- Confirm Object Lock after changes with `mc retention info --default` and `mc version info`.
- Back up the entire MinIO data volume to a second host. COMPLIANCE prevents logical deletion; it cannot protect a single disk or a destroyed Docker volume.
- The pinned MinIO Community image must be tracked as a supply-chain exception because the upstream community repository was archived in 2026. Replace it with a supported WORM-compatible S3 implementation when an operationally mature option is selected.

## Incident behavior

- Vault signing or encryption failure: new approvals return `503 proof_signing_unavailable`; never bypass Proof or reuse the WebAuthn ceremony.
- Archive delay over five minutes: the monitor marks proofs `delayed` and emits a critical log. Celery retries while the signed proof remains locally verifiable.
- Suspected signing-key compromise: set `ProofSigningKey.status=compromised`, block new approvals, rotate Vault Transit, sync the new JWK, and preserve historical keys for incident review. The public verifier reports `key_compromised` for affected proofs.
- Rollback: disable issuance and marketing, but keep migrations, verifier routes, JWS records, public JWKs, Vault key versions, and WORM objects available.

## AWS alternative

The `aws_kms` backend remains supported. It requires an ECC NIST P-256 signing key, a symmetric evidence key, Object Lock S3 bucket, and workload credentials with only `kms:Sign`, `kms:GetPublicKey`, `kms:GenerateDataKey`, `kms:Decrypt`, and the required S3 object actions.
