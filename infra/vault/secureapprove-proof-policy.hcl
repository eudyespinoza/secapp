path "transit/keys/secureapprove-proof-signing" {
  capabilities = ["read"]
}

path "transit/sign/secureapprove-proof-signing/sha2-256" {
  capabilities = ["update"]
}

path "transit/datakey/plaintext/secureapprove-proof-evidence" {
  capabilities = ["update"]
}

path "transit/decrypt/secureapprove-proof-evidence" {
  capabilities = ["update"]
}
