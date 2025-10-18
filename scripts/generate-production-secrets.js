#!/usr/bin/env node

/**
 * SecureApprove - Production Secrets Generator
 * Generates secure random secrets for production environment
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// Generate secure random string
function generateSecret(length = 64) {
    return crypto.randomBytes(length).toString('hex');
}

// Generate MongoDB replica set key (must be 512 characters)
function generateMongoKey() {
    return crypto.randomBytes(256).toString('base64');
}

// Generate encryption key (32 bytes for AES-256)
function generateEncryptionKey() {
    return crypto.randomBytes(32).toString('hex');
}

console.log('🔐 Generando secretos seguros para producción...\n');

const secrets = {
    // Database passwords
    MONGODB_PASSWORD: generateSecret(32),
    MONGODB_ROOT_PASSWORD: generateSecret(32),
    MONGODB_REPLICA_SET_KEY: generateMongoKey(),
    
    // Redis
    REDIS_PASSWORD: generateSecret(32),
    
    // JWT secrets
    JWT_SECRET: generateSecret(64),
    JWT_REFRESH_SECRET: generateSecret(64),
    SESSION_SECRET: generateSecret(64),
    
    // Encryption
    ENCRYPTION_KEY: generateEncryptionKey(),
    
    // Grafana
    GRAFANA_ADMIN_PASSWORD: generateSecret(16),
    GRAFANA_SECRET_KEY: generateSecret(32),
    
    // Backup encryption
    BACKUP_ENCRYPTION_KEY: generateSecret(32)
};

console.log('📋 SECRETOS GENERADOS PARA PRODUCCIÓN:');
console.log('=======================================\n');

// Output secrets
Object.entries(secrets).forEach(([key, value]) => {
    console.log(`${key}=${value}`);
});

console.log('\n=======================================');
console.log('⚠️  IMPORTANTE:');
console.log('1. Copia estos secretos a tu archivo .env en el servidor');
console.log('2. NUNCA compartas estos secretos');
console.log('3. Guárdalos en un gestor de contraseñas seguro');
console.log('4. Cambia las credenciales por defecto de servicios externos');
console.log('=======================================\n');

// Generate .env.secrets file for easy copying
const envContent = Object.entries(secrets)
    .map(([key, value]) => `${key}=${value}`)
    .join('\n');

const secretsFile = path.join(__dirname, '..', '.env.secrets');
fs.writeFileSync(secretsFile, envContent);

console.log(`💾 Secretos guardados en: ${secretsFile}`);
console.log('   Copia este archivo al servidor y actualiza tu .env\n');

console.log('🚀 ¡Listo para producción!');