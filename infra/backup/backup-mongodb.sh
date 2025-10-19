#!/bin/bash

# ==============================================
# SecureApprove - MongoDB Backup Script
# ==============================================

set -e

# Configuration from environment variables
MONGODB_URI=${MONGODB_URI:-"mongodb://mongodb-primary:27017/secureapprove"}
BACKUP_DIR=${BACKUP_DIR:-"/backups"}
BACKUP_PREFIX=${BACKUP_PREFIX:-"secureapprove-backup"}
COMPRESSION=${BACKUP_COMPRESSION:-"gzip"}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="${BACKUP_PREFIX}_${TIMESTAMP}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Health check function
health_check() {
    if mongosh --quiet --eval "db.runCommand('ping')" "$MONGODB_URI" >/dev/null 2>&1; then
        echo "MongoDB connection: OK"
        exit 0
    else
        echo "MongoDB connection: FAILED"
        exit 1
    fi
}

# Handle health check argument
if [ "$1" = "--health-check" ]; then
    health_check
fi

# Main backup function
backup_mongodb() {
    log_info "Starting MongoDB backup: $BACKUP_NAME"
    
    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"
    
    # Perform the backup
    log_info "Creating MongoDB dump..."
    if mongodump --uri="$MONGODB_URI" --out="$BACKUP_DIR/$BACKUP_NAME"; then
        log_success "MongoDB dump created successfully"
    else
        log_error "Failed to create MongoDB dump"
        exit 1
    fi
    
    # Compress the backup if requested
    if [ "$COMPRESSION" = "gzip" ]; then
        log_info "Compressing backup..."
        cd "$BACKUP_DIR"
        if tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"; then
            rm -rf "$BACKUP_NAME"
            log_success "Backup compressed: ${BACKUP_NAME}.tar.gz"
        else
            log_error "Failed to compress backup"
            exit 1
        fi
    fi
    
    log_success "Backup completed successfully: $BACKUP_NAME"
    
    # Log backup size
    if [ "$COMPRESSION" = "gzip" ]; then
        BACKUP_SIZE=$(du -h "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" | cut -f1)
        log_info "Backup size: $BACKUP_SIZE"
    else
        BACKUP_SIZE=$(du -sh "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)
        log_info "Backup size: $BACKUP_SIZE"
    fi
}

# Run backup
backup_mongodb