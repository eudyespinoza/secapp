ui = false
disable_mlock = false
log_level = "info"

storage "raft" {
  path    = "/vault/data"
  node_id = "secureapprove-vault-1"
}

listener "tcp" {
  address            = "0.0.0.0:8200"
  cluster_address    = "0.0.0.0:8201"
  tls_disable        = false
  tls_cert_file      = "/vault/tls/server.crt"
  tls_key_file       = "/vault/tls/server.key"
  tls_min_version    = "tls13"
}

api_addr     = "https://vault:8200"
cluster_addr = "https://vault:8201"
