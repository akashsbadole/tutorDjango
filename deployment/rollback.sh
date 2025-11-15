#!/bin/bash

# Django Tutoring Platform Rollback Script
# This script rolls back to a previous deployment state

set -e  # Exit on any error

# Configuration
PROJECT_NAME="tutor_platform"
BACKUP_DIR="/var/backups/$PROJECT_NAME"
LOG_FILE="/var/log/rollback_$PROJECT_NAME.log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" | tee -a $LOG_FILE
}

# Error handling
error_exit() {
    echo -e "${RED}ERROR: $1${NC}" | tee -a $LOG_FILE
    exit 1
}

# Success message
success() {
    echo -e "${GREEN}SUCCESS: $1${NC}" | tee -a $LOG_FILE
}

# Warning message
warning() {
    echo -e "${YELLOW}WARNING: $1${NC}" | tee -a $LOG_FILE
}

# List available backups
list_backups() {
    log "Available database backups:"
    ls -la $BACKUP_DIR/db_backup_*.sql 2>/dev/null || error_exit "No database backups found"
    
    echo
    log "Available media backups:"
    ls -la $BACKUP_DIR/media_backup_*.tar.gz 2>/dev/null || warning "No media backups found"
}

# Restore database
restore_database() {
    local backup_file=$1
    
    if [ -z "$backup_file" ]; then
        error_exit "Please specify a backup file to restore"
    fi
    
    if [ ! -f "$backup_file" ]; then
        error_exit "Backup file not found: $backup_file"
    fi
    
    log "Restoring database from: $backup_file"
    DB_NAME=$(grep DB_NAME .env | cut -d '=' -f2)
    DB_USER=$(grep DB_USER .env | cut -d '=' -f2)
    
    if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
        error_exit "Database configuration not found in .env file"
    fi
    
    # Drop and recreate database
    dropdb -U $DB_USER -h localhost $DB_NAME || error_exit "Failed to drop database"
    createdb -U $DB_USER -h localhost $DB_NAME || error_exit "Failed to create database"
    
    # Restore from backup
    psql -U $DB_USER -h localhost $DB_NAME < $backup_file || error_exit "Failed to restore database"
    
    success "Database restored successfully"
}

# Restore media files
restore_media() {
    local backup_file=$1
    
    if [ -z "$backup_file" ]; then
        warning "No media backup specified, skipping media restore"
        return
    fi
    
    if [ ! -f "$backup_file" ]; then
        warning "Media backup file not found: $backup_file, skipping media restore"
        return
    fi
    
    log "Restoring media files from: $backup_file"
    MEDIA_DIR=$(grep MEDIA_ROOT deployment/production_settings.py | cut -d "'" -f4)
    
    if [ -z "$MEDIA_DIR" ]; then
        error_exit "Media directory not found in settings"
    fi
    
    # Remove existing media directory
    if [ -d "$MEDIA_DIR" ]; then
        sudo rm -rf $MEDIA_DIR || error_exit "Failed to remove existing media directory"
    fi
    
    # Create media directory
    sudo mkdir -p $MEDIA_DIR || error_exit "Failed to create media directory"
    
    # Extract backup
    sudo tar -xzf $backup_file -C "$(dirname $MEDIA_DIR)" || error_exit "Failed to extract media backup"
    
    # Set proper permissions
    sudo chown -R www-data:www-data $MEDIA_DIR || error_exit "Failed to set media directory permissions"
    
    success "Media files restored successfully"
}

# Rollback to specific commit
rollback_code() {
    local commit_hash=$1
    
    if [ -z "$commit_hash" ]; then
        error_exit "Please specify a commit hash to rollback to"
    fi
    
    log "Rolling back code to commit: $commit_hash"
    git reset --hard $commit_hash || error_exit "Failed to rollback code"
    success "Code rolled back successfully"
}

# Restart services
restart_services() {
    log "Restarting application services..."
    
    # Restart Gunicorn
    sudo systemctl restart gunicorn || error_exit "Failed to restart Gunicorn"
    
    # Restart Nginx
    sudo systemctl restart nginx || error_exit "Failed to restart Nginx"
    
    # Restart Celery (if used)
    if systemctl is-active --quiet celery; then
        sudo systemctl restart celery || error_exit "Failed to restart Celery"
    fi
    
    success "All services restarted successfully"
}

# Health check
health_check() {
    log "Performing health check..."
    
    # Wait for services to start
    sleep 10
    
    # Check if application is responding
    if curl -f -s -o /dev/null http://localhost:8000/health/; then
        success "Application is responding correctly"
    else
        error_exit "Application health check failed"
    fi
}

# Show usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -l, --list              List available backups"
    echo "  -d, --database FILE     Restore database from specific backup file"
    echo "  -m, --media FILE        Restore media files from specific backup file"
    echo "  -c, --commit HASH       Rollback code to specific commit"
    echo "  -a, --all DB_FILE MEDIA_FILE COMMIT_HASH"
    echo "                          Rollback everything (database, media, and code)"
    echo
    echo "Examples:"
    echo "  $0 -l                                    # List available backups"
    echo "  $0 -d /var/backups/tutor_platform/db_backup_20231101_120000.sql  # Restore database only"
    echo "  $0 -a db_backup.sql media_backup.tar.gz abc123def  # Full rollback"
}

# Main rollback function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -l|--list)
                list_backups
                exit 0
                ;;
            -d|--database)
                DB_BACKUP="$2"
                shift 2
                ;;
            -m|--media)
                MEDIA_BACKUP="$2"
                shift 2
                ;;
            -c|--commit)
                COMMIT_HASH="$2"
                shift 2
                ;;
            -a|--all)
                DB_BACKUP="$2"
                MEDIA_BACKUP="$3"
                COMMIT_HASH="$4"
                shift 4
                ;;
            *)
                error_exit "Unknown option: $1"
                ;;
        esac
    done
    
    # Check if any rollback action is specified
    if [ -z "$DB_BACKUP" ] && [ -z "$MEDIA_BACKUP" ] && [ -z "$COMMIT_HASH" ]; then
        error_exit "No rollback action specified. Use -h for help."
    fi
    
    log "Starting rollback process for $PROJECT_NAME..."
    
    # Perform rollback actions
    if [ -n "$COMMIT_HASH" ]; then
        rollback_code "$COMMIT_HASH"
    fi
    
    if [ -n "$DB_BACKUP" ]; then
        restore_database "$DB_BACKUP"
    fi
    
    if [ -n "$MEDIA_BACKUP" ]; then
        restore_media "$MEDIA_BACKUP"
    fi
    
    # Restart services
    restart_services
    
    # Verify rollback
    health_check
    
    success "Rollback completed successfully!"
    log "Rollback completed at $(date)"
}

# Execute main function with all arguments
main "$@"