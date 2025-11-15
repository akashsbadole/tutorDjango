"""
Django Tutor Platform Admin Portal Models

This module contains models for managing admin-specific data including
admin activity logs, access control, and system settings.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

User = get_user_model()


class AdminRole(models.Model):
    """Admin role model for role-based access control"""
    
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Role Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("JSON object containing role permissions")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Admin Role")
        verbose_name_plural = _("Admin Roles")
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def has_permission(self, permission):
        """Check if role has a specific permission"""
        return self.permissions.get(permission, False)


class AdminProfile(models.Model):
    """Extended profile for admin users"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='admin_profile',
        verbose_name=_("User")
    )
    role = models.ForeignKey(
        AdminRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Role")
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Department")
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Phone Number"))
    is_super_admin = models.BooleanField(
        default=False,
        verbose_name=_("Super Admin"))
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Last Login IP"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("Admin Profile")
        verbose_name_plural = _("Admin Profiles")
    
    def __str__(self):
        return f"{self.user.username} - {self.role.name if self.role else 'No Role'}"
    
    def has_permission(self, permission):
        """Check if admin has a specific permission"""
        if self.is_super_admin:
            return True
        if self.role:
            return self.role.has_permission(permission)
        return False


class AdminActivityLog(models.Model):
    """Log for tracking admin activities"""
    
    ACTION_TYPES = [
        ('CREATE', _('Create')),
        ('UPDATE', _('Update')),
        ('DELETE', _('Delete')),
        ('VIEW', _('View')),
        ('EXPORT', _('Export')),
        ('LOGIN', _('Login')),
        ('LOGOUT', _('Logout')),
        ('BULK_ACTION', _('Bulk Action')),
        ('SYSTEM', _('System')),
    ]
    
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_activities',
        verbose_name=_("Admin"))
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        verbose_name=_("Action Type"))
    action_description = models.TextField(verbose_name=_("Action Description"))
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Content Type"))
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Object ID"))
    content_object = GenericForeignKey('content_type', 'object_id')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("IP Address"))
    user_agent = models.TextField(blank=True, verbose_name=_("User Agent"))
    timestamp = models.DateTimeField(default=now, verbose_name=_("Timestamp"))
    additional_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Additional Data"))
    
    class Meta:
        verbose_name = _("Admin Activity Log")
        verbose_name_plural = _("Admin Activity Logs")
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['admin', 'timestamp']),
            models.Index(fields=['action_type', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.admin.username if self.admin else 'System'} - {self.action_type} - {self.timestamp}"


class SystemSetting(models.Model):
    """System settings for admin portal"""
    
    key = models.CharField(max_length=100, unique=True, verbose_name=_("Key"))
    value = models.TextField(verbose_name=_("Value"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    is_public = models.BooleanField(
        default=False,
        help_text=_("Whether this setting can be accessed via API"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    
    class Meta:
        verbose_name = _("System Setting")
        verbose_name_plural = _("System Settings")
        ordering = ['key']
    
    def __str__(self):
        return f"{self.key}: {self.value}"


class AdminSession(models.Model):
    """Track admin sessions for security"""
    
    admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='admin_sessions',
        verbose_name=_("Admin"))
    session_key = models.CharField(max_length=40, unique=True, verbose_name=_("Session Key"))
    ip_address = models.GenericIPAddressField(verbose_name=_("IP Address"))
    user_agent = models.TextField(verbose_name=_("User Agent"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    last_activity = models.DateTimeField(default=now, verbose_name=_("Last Activity"))
    expires_at = models.DateTimeField(verbose_name=_("Expires At"))
    
    class Meta:
        verbose_name = _("Admin Session")
        verbose_name_plural = _("Admin Sessions")
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['admin', 'is_active']),
            models.Index(fields=['session_key']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.admin.username} - {self.session_key[:8]}..."
    
    def is_expired(self):
        """Check if session is expired"""
        return now() > self.expires_at


class DataExport(models.Model):
    """Track data exports performed by admins"""
    
    EXPORT_TYPES = [
        ('USERS', _('Users')),
        ('REQUIREMENTS', _('Requirements')),
        ('PAYMENTS', _('Payments')),
        ('MESSAGES', _('Messages')),
        ('NOTIFICATIONS', _('Notifications')),
        ('SESSIONS', _('Sessions')),
        ('TRANSACTIONS', _('Transactions')),
        ('REPORTS', _('Reports')),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', _('Pending')),
        ('PROCESSING', _('Processing')),
        ('COMPLETED', _('Completed')),
        ('FAILED', _('Failed')),
        ('EXPIRED', _('Expired')),
    ]
    
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='data_exports',
        verbose_name=_("Admin"))
    export_type = models.CharField(
        max_length=20,
        choices=EXPORT_TYPES,
        verbose_name=_("Export Type"))
    filters = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Filters Applied"))
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name=_("Status"))
    file_path = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("File Path"))
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("File Size (bytes)"))
    record_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Record Count"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Completed At"))
    expires_at = models.DateTimeField(verbose_name=_("Expires At"))
    error_message = models.TextField(
        blank=True,
        verbose_name=_("Error Message"))
    
    class Meta:
        verbose_name = _("Data Export")
        verbose_name_plural = _("Data Exports")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['admin', 'status']),
            models.Index(fields=['export_type', 'status']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.export_type} - {self.admin.username if self.admin else 'System'} - {self.status}"
    
    def is_expired(self):
        """Check if export file is expired"""
        return now() > self.expires_at