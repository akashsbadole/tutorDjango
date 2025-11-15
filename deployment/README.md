# Django Tutoring Platform Deployment Guide

This guide provides step-by-step instructions for deploying the Django Tutoring Platform to a production environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Configuration](#database-configuration)
4. [Application Configuration](#application-configuration)
5. [Web Server Setup](#web-server-setup)
6. [SSL/TLS Configuration](#ssltls-configuration)
7. [Deployment Process](#deployment-process)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have the following:

- Ubuntu 20.04 LTS or later (recommended)
- Python 3.9 or later
- PostgreSQL 12 or later
- Redis server
- Nginx web server
- Domain name configured with DNS
- SSL certificate (Let's Encrypt recommended)
- PayPal developer account (for payment processing)

## Environment Setup

### 1. System Dependencies

```bash
sudo apt update
sudo apt install -y python3-pip python3-venv python3-dev
sudo apt install -y postgresql postgresql-contrib
sudo apt install -y redis-server
sudo apt install -y nginx
sudo apt install -y build-essential libpq-dev
sudo apt install -y git curl wget
```

### 2. Application User

```bash
# Create a dedicated user for the application
sudo adduser tutorapp
sudo usermod -aG sudo tutorapp

# Switch to the application user
sudo su - tutorapp
```

### 3. Clone the Repository

```bash
git clone https://github.com/your-username/django-tutor-platform.git
cd django-tutor-platform
```

### 4. Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r tutor_platform/requirements.txt
```

## Database Configuration

### 1. PostgreSQL Setup

```bash
# Switch to postgres user
sudo su - postgres

# Create database and user
psql
CREATE DATABASE tutor_platform;
CREATE USER tutor_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE tutor_platform TO tutor_user;
\q
exit
```

### 2. Test Database Connection

```bash
# Test the connection
psql -h localhost -U tutor_user -d tutor_platform -c "SELECT version();"
```

## Application Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```bash
cp deployment/.env.example .env
```

Edit the `.env` file with your specific configuration:

```bash
# Security
SECRET_KEY=your_very_secure_secret_key_here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_NAME=tutor_platform
DB_USER=tutor_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Email
EMAIL_HOST=smtp.yourprovider.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@yourprovider.com
EMAIL_HOST_PASSWORD=your_email_password
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# PayPal
PAYPAL_MODE=sandbox  # Change to live for production
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
PAYPAL_WEBHOOK_ID=your_paypal_webhook_id

# Redis
REDIS_URL=redis://localhost:6379/0

# Other settings
TIME_ZONE=UTC
LANGUAGE_CODE=en-us
```

### 2. Initialize Database

```bash
# Run the database initialization script
python deployment/init_database.py
```

### 3. Create Superuser

```bash
# Create an admin user
python manage.py createsuperuser --settings=deployment.production_settings
```

## Web Server Setup

### 1. Gunicorn Configuration

Create a Gunicorn service file:

```bash
sudo nano /etc/systemd/system/gunicorn.service
```

Add the following content:

```ini
[Unit]
Description=gunicorn daemon for Django Tutoring Platform
After=network.target

[Service]
User=tutorapp
Group=www-data
WorkingDirectory=/home/tutorapp/django-tutor-platform
ExecStart=/home/tutorapp/django-tutor-platform/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/run/gunicorn.sock \
    tutor_platform.tutor_platform.wsgi:application \
    --env DJANGO_SETTINGS_MODULE=deployment.production_settings

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
sudo systemctl status gunicorn
```

### 2. Nginx Configuration

Create an Nginx site configuration:

```bash
sudo nano /etc/nginx/sites-available/tutor_platform
```

Add the following content:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

    # Static and Media Files
    location /static/ {
        root /var/www;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        root /var/www;
        expires 1y;
        add_header Cache-Control "public";
    }

    # Gunicorn
    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health Check
    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/tutor_platform /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## SSL/TLS Configuration

### 1. Install Certbot

```bash
sudo apt install certbot python3-certbot-nginx
```

### 2. Obtain SSL Certificate

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 3. Set Up Auto-Renewal

```bash
sudo crontab -e
```

Add the following line:

```
0 12 * * * /usr/bin/certbot renew --quiet
```

## Deployment Process

### 1. Make Scripts Executable

```bash
chmod +x deployment/deploy.sh
chmod +x deployment/rollback.sh
chmod +x deployment/init_database.py
```

### 2. Deploy the Application

```bash
./deployment/deploy.sh
```

### 3. Verify Deployment

Check that the application is running:

```bash
curl -I https://yourdomain.com/health/
```

## Monitoring and Maintenance

### 1. Log Monitoring

Monitor application logs:

```bash
tail -f /var/log/deploy_tutor_platform.log
```

### 2. Database Backups

Set up automated backups:

```bash
sudo crontab -e
```

Add the following line for daily backups at 2 AM:

```
0 2 * * * pg_dump -U tutor_user -h localhost tutor_platform > /var/backups/tutor_platform/db_backup_$(date +\%Y\%m\%d_\%H\%M\%S).sql
```

### 3. System Health Checks

Create a health check script:

```bash
nano /home/tutorapp/health_check.sh
```

Add the following content:

```bash
#!/bin/bash

# Check if Gunicorn is running
if ! systemctl is-active --quiet gunicorn; then
    echo "Gunicorn is not running"
    systemctl restart gunicorn
fi

# Check if Nginx is running
if ! systemctl is-active --quiet nginx; then
    echo "Nginx is not running"
    systemctl restart nginx
fi

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    echo "PostgreSQL is not running"
    systemctl restart postgresql
fi

# Check if Redis is running
if ! systemctl is-active --quiet redis; then
    echo "Redis is not running"
    systemctl restart redis
fi

# Check application health
if ! curl -f -s -o /dev/null http://localhost:8000/health/; then
    echo "Application health check failed"
    systemctl restart gunicorn
fi
```

Make it executable and add to crontab:

```bash
chmod +x /home/tutorapp/health_check.sh
sudo crontab -e
```

Add the following line for health checks every 5 minutes:

```
*/5 * * * * /home/tutorapp/health_check.sh
```

## Troubleshooting

### 1. Common Issues

#### Application Not Responding

```bash
# Check Gunicorn status
sudo systemctl status gunicorn

# Check Nginx status
sudo systemctl status nginx

# Check application logs
sudo journalctl -u gunicorn
sudo tail -f /var/log/nginx/error.log
```

#### Database Connection Issues

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
psql -h localhost -U tutor_user -d tutor_platform -c "SELECT version();"
```

#### Static Files Not Loading

```bash
# Collect static files
python manage.py collectstatic --noinput --settings=deployment.production_settings

# Check Nginx configuration
sudo nginx -t

# Check file permissions
sudo chown -R www-data:www-data /var/www/static
sudo chown -R www-data:www-data /var/www/media
```

### 2. Rollback Procedure

If a deployment fails, you can rollback to a previous version:

```bash
# List available backups
./deployment/rollback.sh -l

# Rollback to a specific backup
./deployment/rollback.sh -a /path/to/db_backup.sql /path/to/media_backup.tar.gz commit_hash
```

### 3. Performance Optimization

#### Database Optimization

```sql
-- Create indexes for frequently queried columns
CREATE INDEX idx_requirement_subject ON requirements_requirement(subject_id);
CREATE INDEX idx_requirement_status ON requirements_requirement(status);
CREATE INDEX idx_proposal_requirement ON requirements_proposal(requirement_id);
CREATE INDEX idx_proposal_tutor ON requirements_proposal(tutor_id);
```

#### Caching Configuration

Ensure Redis is properly configured and the application is using it for caching:

```bash
# Check Redis status
sudo systemctl status redis

# Test Redis connection
redis-cli ping
```

## Security Considerations

1. Regularly update system packages:
   ```bash
   sudo apt update && sudo apt upgrade
   ```

2. Monitor for security vulnerabilities:
   ```bash
   pip install safety
   safety check
   ```

3. Use strong passwords for all services
4. Regularly backup your data
5. Monitor application logs for suspicious activity
6. Keep your SSL certificates up to date
7. Implement proper firewall rules

## Scaling Considerations

For high-traffic deployments, consider:

1. Load balancing with multiple Gunicorn workers
2. Database read replicas
3. CDN for static files
4. Separate Redis instances for caching and sessions
5. Containerization with Docker
6. Cloud deployment with AWS, Google Cloud, or Azure

## Support

For additional support:

1. Check the application logs for error messages
2. Review the Django documentation
3. Consult the PostgreSQL documentation
4. Refer to the Nginx documentation
5. Check the PayPal API documentation for payment-related issues