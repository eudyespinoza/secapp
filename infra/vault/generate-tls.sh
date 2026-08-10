#!/usr/bin/env sh
set -eu

OUTPUT_DIR="${1:-./secrets/vault/tls}"
if [ -e "$OUTPUT_DIR/ca.key" ] || [ -e "$OUTPUT_DIR/server.key" ]; then
  echo "Vault TLS material already exists at $OUTPUT_DIR" >&2
  exit 1
fi

umask 077
mkdir -p "$OUTPUT_DIR"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

openssl genrsa -out "$OUTPUT_DIR/ca.key" 4096
openssl req -x509 -new -sha256 -days 3650 \
  -key "$OUTPUT_DIR/ca.key" \
  -subj "/CN=SecureApprove Vault Internal CA" \
  -out "$OUTPUT_DIR/ca.crt"

openssl genrsa -out "$OUTPUT_DIR/server.key" 3072
openssl req -new -sha256 \
  -key "$OUTPUT_DIR/server.key" \
  -subj "/CN=vault" \
  -out "$TMP_DIR/server.csr"

printf '%s\n' \
  'subjectAltName=DNS:vault,DNS:localhost,IP:127.0.0.1' \
  'extendedKeyUsage=serverAuth' \
  'keyUsage=digitalSignature,keyEncipherment' > "$TMP_DIR/server.ext"

openssl x509 -req -sha256 -days 825 \
  -in "$TMP_DIR/server.csr" \
  -CA "$OUTPUT_DIR/ca.crt" \
  -CAkey "$OUTPUT_DIR/ca.key" \
  -CAcreateserial \
  -extfile "$TMP_DIR/server.ext" \
  -out "$OUTPUT_DIR/server.crt"

chmod 600 "$OUTPUT_DIR/ca.key" "$OUTPUT_DIR/server.key"
chmod 644 "$OUTPUT_DIR/ca.crt" "$OUTPUT_DIR/server.crt"
echo "Vault TLS material created at $OUTPUT_DIR"
