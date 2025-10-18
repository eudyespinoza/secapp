#!/usr/bin/env node

/**
 * Generate Secrets Script
 * Generates secure random secrets for production deployment
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

function generateSecret(length = 64) {
  return crypto.randomBytes(length).toString('hex');
}

function generateBase64Secret(length = 756) {
  return crypto.randomBytes(length).toString('base64');
}

function generateBcryptPassword() {
  const password = crypto.randomBytes(16).toString('hex');
  console.log(`\nGenerated password: ${password}`);
  console.log('Hash this with: npx bcryptjs ${password}');
  return password;
}

console.log('🔐 Generating Secrets for Production...\n');
console.log('='.repeat(60));

// Generate all secrets
const secrets = {
  MONGODB_PASSWORD: generateSecret(16),
  MONGODB_ROOT_PASSWORD: generateSecret(16),
  MONGODB_REPLICA_SET_KEY: generateBase64Secret(756),
  REDIS_PASSWORD: generateSecret(12),
  REDIS_SENTINEL_PASSWORD: generateSecret(12),
  JWT_SECRET: generateSecret(64),
  JWT_REFRESH_SECRET: generateSecret(64),
  ENCRYPTION_KEY: generateSecret(16), // 32 hex chars = 16 bytes for AES-256
  SESSION_SECRET: generateSecret(64),
  GRAFANA_ADMIN_PASSWORD: generateSecret(8),
  GRAFANA_SECRET_KEY: generateSecret(16),
  BACKUP_ENCRYPTION_KEY: generateSecret(16),
};

console.log('\n📋 Generated Secrets:\n');
console.log('Copy these to your .env file:\n');
console.log('='.repeat(60));

for (const [key, value] of Object.entries(secrets)) {
  console.log(`${key}=${value}`);
}

console.log('\n='.repeat(60));

// Save to a temporary file (NOT committed to git)
const outputPath = path.join(__dirname, '..', '.secrets.temp');
const output = Object.entries(secrets)
  .map(([key, value]) => `${key}=${value}`)
  .join('\n');

fs.writeFileSync(outputPath, output, 'utf8');
console.log(`\n✅ Secrets saved to: ${outputPath}`);
console.log('⚠️  WARNING: Delete this file after copying to .env!\n');

// Generate MongoDB keyfile
const mongoKeyfilePath = path.join(__dirname, '..', 'infra', 'mongodb', 'keyfile');
const mongoKeyfileDir = path.dirname(mongoKeyfilePath);

if (!fs.existsSync(mongoKeyfileDir)) {
  fs.mkdirSync(mongoKeyfileDir, { recursive: true });
}

fs.writeFileSync(mongoKeyfilePath, secrets.MONGODB_REPLICA_SET_KEY, 'utf8');
fs.chmodSync(mongoKeyfilePath, 0o400);
console.log(`✅ MongoDB keyfile created: ${mongoKeyfilePath}\n`);

// Generate Traefik dashboard password
console.log('🔑 Generate Traefik Dashboard Password:');
console.log('Run: htpasswd -nbB admin <password>');
console.log('Or use online generator: https://bcrypt-generator.com/\n');

console.log('='.repeat(60));
console.log('\n✅ Secret generation complete!');
console.log('\n📝 Next steps:');
console.log('1. Copy secrets from .secrets.temp to .env');
console.log('2. Generate Traefik password hash');
console.log('3. Update AWS credentials in .env');
console.log('4. Configure SMTP settings in .env');
console.log('5. Delete .secrets.temp file');
console.log('6. Never commit .env to version control!\n');
