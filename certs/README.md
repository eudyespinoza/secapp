# SSL Certificates Directory

This directory will contain SSL/TLS certificates for production deployment.

## Development

For development, generate self-signed certificates:

```bash
npm run generate:ssl
```

This will create:
- `privkey.pem` - Private key
- `fullchain.pem` - Certificate
- `chain.pem` - CA chain
- `client-cert.pem` - Client certificate for mTLS
- `client-key.pem` - Client key for mTLS

## Production

For production, Traefik will automatically request and renew Let's Encrypt certificates.

Certificates are stored in `letsencrypt/acme.json`.

## Security

⚠️ **IMPORTANT**: 
- Never commit certificate files to version control
- Keep private keys secure with proper file permissions (600)
- Rotate certificates regularly
- Monitor certificate expiration dates

## File Permissions

```bash
chmod 600 *.pem
chmod 600 *.key
```

## Verification

Check certificate validity:

```bash
openssl x509 -in fullchain.pem -text -noout
```

Test SSL connection:

```bash
openssl s_client -connect secureapprove.com:443
```
