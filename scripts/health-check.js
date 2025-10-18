#!/usr/bin/env node

/**
 * Health Check Script for Production Deployment
 * Validates all services are running correctly
 */

const https = require('https');
const http = require('http');

const SERVICES = [
  {
    name: 'API Health',
    url: process.env.API_URL || 'https://api.secureapprove.com',
    path: '/api/health',
    timeout: 5000,
  },
  {
    name: 'Frontend',
    url: process.env.APP_URL || 'https://secureapprove.com',
    path: '/api/health',
    timeout: 5000,
  },
  {
    name: 'Prometheus',
    url: 'http://localhost:9090',
    path: '/-/healthy',
    timeout: 3000,
  },
  {
    name: 'Grafana',
    url: 'http://localhost:3001',
    path: '/api/health',
    timeout: 3000,
  },
];

function checkService(service) {
  return new Promise((resolve, reject) => {
    const url = new URL(service.path, service.url);
    const protocol = url.protocol === 'https:' ? https : http;

    const req = protocol.get(
      url.href,
      {
        timeout: service.timeout,
        rejectUnauthorized: false, // Allow self-signed certs in dev
      },
      (res) => {
        if (res.statusCode === 200) {
          resolve({
            name: service.name,
            status: 'OK',
            statusCode: res.statusCode,
          });
        } else {
          reject({
            name: service.name,
            status: 'UNHEALTHY',
            statusCode: res.statusCode,
          });
        }
      }
    );

    req.on('error', (error) => {
      reject({
        name: service.name,
        status: 'ERROR',
        error: error.message,
      });
    });

    req.on('timeout', () => {
      req.destroy();
      reject({
        name: service.name,
        status: 'TIMEOUT',
        error: 'Request timeout',
      });
    });
  });
}

async function runHealthChecks() {
  console.log('🏥 Running health checks...\n');

  const results = [];
  let hasErrors = false;

  for (const service of SERVICES) {
    try {
      const result = await checkService(service);
      results.push(result);
      console.log(`✅ ${result.name}: ${result.status} (${result.statusCode})`);
    } catch (error) {
      results.push(error);
      hasErrors = true;
      console.error(`❌ ${error.name}: ${error.status} - ${error.error || error.statusCode}`);
    }
  }

  console.log('\n' + '='.repeat(50));
  console.log(`Total services checked: ${results.length}`);
  console.log(`Healthy: ${results.filter((r) => r.status === 'OK').length}`);
  console.log(`Unhealthy: ${results.filter((r) => r.status !== 'OK').length}`);
  console.log('='.repeat(50));

  if (hasErrors) {
    console.error('\n⚠️  Some services are not healthy!');
    process.exit(1);
  } else {
    console.log('\n✅ All services are healthy!');
    process.exit(0);
  }
}

runHealthChecks().catch((error) => {
  console.error('Fatal error during health check:', error);
  process.exit(1);
});
