# Django Tutor Platform Admin Portal

This module provides a comprehensive admin portal for managing the Django tutoring platform with advanced features for user management, content moderation, financial oversight, and system monitoring.

## Features

### 1. Custom Admin Site
- Separate admin portal from Django's default admin
- Custom branding and authentication
- Role-based access control
- Enhanced security features

### 2. Dashboard Views
- **Main Dashboard**: Key metrics and statistics
- **User Management**: User oversight and bulk operations
- **Requirement Management**: Content moderation and oversight
- **Payment & Escrow**: Financial monitoring and management
- **Communication Monitoring**: Message oversight and moderation
- **System Analytics**: Platform health and performance metrics

### 3. Security Features
- Admin access logging
- Session security and management
- Permission validation middleware
- Rate limiting
- Security headers
- CSRF protection

### 4. Data Management
- Data export utilities (CSV, Excel, JSON)
- Bulk operations for efficient management
- Automated data backup
- System cleanup tools

### 5. Management Commands
- `data_backup`: Create comprehensive system backups
- `system_cleanup`: Clean up old data and maintain performance
- `user_verification`: Handle user verification tasks
- `report_generation`: Generate various system reports

## Installation

1. Add `admin_portal` to your `INSTALLED_APPS` in settings.py:

```python
INSTALLED_APPS = [
    # ... other apps
    "admin_portal",
]
```

2. Add the middleware to your `MIDDLEWARE` in settings.py:

```python
MIDDLEWARE = [
    # ... other middleware
    "admin_portal.middleware.AdminAccessLoggingMiddleware",
    "admin_portal.middleware.AdminSessionSecurityMiddleware",
    "admin_portal.middleware.AdminPermissionMiddleware",
    "admin_portal.middleware.AdminRateLimitMiddleware",
    "admin_portal.middleware.AdminSecurityHeadersMiddleware",
]
```

3. Include the admin portal URLs in your main `urls.py`:

```python
urlpatterns = [
    # ... other URLs
    path("admin-panel/", include("admin_portal.urls", namespace="admin_portal")),
]
```

4. Run migrations:

```bash
python manage.py migrate
```

## Configuration

### Admin Portal Settings

Add these settings to your `settings.py` to configure the admin portal:

```python
# Admin Portal Settings
ADMIN_RATE_LIMIT = '100/m'  # Rate limit for admin requests
ADMIN_MAX_CONCURRENT_SESSIONS = 3  # Maximum concurrent admin sessions
ADMIN_SESSION_IP_CHECK = False  # Whether to check IP addresses for sessions
ADMIN_CSP_ENABLED = True  # Enable Content Security Policy headers

# Email settings for admin notifications
DEFAULT_FROM_EMAIL = 'admin@tutorplatform.com'
SITE_NAME = 'Django Tutor Platform'
```

### Role-Based Permissions

The admin portal uses a role-based permission system. Define roles and permissions in the `AdminRole` model:

```python
# Example role permissions
{
    "dashboard": True,
    "user_management": True,
    "payment_management": False,
    "system_settings": False
}
```

## Usage

### Accessing the Admin Portal

1. Navigate to `/admin-panel/` in your browser
2. Login with your admin credentials
3. Access various sections based on your permissions

### Management Commands

#### Data Backup
```bash
# Create a full backup
python manage.py data_backup

# Create backup with specific options
python manage.py data_backup --compress --include-media --output /path/to/backups
```

#### System Cleanup
```bash
# Run all cleanup tasks
python manage.py system_cleanup --all

# Clean up specific data types
python manage.py system_cleanup --cleanup-logs --cleanup-sessions --days 30
```

#### User Verification
```bash
# Verify pending tutor applications
python manage.py user_verification --verify-tutors

# Send verification reminders
python manage.py user_verification --send-reminders

# Auto-verify users with complete profiles
python manage.py user_verification --auto-verify
```

#### Report Generation
```bash
# Generate monthly report
python manage.py report_generation --type monthly --format json --email

# Generate custom date range report
python manage.py report_generation --type custom --start-date 2023-01-01 --end-date 2023-12-31
```

## Security Features

### Access Control
- Role-based permissions for different admin functions
- Session management with automatic expiration
- IP address validation (optional)
- Concurrent session limits

### Audit Trail
- Comprehensive logging of all admin actions
- Track who did what, when, and from where
- Export logs for compliance and analysis

### Rate Limiting
- Configurable rate limits for admin requests
- Protection against brute force attacks
- Automatic blocking of excessive requests

### Data Protection
- CSRF protection on all forms
- Security headers for XSS and clickjacking protection
- Content Security Policy (CSP) headers
- Secure session handling

## Templates

The admin portal uses responsive Bootstrap 5 templates with:

- Modern, clean interface
- Mobile-responsive design
- Interactive charts and data visualizations
- Accessibility features
- Dark mode support

## API Endpoints

The admin portal provides several API endpoints for AJAX functionality:

- `/admin-panel/api/chart-data/`: Get chart data for dashboards
- `/admin-panel/users/bulk-action/`: Perform bulk user operations
- `/admin-panel/api/system-cleanup/`: Trigger system cleanup

## Customization

### Customizing the Dashboard

You can customize the dashboard by:

1. Modifying the `AdminDashboardView` in `views.py`
2. Creating new template blocks in `dashboard.html`
3. Adding custom chart data endpoints

### Adding New Permissions

1. Add permission keys to the `AdminRole.permissions` JSON field
2. Update the `check_permission()` function in `utils.py`
3. Add permission checks to relevant views and middleware

### Extending Management Commands

1. Create new command files in `management/commands/`
2. Inherit from `BaseCommand`
3. Follow the existing patterns for error handling and output

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   - Check that the user has an `AdminProfile`
   - Verify the role has the required permissions
   - Ensure middleware is properly configured

2. **Session Issues**
   - Check session expiration settings
   - Verify middleware order
   - Clear browser cookies if needed

3. **Chart Not Loading**
   - Check browser console for JavaScript errors
   - Verify API endpoints are accessible
   - Ensure Chart.js is loaded

### Debug Mode

Enable debug mode by setting:

```python
DEBUG = True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'admin_portal': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

## Contributing

When contributing to the admin portal:

1. Follow Django coding standards
2. Add comprehensive tests for new features
3. Update documentation for new functionality
4. Ensure security best practices are followed

## License

This module is part of the Django Tutor Platform project and follows the same license terms.