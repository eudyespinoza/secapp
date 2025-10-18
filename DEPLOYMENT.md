# SecureApprove - Deployment Guide

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+
- Git
- OpenSSL (for certificate generation)

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/your-org/secure-approve.git
cd secure-approve

# 2. Copy environment template
cp .env.example .env

# 3. Generate secrets and certificates
npm run generate:secrets
npm run generate:ssl

# 4. Edit .env with your credentials
# Update the following:
# - MongoDB passwords
# - Redis passwords
# - JWT secrets
# - AWS credentials
# - SMTP settings
nano .env

# 5. Generate MongoDB keyfile
# Already done by generate:secrets script
chmod 400 infra/mongodb/keyfile

# 6. Install dependencies
npm run install:all

# 7. Build applications
npm run build

# 8. Start production environment
npm run docker:prod

# 9. Verify deployment
npm run health:check
```

## 🔧 Configuration

### Domain Setup

1. **DNS Configuration**
   - Point your domain to your server IP
   - Create A records for:
     - `secureapprove.com` → Your IP
     - `api.secureapprove.com` → Your IP
     - `grafana.secureapprove.com` → Your IP
     - `traefik.secureapprove.com` → Your IP

2. **SSL Certificates**
   - For development: Use generated self-signed certificates
   - For production: Traefik will automatically request Let's Encrypt certificates
   - Certificates are stored in `letsencrypt/acme.json`

### Environment Variables

Critical variables in `.env`:

```bash
# Application
DOMAIN=secureapprove.com
API_URL=https://api.secureapprove.com
APP_URL=https://secureapprove.com

# Database
MONGODB_URI=mongodb://mongodb-primary:27017,mongodb-secondary1:27017,mongodb-secondary2:27017/secureapprove?replicaSet=rs0
MONGODB_PASSWORD=<strong-password>
MONGODB_ROOT_PASSWORD=<strong-password>

# Redis
REDIS_PASSWORD=<strong-password>
REDIS_SENTINEL_PASSWORD=<strong-password>

# JWT
JWT_SECRET=<64-char-hex>
JWT_REFRESH_SECRET=<64-char-hex>

# Encryption
ENCRYPTION_KEY=<32-char-hex>

# AWS S3 (for backups)
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_S3_BUCKET=secureapprove-backups

# Email (SendGrid)
SMTP_PASSWORD=<sendgrid-api-key>

# Monitoring
GRAFANA_ADMIN_PASSWORD=<strong-password>
```

## 🐳 Docker Services

### Running Services

The production environment includes:

| Service | Container | Port | Description |
|---------|-----------|------|-------------|
| Traefik | secureapprove-traefik | 80, 443, 8080 | Load balancer & SSL termination |
| API (x3) | secureapprove-api-1,2,3 | Internal | NestJS backend instances |
| Frontend | secureapprove-frontend | Internal | Next.js web application |
| MongoDB Primary | secureapprove-mongodb-primary | 27017 | Database primary node |
| MongoDB Secondary1 | secureapprove-mongodb-secondary1 | Internal | Database replica |
| MongoDB Secondary2 | secureapprove-mongodb-secondary2 | Internal | Database replica |
| Redis Master | secureapprove-redis-master | 6379 | Cache master |
| Redis Slave1 | secureapprove-redis-slave1 | Internal | Cache replica |
| Redis Slave2 | secureapprove-redis-slave2 | Internal | Cache replica |
| Sentinel1 | secureapprove-sentinel1 | 26379 | Redis HA manager |
| Sentinel2 | secureapprove-sentinel2 | 26380 | Redis HA manager |
| Sentinel3 | secureapprove-sentinel3 | 26381 | Redis HA manager |
| Prometheus | secureapprove-prometheus | 9090 | Metrics collection |
| Grafana | secureapprove-grafana | 3001 | Monitoring dashboards |
| Backup | secureapprove-backup | N/A | Automated backups |

### Service Management

```bash
# Start all services
npm run docker:prod

# Stop all services
npm run docker:down

# View logs
npm run docker:logs

# View specific service logs
npm run logs:api
npm run logs:mongodb
npm run logs:redis

# Restart a service
docker-compose restart api-1

# Scale API instances
docker-compose up -d --scale api=5

# Clean up
npm run docker:clean
```

## 📊 Monitoring

### Access Dashboards

```bash
# Grafana (monitoring)
URL: https://grafana.secureapprove.com
Username: admin
Password: <GRAFANA_ADMIN_PASSWORD from .env>

# Prometheus (metrics)
URL: http://localhost:9090

# Traefik (load balancer)
URL: https://traefik.secureapprove.com
Username: admin
Password: <hashed password from .env>
```

### Key Metrics

- **Response Time**: P50, P95, P99 latencies
- **Throughput**: Requests per minute
- **Error Rate**: 4xx and 5xx responses
- **Authentication**: Success/failure rates
- **Database**: Query performance and connections
- **Cache**: Redis hit/miss ratios

## 🔒 Security

### Initial Security Setup

1. **Change default passwords**
   ```bash
   # Generate new secrets
   npm run generate:secrets
   # Update .env with new values
   ```

2. **Configure firewall**
   ```bash
   # Ubuntu/Debian
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

3. **Setup fail2ban**
   ```bash
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

4. **Enable automatic updates**
   ```bash
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure --priority=low unattended-upgrades
   ```

### Security Best Practices

- ✅ Use strong, unique passwords for all services
- ✅ Enable 2FA for all admin accounts
- ✅ Regularly update dependencies (`npm audit fix`)
- ✅ Monitor security logs in Grafana
- ✅ Enable automatic backups
- ✅ Test disaster recovery procedures monthly
- ✅ Keep SSL certificates up to date
- ✅ Use VPN for admin access
- ✅ Implement IP whitelisting for admin endpoints

## 💾 Backup & Recovery

### Automated Backups

Backups run daily at 2:00 AM UTC:

```bash
# Manual backup
npm run backup:create

# List backups
npm run backup:list

# Restore from backup
npm run backup:restore backup-20240101-020000
```

### Backup Storage

- **Location**: AWS S3 bucket (encrypted)
- **Retention**: 30 days
- **Frequency**: Daily
- **Components**: MongoDB, Redis, configuration files

### Disaster Recovery

1. **Restore from backup**
   ```bash
   npm run backup:restore <backup-name>
   ```

2. **Restart services**
   ```bash
   npm run docker:prod
   ```

3. **Verify integrity**
   ```bash
   npm run health:check
   npm run test:smoke:production
   ```

## 🔄 Updates & Maintenance

### Application Updates

```bash
# Pull latest changes
git pull origin main

# Update dependencies
npm run install:all

# Rebuild applications
npm run build

# Rolling update (zero downtime)
docker-compose up -d --no-deps --build api-1
sleep 10
docker-compose up -d --no-deps --build api-2
sleep 10
docker-compose up -d --no-deps --build api-3

# Verify deployment
npm run health:check
```

### Database Maintenance

```bash
# Compact database
docker exec secureapprove-mongodb-primary mongosh --eval "db.runCommand({ compact: 'users' })"

# Check replication status
docker exec secureapprove-mongodb-primary mongosh --eval "rs.status()"

# Database backup
docker exec secureapprove-mongodb-primary mongodump --out=/backup
```

## 🐛 Troubleshooting

### Common Issues

**API not responding**
```bash
# Check logs
docker logs secureapprove-api-1

# Restart service
docker-compose restart api-1

# Check health
curl http://localhost:3000/health
```

**MongoDB connection failed**
```bash
# Check ReplicaSet status
docker exec secureapprove-mongodb-primary mongosh --eval "rs.status()"

# Verify authentication
docker exec -it secureapprove-mongodb-primary mongosh -u root -p
```

**Redis connection issues**
```bash
# Check Sentinel status
docker exec secureapprove-sentinel1 redis-cli -p 26379 SENTINEL get-master-addr-by-name mymaster

# Test connection
docker exec secureapprove-redis-master redis-cli -a $REDIS_PASSWORD PING
```

**High memory usage**
```bash
# Check resource usage
docker stats

# Identify memory leaks
docker exec secureapprove-api-1 node --expose-gc --inspect index.js
```

## 📞 Support

- **Documentation**: https://docs.secureapprove.com
- **Issues**: https://github.com/your-org/secure-approve/issues
- **Security**: security@secureapprove.com
- **Support**: support@secureapprove.com

## 📋 Checklist

### Pre-Deployment
- [ ] Domain DNS configured
- [ ] SSL certificates ready
- [ ] Environment variables configured
- [ ] Secrets generated
- [ ] Firewall configured
- [ ] Backup storage configured
- [ ] Email service configured
- [ ] Monitoring dashboards setup

### Post-Deployment
- [ ] Health checks passing
- [ ] SSL certificates valid
- [ ] Monitoring alerts working
- [ ] Backups running successfully
- [ ] Email notifications working
- [ ] WebAuthn registration tested
- [ ] Load balancing verified
- [ ] Disaster recovery tested

---

**Last Updated**: December 2024
**Version**: 1.0.0
