"""
Django Tutor Platform Admin Portal Model Admins

This module contains admin configurations for the admin portal models.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count
from .models import (
    AdminRole, AdminProfile, AdminActivityLog, SystemSetting,
    AdminSession, DataExport
)


@admin.register(AdminRole)
class AdminRoleAdmin(admin.ModelAdmin):
    """Admin configuration for AdminRole model"""
    
    list_display = ['name', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'is_active')
        }),
        (_('Permissions'), {
            'fields': ('permissions',),
            'classes': ('collapse',),
            'description': _('JSON object containing role permissions. Format: {"permission_name": true/false}')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    """Admin configuration for AdminProfile model"""
    
    list_display = ['user', 'role', 'department', 'is_super_admin', 'last_login_ip', 'created_at']
    list_filter = ['role', 'is_super_admin', 'department', 'created_at']
    search_fields = ['user__username', 'user__email', 'department']
    readonly_fields = ['created_at', 'updated_at', 'last_login_ip']
    ordering = ['user__username']
    
    fieldsets = (
        (None, {
            'fields': ('user', 'role', 'is_super_admin')
        }),
        (_('Contact Information'), {
            'fields': ('department', 'phone', 'last_login_ip')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'role')


@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):
    """Admin configuration for AdminActivityLog model"""
    
    list_display = ['admin', 'action_type', 'action_description', 'content_object', 'ip_address', 'timestamp']
    list_filter = ['action_type', 'timestamp', 'content_type']
    search_fields = ['admin__username', 'action_description', 'ip_address']
    readonly_fields = [
        'admin', 'action_type', 'action_description', 'content_type', 
        'object_id', 'ip_address', 'user_agent', 'timestamp', 'additional_data'
    ]
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        """Disable manual creation of activity logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing of activity logs"""
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('admin', 'content_type')
    
    fieldsets = (
        (None, {
            'fields': ('admin', 'action_type', 'action_description')
        }),
        (_('Object Information'), {
            'fields': ('content_type', 'object_id', 'content_object')
        }),
        (_('Request Information'), {
            'fields': ('ip_address', 'user_agent')
        }),
        (_('Timestamps'), {
            'fields': ('timestamp',)
        }),
        (_('Additional Data'), {
            'fields': ('additional_data',),
            'classes': ('collapse',),
        }),
    )


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    """Admin configuration for SystemSetting model"""
    
    list_display = ['key', 'value_preview', 'is_public', 'updated_at']
    list_filter = ['is_public', 'created_at', 'updated_at']
    search_fields = ['key', 'description', 'value']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['key']
    
    def value_preview(self, obj):
        """Show preview of value (truncated if too long)"""
        if len(obj.value) > 50:
            return f"{obj.value[:50]}..."
        return obj.value
    value_preview.short_description = _('Value')
    
    fieldsets = (
        (None, {
            'fields': ('key', 'value', 'description')
        }),
        (_('Settings'), {
            'fields': ('is_public',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(AdminSession)
class AdminSessionAdmin(admin.ModelAdmin):
    """Admin configuration for AdminSession model"""
    
    list_display = ['admin', 'session_key_preview', 'ip_address', 'is_active', 'last_activity', 'expires_at']
    list_filter = ['is_active', 'created_at', 'last_activity']
    search_fields = ['admin__username', 'ip_address', 'session_key']
    readonly_fields = [
        'admin', 'session_key', 'ip_address', 'user_agent',
        'created_at', 'last_activity', 'expires_at'
    ]
    ordering = ['-last_activity']
    date_hierarchy = 'last_activity'
    
    def session_key_preview(self, obj):
        """Show preview of session key"""
        return f"{obj.session_key[:8]}..."
    session_key_preview.short_description = _('Session Key')
    
    def has_add_permission(self, request):
        """Disable manual creation of sessions"""
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('admin')
    
    actions = ['terminate_sessions']
    
    def terminate_sessions(self, request, queryset):
        """Terminate selected sessions"""
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} sessions terminated successfully.")
    terminate_sessions.short_description = _('Terminate selected sessions')
    
    fieldsets = (
        (None, {
            'fields': ('admin', 'session_key', 'is_active')
        }),
        (_('Session Information'), {
            'fields': ('ip_address', 'user_agent')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'last_activity', 'expires_at')
        }),
    )


@admin.register(DataExport)
class DataExportAdmin(admin.ModelAdmin):
    """Admin configuration for DataExport model"""
    
    list_display = ['export_type', 'admin', 'status', 'record_count', 'file_size', 'created_at', 'expires_at']
    list_filter = ['export_type', 'status', 'created_at']
    search_fields = ['admin__username', 'export_type']
    readonly_fields = [
        'admin', 'export_type', 'filters', 'status', 'file_path',
        'file_size', 'record_count', 'created_at', 'completed_at',
        'expires_at', 'error_message'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        """Disable manual creation of export records"""
        return False
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('admin')
    
    actions = ['mark_as_expired']
    
    def mark_as_expired(self, request, queryset):
        """Mark selected exports as expired"""
        count = queryset.update(status='EXPIRED')
        self.message_user(request, f"{count} exports marked as expired.")
    mark_as_expired.short_description = _('Mark selected exports as expired')
    
    def file_size_display(self, obj):
        """Display file size in human readable format"""
        if obj.file_size:
            for unit in ['B', 'KB', 'MB', 'GB']:
                if obj.file_size < 1024.0:
                    return f"{obj.file_size:.1f} {unit}"
                obj.file_size /= 1024.0
            return f"{obj.file_size:.1f} TB"
        return "-"
    file_size_display.short_description = _('File Size')
    
    fieldsets = (
        (None, {
            'fields': ('admin', 'export_type', 'status')
        }),
        (_('Export Details'), {
            'fields': ('filters', 'record_count', 'file_size')
        }),
        (_('File Information'), {
            'fields': ('file_path',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'completed_at', 'expires_at')
        }),
        (_('Error Information'), {
            'fields': ('error_message',),
            'classes': ('collapse',),
        }),
    )


# Customize admin site header and title
admin.site.site_header = _("Django Tutor Platform Admin Portal")
admin.site.site_title = _("Admin Portal")
admin.site.index_title = _("Administration Dashboard")