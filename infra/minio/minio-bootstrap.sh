#!/usr/bin/env sh
set -eu

if [ ! -r /run/minio-secrets/minio.env ] || [ ! -r /run/app-secrets/archive-credentials ]; then
  echo "MinIO credential files are missing." >&2
  exit 1
fi

set -a
. /run/minio-secrets/minio.env
set +a

archive_access_key=''
archive_secret_key=''
while IFS='=' read -r credential_name credential_value; do
  case "$credential_name" in
    *aws_access_key_id*) archive_access_key="$(printf '%s' "$credential_value" | tr -d '[:space:]')" ;;
    *aws_secret_access_key*) archive_secret_key="$(printf '%s' "$credential_value" | tr -d '[:space:]')" ;;
  esac
done < /run/app-secrets/archive-credentials

case "${PROOF_ARCHIVE_BUCKET:-}" in
  ''|*[!a-z0-9.-]*) echo "Invalid proof archive bucket name." >&2; exit 1 ;;
esac
case "${PROOF_ARCHIVE_RETENTION_DAYS:-}" in
  ''|*[!0-9]*) echo "Invalid proof archive retention." >&2; exit 1 ;;
esac
if [ -z "$archive_access_key" ] || [ -z "$archive_secret_key" ]; then
  echo "Invalid archive credentials file." >&2
  exit 1
fi

mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null
if ! mc stat "local/$PROOF_ARCHIVE_BUCKET" >/dev/null 2>&1; then
  mc mb --with-lock "local/$PROOF_ARCHIVE_BUCKET" >/dev/null
fi
mc version enable "local/$PROOF_ARCHIVE_BUCKET" >/dev/null
mc retention set --default COMPLIANCE "${PROOF_ARCHIVE_RETENTION_DAYS}d" "local/$PROOF_ARCHIVE_BUCKET" >/dev/null

printf '%s\n' \
  '{' \
  '  "Version": "2012-10-17",' \
  '  "Statement": [' \
  '    {' \
  '      "Effect": "Allow",' \
  '      "Action": ["s3:GetBucketLocation", "s3:GetBucketVersioning"],' \
  "      \"Resource\": [\"arn:aws:s3:::$PROOF_ARCHIVE_BUCKET\"]" \
  '    },' \
  '    {' \
  '      "Effect": "Allow",' \
  '      "Action": ["s3:PutObject", "s3:PutObjectRetention", "s3:GetObjectRetention"],' \
  "      \"Resource\": [\"arn:aws:s3:::$PROOF_ARCHIVE_BUCKET/proofs/*\"]" \
  '    }' \
  '  ]' \
  '}' > /tmp/proof-archive-policy.json
mc admin policy create local secureapprove-proof-archive /tmp/proof-archive-policy.json >/dev/null
mc admin user add local "$archive_access_key" "$archive_secret_key" >/dev/null
mc admin policy attach local secureapprove-proof-archive --user "$archive_access_key" >/dev/null

mc version info "local/$PROOF_ARCHIVE_BUCKET"
mc retention info --default "local/$PROOF_ARCHIVE_BUCKET"
