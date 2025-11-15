"""
Django Tutor Platform Admin Portal App Configuration
"""

from django.apps import AppConfig


class AdminPortalConfig(AppConfig):
    """Admin Portal app configuration"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'admin_portal'
    verbose_name = 'Admin Portal'
    
    def ready(self):
        """Initialize app when Django starts"""
        # Import signal handlers
        try:
            from . import signals
        except ImportError:
            pass