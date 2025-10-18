#!/usr/bin/env node

/**
 * Generate Self-Signed SSL Certificates for Development
 * For production, use Let's Encrypt via Traefik
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const CERTS_DIR = path.join(__dirname, '..', 'certs');
const DOMAIN = process.env.DOMAIN || 'secureapprove.com';
const DAYS = 365;

console.log('🔐 Generating Self-Signed SSL Certificates...\n');
console.log('='.repeat(60));

// Create certs directory
if (!fs.existsSync(CERTS_DIR)) {
  fs.mkdirSync(CERTS_DIR, { recursive: true });
  console.log(`✅ Created directory: ${CERTS_DIR}`);
}

// Create .gitkeep file
fs.writeFileSync(path.join(CERTS_DIR, '.gitkeep'), '', 'utf8');

try {
  // Generate private key
  console.log('\n📝 Generating private key...');
  execSync(
    `openssl genrsa -out "${path.join(CERTS_DIR, 'privkey.pem')}" 2048`,
    { stdio: 'inherit' }
  );

  // Generate certificate signing request
  console.log('\n📝 Generating CSR...');
  const csrConfig = `
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=US
ST=California
L=San Francisco
O=SecureApprove
OU=IT Department
CN=${DOMAIN}

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${DOMAIN}
DNS.2 = *.${DOMAIN}
DNS.3 = localhost
DNS.4 = api.${DOMAIN}
DNS.5 = grafana.${DOMAIN}
DNS.6 = traefik.${DOMAIN}
IP.1 = 127.0.0.1
`;

  const csrConfigPath = path.join(CERTS_DIR, 'csr.conf');
  fs.writeFileSync(csrConfigPath, csrConfig, 'utf8');

  execSync(
    `openssl req -new -key "${path.join(CERTS_DIR, 'privkey.pem')}" -out "${path.join(CERTS_DIR, 'csr.pem')}" -config "${csrConfigPath}"`,
    { stdio: 'inherit' }
  );

  // Generate self-signed certificate
  console.log('\n📝 Generating self-signed certificate...');
  execSync(
    `openssl x509 -req -days ${DAYS} -in "${path.join(CERTS_DIR, 'csr.pem')}" -signkey "${path.join(CERTS_DIR, 'privkey.pem')}" -out "${path.join(CERTS_DIR, 'fullchain.pem')}" -extensions v3_req -extfile "${csrConfigPath}"`,
    { stdio: 'inherit' }
  );

  // Copy fullchain to chain.pem
  fs.copyFileSync(
    path.join(CERTS_DIR, 'fullchain.pem'),
    path.join(CERTS_DIR, 'chain.pem')
  );

  // Generate client certificate for mTLS
  console.log('\n📝 Generating client certificate for mTLS...');
  execSync(
    `openssl genrsa -out "${path.join(CERTS_DIR, 'client-key.pem')}" 2048`,
    { stdio: 'inherit' }
  );
  execSync(
    `openssl req -new -key "${path.join(CERTS_DIR, 'client-key.pem')}" -out "${path.join(CERTS_DIR, 'client-csr.pem')}" -subj "/C=US/ST=California/L=San Francisco/O=SecureApprove/OU=API Client/CN=api-client"`,
    { stdio: 'inherit' }
  );
  execSync(
    `openssl x509 -req -days ${DAYS} -in "${path.join(CERTS_DIR, 'client-csr.pem')}" -CA "${path.join(CERTS_DIR, 'fullchain.pem')}" -CAkey "${path.join(CERTS_DIR, 'privkey.pem')}" -CAcreateserial -out "${path.join(CERTS_DIR, 'client-cert.pem')}"`,
    { stdio: 'inherit' }
  );

  // Set correct permissions
  const certFiles = [
    'privkey.pem',
    'fullchain.pem',
    'chain.pem',
    'client-key.pem',
    'client-cert.pem',
  ];

  certFiles.forEach((file) => {
    const filePath = path.join(CERTS_DIR, file);
    if (fs.existsSync(filePath)) {
      fs.chmodSync(filePath, 0o600);
    }
  });

  // Clean up temporary files
  const tempFiles = ['csr.pem', 'client-csr.pem', 'csr.conf', 'fullchain.srl'];
  tempFiles.forEach((file) => {
    const filePath = path.join(CERTS_DIR, file);
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
  });

  console.log('\n' + '='.repeat(60));
  console.log('✅ SSL Certificates generated successfully!\n');
  console.log('📁 Certificate files:');
  console.log(`   - Private key: ${path.join(CERTS_DIR, 'privkey.pem')}`);
  console.log(`   - Certificate: ${path.join(CERTS_DIR, 'fullchain.pem')}`);
  console.log(`   - CA Chain: ${path.join(CERTS_DIR, 'chain.pem')}`);
  console.log(`   - Client cert: ${path.join(CERTS_DIR, 'client-cert.pem')}`);
  console.log(`   - Client key: ${path.join(CERTS_DIR, 'client-key.pem')}\n`);

  console.log('⚠️  Note: These are self-signed certificates for development only.');
  console.log('   For production, use Let\'s Encrypt certificates via Traefik.\n');

  console.log('📝 To trust the certificate on your system:');
  console.log('   macOS: sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain certs/fullchain.pem');
  console.log('   Linux: sudo cp certs/fullchain.pem /usr/local/share/ca-certificates/secureapprove.crt && sudo update-ca-certificates');
  console.log('   Windows: Import certs/fullchain.pem to Trusted Root Certification Authorities\n');
  console.log('='.repeat(60));
} catch (error) {
  console.error('\n❌ Error generating certificates:', error.message);
  console.error('\n⚠️  Make sure OpenSSL is installed on your system.');
  process.exit(1);
}
