"""
Django settings for tutor_platform project (test environment).

This extends the main settings.py with test-specific configurations.
"""

from .settings import *

# Override settings for testing
DEBUG = True
SECRET_KEY = "test-secret-key-not-for-production-use"

# Use in-memory database for faster tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable migrations for faster test runs
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Test-specific email backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Disable password hashing for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Cache configuration for testing
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Media files for testing
MEDIA_ROOT = BASE_DIR / "test_media"
DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

# Logging configuration for testing
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# Celery configuration for testing
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# PayPal test configuration
PAYPAL_CONFIG = {
    **PAYPAL_CONFIG,
    'MODE': 'sandbox',
    'SKIP_WEBHOOK_VERIFICATION': True,
    'CLIENT_ID': 'test_client_id',
    'CLIENT_SECRET': 'test_client_secret',
}

# Payment gateway test configuration
PAYMENT_GATEWAYS = {
    'STRIPE': {
        'PUBLISHABLE_KEY': 'pk_test_test_key',
        'SECRET_KEY': 'sk_test_test_key',
        'WEBHOOK_SECRET': 'whsec_test_secret',
    },
    'PAYPAL': {
        'CLIENT_ID': 'test_client_id',
        'CLIENT_SECRET': 'test_client_secret',
        'MODE': 'sandbox',
    },
}

# Disable rate limiting for tests
RATELIMIT_ENABLE = False
RATELIMIT_USE_CACHE = "default"

# Test-specific UI components configuration
UI_COMPONENTS = {
    **UI_COMPONENTS,
    'HTMX_ENABLED': False,  # Disable for unit tests
    'ALPINE_ENABLED': False,  # Disable for unit tests
    'TOAST_NOTIFICATIONS': False,
    'NOTIFICATION_POLLING': False,
}

# Security settings for testing (relaxed for easier testing)
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = False
SECURE_BROWSER_XSS_FILTER = False
SECURE_REFERRER_POLICY = None

# CSRF settings for testing
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False
CSRF_TRUSTED_ORIGINS = ["http://testserver", "http://localhost"]

# Session settings for testing
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = False

# Disable allauth email verification for faster tests
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_EMAIL_REQUIRED = False

# Test-specific templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates", BASE_DIR / "test_templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "ui_components.context_processors.ui_context",
            ],
        },
    },
]

# Add test-specific apps to INSTALLED_APPS
INSTALLED_APPS += [
    "tests",
]

# Test-specific middleware (remove some for faster tests)
MIDDLEWARE = [
    middleware for middleware in MIDDLEWARE
    if middleware not in [
        "admin_portal.middleware.AdminAccessLoggingMiddleware",
        "admin_portal.middleware.AdminSessionSecurityMiddleware",
        "admin_portal.middleware.AdminPermissionMiddleware",
        "admin_portal.middleware.AdminRateLimitMiddleware",
        "admin_portal.middleware.AdminSecurityHeadersMiddleware",
        "paypal_integration.middleware.PayPalRequestLoggingMiddleware",
        "paypal_integration.middleware.PayPalCSRFProtectionMiddleware",
        "paypal_integration.middleware.PayPalSecurityHeadersMiddleware",
    ]
]

# Channels configuration for testing
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# Test-specific static files configuration
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

# Disable debug toolbar for tests
if "debug_toolbar" in INSTALLED_APPS:
    INSTALLED_APPS.remove("debug_toolbar")

if "debug_toolbar.middleware.DebugToolbarMiddleware" in MIDDLEWARE:
    MIDDLEWARE.remove("debug_toolbar.middleware.DebugToolbarMiddleware")

# Test-specific internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"

# Test-specific authentication
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# Test-specific REST framework configuration
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# Test-specific file upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 10  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024 * 10  # 10MB

# Test-specific settings for external services
SENTRY_DSN = None

# Test-specific performance settings
CONN_MAX_AGE = 0

# Test-specific settings for third-party integrations
ANYMAIL = {
    "TEST_BACKEND": "anymail.backends.test.EmailBackend",
}

# Disable celery beat for tests
CELERY_BEAT_SCHEDULER = None

# Test-specific settings for search
ELASTICSEARCH_DSL = {
    "default": {
        "hosts": [{"host": "localhost", "port": 9200}],
        "timeout": 20,
    },
}

# Test-specific settings for redis
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 15  # Use a separate DB for tests

# Test-specific settings for background tasks
BACKGROUND_TASK_RUN_EVERY = 1  # seconds
BACKGROUND_TASK_ASYNC = False  # Run tasks synchronously for tests

# Test-specific settings for file storage
AWS_S3_CUSTOM_DOMAIN = None
AWS_STORAGE_BUCKET_NAME = "test-bucket"

# Test-specific settings for monitoring
MONITORING_ENABLED = False