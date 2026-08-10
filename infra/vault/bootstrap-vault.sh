#!/usr/bin/env sh
set -eu

SECRETS_DIR="${SECUREAPPROVE_SECRETS_DIR:-./secrets}"
VAULT_SECRETS_DIR="$SECRETS_DIR/vault"
INIT_FILE="$VAULT_SECRETS_DIR/init.json"
INIT_TMP="$VAULT_SECRETS_DIR/.init.json.tmp"

umask 077
mkdir -p "$VAULT_SECRETS_DIR"

if python3 -c 'import json' >/dev/null 2>&1; then
  PYTHON_BIN=python3
elif python -c 'import json' >/dev/null 2>&1; then
  PYTHON_BIN=python
else
  echo "Python 3 is required to parse Vault recovery material safely." >&2
  exit 1
fi

vault_exec() {
  docker compose exec -T vault vault "$@"
}

attempt=0
until vault_exec status -format=json 2>/dev/null | grep -q '"initialized"'; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "Vault API did not become ready within 30 seconds." >&2
    exit 1
  fi
  sleep 1
done

initialized="$(vault_exec status -format=json 2>/dev/null | "$PYTHON_BIN" -c 'import json,sys; print(str(json.load(sys.stdin).get("initialized", False)).lower())' 2>/dev/null || printf 'false')"
if [ "$initialized" != "true" ]; then
  if [ -e "$INIT_FILE" ]; then
    echo "Vault is uninitialized but $INIT_FILE already exists; refusing to overwrite recovery material." >&2
    exit 1
  fi
  rm -f "$INIT_TMP"
  if ! vault_exec operator init -key-shares=5 -key-threshold=3 -format=json > "$INIT_TMP"; then
    rm -f "$INIT_TMP"
    echo "Vault initialization failed; no recovery file was written." >&2
    exit 1
  fi
  mv "$INIT_TMP" "$INIT_FILE"
  chmod 600 "$INIT_FILE"
  echo "Vault initialized with five Shamir shares and a three-share threshold."
fi

sealed="$(vault_exec status -format=json 2>/dev/null | "$PYTHON_BIN" -c 'import json,sys; print(str(json.load(sys.stdin).get("sealed", True)).lower())' 2>/dev/null || printf 'true')"
if [ "$sealed" = "true" ]; then
  if [ ! -f "$INIT_FILE" ]; then
    echo "Vault is sealed. Supply three unseal shares manually; no local init file exists." >&2
    exit 1
  fi
  for index in 0 1 2; do
    key="$("$PYTHON_BIN" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["unseal_keys_b64"][int(sys.argv[2])])' "$INIT_FILE" "$index")"
    docker compose exec -T vault vault operator unseal "$key" >/dev/null
  done
  echo "Vault unsealed."
fi

root_token="$("$PYTHON_BIN" -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["root_token"])' "$INIT_FILE")"
vault_root() {
  docker compose exec -T -e VAULT_TOKEN="$root_token" vault vault "$@"
}

attempt=0
until vault_root secrets list -format=json >/dev/null 2>&1; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "Vault did not become active within 30 seconds after unseal." >&2
    exit 1
  fi
  sleep 1
done

if ! vault_root secrets list -format=json | "$PYTHON_BIN" -c 'import json,sys; raise SystemExit(0 if "transit/" in json.load(sys.stdin) else 1)'; then
  vault_root secrets enable transit >/dev/null
fi
if ! vault_root read transit/keys/secureapprove-proof-signing >/dev/null 2>&1; then
  vault_root write transit/keys/secureapprove-proof-signing type=ecdsa-p256 exportable=false allow_plaintext_backup=false >/dev/null
fi
if ! vault_root read transit/keys/secureapprove-proof-evidence >/dev/null 2>&1; then
  vault_root write transit/keys/secureapprove-proof-evidence type=aes256-gcm96 derived=true exportable=false allow_plaintext_backup=false >/dev/null
fi

vault_root policy write secureapprove-proof - < infra/vault/secureapprove-proof-policy.hcl >/dev/null
if ! vault_root auth list -format=json | "$PYTHON_BIN" -c 'import json,sys; raise SystemExit(0 if "approle/" in json.load(sys.stdin) else 1)'; then
  vault_root auth enable approle >/dev/null
fi
vault_root write auth/approle/role/secureapprove-proof \
  token_policies=secureapprove-proof \
  token_period=1h \
  token_num_uses=0 \
  secret_id_num_uses=0 \
  secret_id_ttl=0 >/dev/null

vault_root read -field=role_id auth/approle/role/secureapprove-proof/role-id > "$VAULT_SECRETS_DIR/role-id"
if [ ! -s "$VAULT_SECRETS_DIR/secret-id" ]; then
  vault_root write -f -field=secret_id auth/approle/role/secureapprove-proof/secret-id > "$VAULT_SECRETS_DIR/secret-id"
fi
chmod 600 "$VAULT_SECRETS_DIR/role-id" "$VAULT_SECRETS_DIR/secret-id"

echo "Vault Transit and the SecureApprove Proof AppRole are ready."
echo "Move $INIT_FILE to encrypted offline custody after validating recovery."
