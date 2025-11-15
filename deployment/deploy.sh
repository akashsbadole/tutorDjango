#!/bin/bash

# Django Tutoring Platform Deployment Script
# This script automates the deployment process for production environments

set -e  # Exit on any error

# Configuration
PROJECT_NAME="tutor_platform"
BACKUP_DIR="/var/backups/$PROJECT_NAME"
LOG_FILE="/var/log/deploy_$PROJECT_NAME.log"
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

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error_exit "This script should not be run as root for security reasons"
    fi
}

# Create backup directory
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        sudo mkdir -p $BACKUP_DIR
        sudo chown $USER:$USER $BACKUP_DIR
        success "Created backup directory: $BACKUP_DIR"
    fi
}

# Backup database
backup_database() {
    log "Creating database backup..."
    DB_NAME=$(grep DB_NAME .env | cut -d '=' -f2)
    DB_USER=$(grep DB_USER .env | cut -d '=' -f2)
    
    if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ]; then
        error_exit "Database configuration not found in .env file"
    fi
    
    pg_dump -U $DB_USER -h localhost $DB_NAME > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql" || error_exit "Database backup failed"
    success "Database backup created: $BACKUP_DIR/db_backup_$TIMESTAMP.sql"
}

# Backup media files
backup_media() {
    log "Creating media files backup..."
    MEDIA_DIR=$(grep MEDIA_ROOT deployment/production_settings.py | cut -d "'" -f4)
    
    if [ -d "$MEDIA_DIR" ]; then
        tar -czf "$BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz" -C "$(dirname $MEDIA_DIR)" "$(basename $MEDIA_DIR)" || error_exit "Media backup failed"
        success "Media backup created: $BACKUP_DIR/media_backup_$TIMESTAMP.tar.gz"
    else
        warning "Media directory not found: $MEDIA_DIR"
    fi
}

# Update code from repository
update_code() {
    log "Updating application code..."
    git pull origin main || error_exit "Failed to pull latest code"
    success "Code updated successfully"
}

# Install/update dependencies
install_dependencies() {
    log "Installing/updating dependencies..."
    
    # Python dependencies
    pip install -r requirements.txt || error_exit "Failed to install Python dependencies"
    
    # Node dependencies (if any)
    if [ -f "package.json" ]; then
        npm install || error_exit "Failed to install Node dependencies"
    fi
    
    success "Dependencies installed successfully"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    python manage.py migrate --settings=deployment.production_settings || error_exit "Database migrations failed"
    success "Database migrations completed"
}

# Collect static files
collect_static() {
    log "Collecting static files..."
    python manage.py collectstatic --noinput --settings=deployment.production_settings || error_exit "Static file collection failed"
    success "Static files collected"
}

# Restart application services
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

# Cleanup old backups
cleanup_backups() {
    log "Cleaning up old backups (keeping last 7 days)..."
    find $BACKUP_DIR -name "*backup_*" -mtime +7 -delete || warning "Failed to cleanup old backups"
    success "Old backups cleaned up"
}

# Main deployment function
main() {
    log "Starting deployment process for $PROJECT_NAME..."
    
    check_root
    create_backup_dir
    
    # Backup current state
    backup_database
    backup_media
    
    # Update application
    update_code
    install_dependencies
    run_migrations
    collect_static
    
    # Restart services
    restart_services
    
    # Verify deployment
    health_check
    
    # Cleanup
    cleanup_backups
    
    success "Deployment completed successfully!"
    log "Deployment completed at $(date)"
}

# Execute main function
main "$@"