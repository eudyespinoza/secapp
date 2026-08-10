#!/usr/bin/env sh
set -eu

OUTPUT_DIR="${1:-./secrets/minio}"
if [ -e "$OUTPUT_DIR/minio.env" ] || [ -e "$OUTPUT_DIR/archive-credentials" ]; then
  echo "MinIO credentials already exist at $OUTPUT_DIR" >&2
  exit 1
fi

umask 077
mkdir -p "$OUTPUT_DIR"
root_user="SECAPPROOT$(openssl rand -hex 5)"
root_password="$(openssl rand -hex 32)"
archive_access_key="SECAPPROOF$(openssl rand -hex 5)"
archive_secret_key="$(openssl rand -hex 32)"

printf 'MINIO_ROOT_USER=%s\nMINIO_ROOT_PASSWORD=%s\n' \
  "$root_user" "$root_password" > "$OUTPUT_DIR/minio.env"
printf '[default]\naws_access_key_id = %s\naws_secret_access_key = %s\n' \
  "$archive_access_key" "$archive_secret_key" > "$OUTPUT_DIR/archive-credentials"

chmod 600 "$OUTPUT_DIR/minio.env" "$OUTPUT_DIR/archive-credentials"
echo "MinIO root and least-privilege archive credentials created at $OUTPUT_DIR"
