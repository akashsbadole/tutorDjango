"""
Tests app configuration for Django Tutor Platform.
"""
from django.apps import AppConfig


class TestsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tests'
    verbose_name = 'Testing Infrastructure'
    
    def ready(self):
        """Initialize app when Django starts."""
        # Import test utilities and fixtures
        try:
            from . import fixtures  # noqa
            from . import utils  # noqa
        except ImportError:
            # Fixtures and utils will be created later
            pass