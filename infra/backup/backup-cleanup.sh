#!/bin/bash

# ==============================================
# SecureApprove - Backup Cleanup Script
# ==============================================

set -e

# Configuration from environment variables
BACKUP_DIR=${BACKUP_DIR:-"/backups"}
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
BACKUP_PREFIX=${BACKUP_PREFIX:-"secureapprove-backup"}

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

# Main cleanup function
cleanup_old_backups() {
    log_info "Starting backup cleanup (retention: ${RETENTION_DAYS} days)"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        log_warning "Backup directory does not exist: $BACKUP_DIR"
        return 0
    fi
    
    # Find and delete old backup files
    DELETED_COUNT=0
    
    # Find files older than retention period
    while IFS= read -r -d '' file; do
        log_info "Deleting old backup: $(basename "$file")"
        if rm -f "$file"; then
            DELETED_COUNT=$((DELETED_COUNT + 1))
        else
            log_error "Failed to delete: $(basename "$file")"
        fi
    done < <(find "$BACKUP_DIR" -name "${BACKUP_PREFIX}_*.tar.gz" -type f -mtime +${RETENTION_DAYS} -print0 2>/dev/null)
    
    # Find directories older than retention period (uncompressed backups)
    while IFS= read -r -d '' dir; do
        log_info "Deleting old backup directory: $(basename "$dir")"
        if rm -rf "$dir"; then
            DELETED_COUNT=$((DELETED_COUNT + 1))
        else
            log_error "Failed to delete directory: $(basename "$dir")"
        fi
    done < <(find "$BACKUP_DIR" -name "${BACKUP_PREFIX}_*" -type d -mtime +${RETENTION_DAYS} -print0 2>/dev/null)
    
    log_success "Cleanup completed. Deleted $DELETED_COUNT old backups"
    
    # Show current backup count and disk usage
    CURRENT_BACKUPS=$(find "$BACKUP_DIR" -name "${BACKUP_PREFIX}_*" | wc -l)
    DISK_USAGE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
    
    log_info "Current backups: $CURRENT_BACKUPS"
    log_info "Total backup disk usage: $DISK_USAGE"
}

# Run cleanup
cleanup_old_backups