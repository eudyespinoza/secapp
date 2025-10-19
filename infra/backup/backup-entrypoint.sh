#!/bin/bash

# ==============================================
# SecureApprove - Backup Service Entry Point
# ==============================================

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
}

log_info "Starting SecureApprove Backup Service..."

# Validate environment variables
if [ -z "$BACKUP_SCHEDULE" ]; then
    log_info "BACKUP_SCHEDULE not set, using default: '0 2 * * *' (daily at 2 AM)"
    export BACKUP_SCHEDULE="0 2 * * *"
fi

if [ -z "$BACKUP_RETENTION_DAYS" ]; then
    log_info "BACKUP_RETENTION_DAYS not set, using default: 30"
    export BACKUP_RETENTION_DAYS="30"
fi

# Create backup directory
mkdir -p /backups

# Update crontab with environment-specific schedule
echo "$BACKUP_SCHEDULE /scripts/backup-mongodb.sh >> /backups/backup.log 2>&1" > /tmp/backup-cron
echo "0 3 * * * /scripts/backup-cleanup.sh >> /backups/cleanup.log 2>&1" >> /tmp/backup-cron
crontab /tmp/backup-cron

log_info "Backup schedule configured: $BACKUP_SCHEDULE"
log_info "Retention period: $BACKUP_RETENTION_DAYS days"

# Test MongoDB connection
log_info "Testing MongoDB connection..."
if /scripts/backup-mongodb.sh --health-check; then
    log_success "MongoDB connection successful"
else
    log_info "MongoDB connection failed, will retry when service is available"
fi

log_success "Backup service initialized successfully"

# Start cron in foreground
exec "$@"