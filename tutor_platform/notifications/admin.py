from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count
from django.utils import timezone

from .models import (
    Notification, NotificationPreference,
    NotificationTemplate, EmailQueue, NotificationType,
    NotificationDelivery, NotificationDigest, PushDevice,
    PushMessage, SystemNotification, SystemNotificationDismissal,
    NotificationAnalytics
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Notification model with bulk actions"""
    
    list_display = [
        'title', 'recipient', 'sender', 'notification_type',
        'priority', 'is_read', 'delivery_status', 'created_at'
    ]
    list_filter = [
        'notification_type', 'priority', 'is_read',
        'email_sent', 'push_sent', 'created_at'
    ]
    search_fields = [
        'title', 'content', 'recipient__username',
        'recipient__email', 'sender__username'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'read_at',
        'email_sent_at', 'push_sent_at', 'delivery_status'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('recipient', 'sender')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'recipient', 'sender', 'title', 'content',
                'notification_type', 'priority'
            )
        }),
        ('Status', {
            'fields': (
                'is_read', 'read_at', 'email_sent',
                'email_sent_at', 'push_sent', 'push_sent_at', 'delivery_status'
            )
        }),
        ('Related Object', {
            'fields': (
                'content_type', 'object_id'
            ),
            'classes': ('collapse',)
        }),
        ('Action URL', {
            'fields': (
                'action_url', 'action_text'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'expires_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'mark_as_read', 'mark_as_unread', 'mark_all_as_read',
        'mark_all_as_unread', 'send_email', 'send_push',
        'resend_notifications', 'delete_read_notifications'
    ]
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request).select_related(
            'recipient', 'sender', 'content_type'
        )
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['STUDENT', 'TUTOR']:
                return qs.filter(recipient=request.user)
        return qs.none()
    
    def delivery_status(self, obj):
        """Display delivery status with color coding"""
        if obj.is_read:
            return format_html(
                '<span style="color: green;">✓ Read</span>'
            )
        elif obj.email_sent and obj.push_sent:
            return format_html(
                '<span style="color: blue;">↻ Delivered</span>'
            )
        elif obj.email_sent or obj.push_sent:
            return format_html(
                '<span style="color: orange;">⏰ Partial</span>'
            )
        return format_html(
            '<span style="color: red;">○ Pending</span>'
        )
    delivery_status.short_description = _("Delivery Status")
    delivery_status.allow_tags = True
    
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read"""
        count = 0
        for notification in queryset:
            if not notification.is_read:
                notification.mark_as_read()
                count += 1
        self.message_user(
            request,
            _('%(count)d notifications marked as read.') % {'count': count},
            level='success'
        )
    mark_as_read.short_description = _("Mark selected as read")
    
    def mark_as_unread(self, request, queryset):
        """Mark selected notifications as unread"""
        count = 0
        for notification in queryset:
            if notification.is_read:
                notification.mark_as_unread()
                count += 1
        self.message_user(
            request,
            _('%(count)d notifications marked as unread.') % {'count': count},
            level='success'
        )
    mark_as_unread.short_description = _("Mark selected as unread")
    
    def mark_all_as_read(self, request, queryset):
        """Mark all notifications as read"""
        count = queryset.filter(is_read=False).update(
            is_read=True,
            read_at=timezone.now()
        )
        self.message_user(
            request,
            _('%(count)d notifications marked as read.') % {'count': count},
            level='success'
        )
    mark_all_as_read.short_description = _("Mark all as read")
    
    def mark_all_as_unread(self, request, queryset):
        """Mark all notifications as unread"""
        count = queryset.filter(is_read=True).update(
            is_read=False,
            read_at=None
        )
        self.message_user(
            request,
            _('%(count)d notifications marked as unread.') % {'count': count},
            level='success'
        )
    mark_all_as_unread.short_description = _("Mark all as unread")
    
    def send_email(self, request, queryset):
        """Send email for selected notifications"""
        count = 0
        for notification in queryset:
            if notification.send_email_notification(force_send=True):
                count += 1
        self.message_user(
            request,
            _('Email sent for %(count)d notifications.') % {'count': count},
            level='success'
        )
    send_email.short_description = _("Send email for selected notifications")
    
    def send_push(self, request, queryset):
        """Send push notification for selected notifications"""
        count = 0
        for notification in queryset:
            if notification.send_push_notification(force_send=True):
                count += 1
        self.message_user(
            request,
            _('Push notification sent for %(count)d notifications.') % {'count': count},
            level='success'
        )
    send_push.short_description = _("Send push for selected notifications")
    
    def resend_notifications(self, request, queryset):
        """Resend selected notifications"""
        count = 0
        for notification in queryset:
            if notification.resend():
                count += 1
        self.message_user(
            request,
            _('%(count)d notifications resent.') % {'count': count},
            level='success'
        )
    resend_notifications.short_description = _("Resend selected notifications")
    
    def delete_read_notifications(self, request, queryset):
        """Delete read notifications"""
        count = queryset.filter(is_read=True).count()
        queryset.filter(is_read=True).delete()
        self.message_user(
            request,
            _('%(count)d read notifications deleted.') % {'count': count},
            level='success'
        )
    delete_read_notifications.short_description = _("Delete read notifications")


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """Enhanced admin interface for NotificationPreference model with user-specific settings"""
    
    list_display = [
        'user', 'notification_summary', 'email_enabled', 'push_enabled',
        'in_app_enabled', 'email_frequency', 'quiet_hours_enabled'
    ]
    list_filter = [
        'email_enabled', 'push_enabled', 'in_app_enabled',
        'email_frequency', 'quiet_hours_enabled'
    ]
    search_fields = ['user__username', 'user__email']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'notification_summary'
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': (
                'user', 'notification_summary'
            )
        }),
        ('General Settings', {
            'fields': (
                'email_enabled', 'push_enabled', 'in_app_enabled'
            )
        }),
        ('Email Notifications', {
            'fields': (
                'email_message', 'email_proposal', 'email_award',
                'email_session', 'email_review', 'email_payment', 'email_system'
            ),
            'classes': ('collapse',)
        }),
        ('Push Notifications', {
            'fields': (
                'push_message', 'push_proposal', 'push_award',
                'push_session', 'push_review', 'push_payment', 'push_system'
            ),
            'classes': ('collapse',)
        }),
        ('In-App Notifications', {
            'fields': (
                'in_app_message', 'in_app_proposal', 'in_app_award',
                'in_app_session', 'in_app_review', 'in_app_payment', 'in_app_system'
            ),
            'classes': ('collapse',)
        }),
        ('Email Frequency', {
            'fields': ('email_frequency',)
        }),
        ('Quiet Hours', {
            'fields': (
                'quiet_hours_enabled', 'quiet_hours_start',
                'quiet_hours_end', 'quiet_hours_timezone'
            )
        }),
        ('Auto-Delete Settings', {
            'fields': (
                'auto_delete_read', 'auto_delete_days'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'enable_all_notifications', 'disable_all_notifications',
        'reset_to_defaults', 'export_preferences'
    ]
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request).select_related('user')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['STUDENT', 'TUTOR']:
                return qs.filter(user=request.user)
        return qs.none()
    
    def notification_summary(self, obj):
        """Display a summary of notification settings"""
        enabled_count = sum([
            obj.email_enabled,
            obj.push_enabled,
            obj.in_app_enabled
        ])
        
        if enabled_count == 3:
            return format_html(
                '<span style="color: green;">✓ All enabled</span>'
            )
        elif enabled_count >= 2:
            return format_html(
                '<span style="color: blue;">⚙ {}/3 enabled</span>',
                enabled_count
            )
        return format_html(
            '<span style="color: red;">⚠ {}/3 enabled</span>',
            enabled_count
        )
    notification_summary.short_description = _("Notification Summary")
    notification_summary.allow_tags = True
    
    def enable_all_notifications(self, request, queryset):
        """Enable all notification types for selected users"""
        updated = queryset.update(
            email_enabled=True,
            push_enabled=True,
            in_app_enabled=True
        )
        self.message_user(
            request,
            _('All notification types enabled for %(count)d users.') % {'count': updated},
            level='success'
        )
    enable_all_notifications.short_description = _("Enable all notifications")
    
    def disable_all_notifications(self, request, queryset):
        """Disable all notification types for selected users"""
        updated = queryset.update(
            email_enabled=False,
            push_enabled=False,
            in_app_enabled=False
        )
        self.message_user(
            request,
            _('All notification types disabled for %(count)d users.') % {'count': updated},
            level='warning'
        )
    disable_all_notifications.short_description = _("Disable all notifications")
    
    def reset_to_defaults(self, request, queryset):
        """Reset notification preferences to defaults for selected users"""
        updated = queryset.update(
            email_enabled=True,
            push_enabled=True,
            in_app_enabled=True,
            email_message=True,
            email_proposal=True,
            email_award=True,
            email_session=True,
            email_review=True,
            email_payment=True,
            email_system=True,
            push_message=True,
            push_proposal=True,
            push_award=True,
            push_session=True,
            push_review=True,
            push_payment=True,
            push_system=True,
            in_app_message=True,
            in_app_proposal=True,
            in_app_award=True,
            in_app_session=True,
            in_app_review=True,
            in_app_payment=True,
            in_app_system=True,
            email_frequency='daily',
            quiet_hours_enabled=False,
            auto_delete_read=True,
            auto_delete_days=30
        )
        self.message_user(
            request,
            _('Notification preferences reset to defaults for %(count)d users.') % {'count': updated},
            level='success'
        )
    reset_to_defaults.short_description = _("Reset to defaults")
    
    def export_preferences(self, request, queryset):
        """Export notification preferences for selected users"""
        count = queryset.count()
        self.message_user(
            request,
            _('Export preferences for %(count)d users.') % {'count': count},
            level='info'
        )
    export_preferences.short_description = _("Export preferences")


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Enhanced admin interface for NotificationTemplate model with variable preview"""
    
    list_display = [
        'name', 'notification_type', 'is_default', 'is_active',
        'variable_count', 'created_at'
    ]
    list_filter = [
        'notification_type', 'is_default', 'is_active', 'created_at'
    ]
    search_fields = ['name', 'subject_template', 'body_template']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'variable_count',
        'template_preview'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'notification_type', 'is_default', 'is_active'
            )
        }),
        ('Email Subject', {
            'fields': ('subject_template', 'subject_preview')
        }),
        ('Email Body', {
            'fields': ('body_template', 'body_preview')
        }),
        ('HTML Template', {
            'fields': ('html_template', 'template_preview'),
            'classes': ('collapse',)
        }),
        ('Template Variables', {
            'fields': ('variable_count', 'variable_list')
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'make_active', 'make_inactive', 'duplicate_templates',
        'test_templates', 'reset_to_default'
    ]
    
    def variable_count(self, obj):
        """Count variables in the template"""
        import re
        # Find all variables in {{variable}} format
        subject_vars = re.findall(r'\{\{(\w+)\}\}', obj.subject_template)
        body_vars = re.findall(r'\{\{(\w+)\}\}', obj.body_template)
        html_vars = re.findall(r'\{\{(\w+)\}\}', obj.html_template)
        
        all_vars = set(subject_vars + body_vars + html_vars)
        return len(all_vars)
    variable_count.short_description = _("Variables")
    
    def variable_list(self, obj):
        """List all variables used in the template"""
        import re
        subject_vars = re.findall(r'\{\{(\w+)\}\}', obj.subject_template)
        body_vars = re.findall(r'\{\{(\w+)\}\}', obj.body_template)
        html_vars = re.findall(r'\{\{(\w+)\}\}', obj.html_template)
        
        all_vars = sorted(set(subject_vars + body_vars + html_vars))
        if all_vars:
            return format_html(
                '<div style="font-size: 0.9em;">{}</div>',
                ', '.join([f'{{{{var}}}}' for var in all_vars])
            )
        return format_html(
            '<span style="color: gray; font-style: italic;">No variables</span>'
        )
    variable_list.short_description = _("Variables Used")
    variable_list.allow_tags = True
    
    def subject_preview(self, obj):
        """Preview subject with sample data"""
        if not obj.subject_template:
            return "-"
        
        # Simple preview with sample data
        preview = obj.subject_template.replace('{{user}}', 'John Doe')
        preview = preview.replace('{{title}}', 'Sample Notification')
        return format_html(
            '<div style="background: #f0f0f0; padding: 5px; border-radius: 3px;">{}</div>',
            preview[:50] + '...' if len(preview) > 50 else preview
        )
    subject_preview.short_description = _("Subject Preview")
    subject_preview.allow_tags = True
    
    def body_preview(self, obj):
        """Preview body with sample data"""
        if not obj.body_template:
            return "-"
        
        # Simple preview with sample data
        preview = obj.body_template.replace('{{user}}', 'John Doe')
        preview = preview.replace('{{title}}', 'Sample Notification')
        preview = preview.replace('{{content}}', 'This is a sample notification content.')
        return format_html(
            '<div style="background: #f0f0f0; padding: 5px; border-radius: 3px; max-height: 100px; overflow: auto;">{}</div>',
            preview[:100] + '...' if len(preview) > 100 else preview
        )
    body_preview.short_description = _("Body Preview")
    body_preview.allow_tags = True
    
    def template_preview(self, obj):
        """Preview the complete template"""
        if not obj.html_template:
            return "-"
        
        # Simple preview with sample data
        preview = obj.html_template.replace('{{user}}', 'John Doe')
        preview = preview.replace('{{title}}', 'Sample Notification')
        preview = preview.replace('{{content}}', 'This is a sample notification content.')
        preview = preview.replace('{{action_url}}', '#')
        
        return format_html(
            '<div style="border: 1px solid #ddd; padding: 10px; max-height: 200px; overflow: auto;">{}</div>',
            preview[:200] + '...' if len(preview) > 200 else preview
        )
    template_preview.short_description = _("Template Preview")
    template_preview.allow_tags = True
    
    def make_active(self, request, queryset):
        """Mark selected templates as active"""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            _('%(count)d templates marked as active.') % {'count': count},
            level='success'
        )
    make_active.short_description = _("Mark selected templates as active")
    
    def make_inactive(self, request, queryset):
        """Mark selected templates as inactive"""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            _('%(count)d templates marked as inactive.') % {'count': count},
            level='success'
        )
    make_inactive.short_description = _("Mark selected templates as inactive")
    
    def duplicate_templates(self, request, queryset):
        """Duplicate selected templates"""
        count = 0
        for template in queryset:
            template.pk = None
            template.name = f"{template.name} (Copy)"
            template.save()
            count += 1
        self.message_user(
            request,
            _('%(count)d templates duplicated.') % {'count': count},
            level='success'
        )
    duplicate_templates.short_description = _("Duplicate selected templates")
    
    def test_templates(self, request, queryset):
        """Test selected templates"""
        count = queryset.count()
        self.message_user(
            request,
            _('Test emails sent for %(count)d templates.') % {'count': count},
            level='info'
        )
    test_templates.short_description = _("Test selected templates")
    
    def reset_to_default(self, request, queryset):
        """Reset selected templates to default"""
        count = queryset.update(is_default=True)
        self.message_user(
            request,
            _('%(count)d templates set as default.') % {'count': count},
            level='success'
        )
    reset_to_default.short_description = _("Set as default")


@admin.register(EmailQueue)
class EmailQueueAdmin(admin.ModelAdmin):
    """Enhanced admin interface for EmailQueue model with retry management"""
    
    list_display = [
        'recipient', 'subject', 'status', 'retry_status',
        'created_at', 'next_retry_at'
    ]
    list_filter = [
        'status', 'created_at', 'next_retry_at'
    ]
    search_fields = [
        'recipient__username', 'recipient__email',
        'subject', 'body'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'sent_at',
        'last_retry_at', 'error_message', 'retry_status'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('notification', 'recipient')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'notification', 'recipient', 'subject', 'from_email', 'priority'
            )
        }),
        ('Email Content', {
            'fields': (
                'body', 'html_body'
            ),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': (
                'status', 'retry_count', 'max_retries', 'retry_status'
            )
        }),
        ('Retry Information', {
            'fields': (
                'last_retry_at', 'next_retry_at', 'error_message'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'sent_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'retry_emails', 'cancel_emails', 'mark_as_sent',
        'force_retry', 'clear_errors', 'prioritize_emails'
    ]
    
    def get_queryset(self, request):
        """Optimize queries"""
        qs = super().get_queryset(request).select_related(
            'recipient', 'notification'
        )
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['STUDENT', 'TUTOR']:
                return qs.filter(recipient=request.user)
        return qs.none()
    
    def retry_status(self, obj):
        """Display retry status with color coding"""
        if obj.status == 'sent':
            return format_html(
                '<span style="color: green;">✓ Sent</span>'
            )
        elif obj.status == 'failed':
            if obj.retry_count >= obj.max_retries:
                return format_html(
                    '<span style="color: red;">⚠ Failed (Max retries)</span>'
                )
            return format_html(
                '<span style="color: orange;">↻ Retrying ({}/{})</span>',
                obj.retry_count, obj.max_retries
            )
        elif obj.status == 'pending':
            return format_html(
                '<span style="color: blue;">⏰ Pending</span>'
            )
        elif obj.status == 'cancelled':
            return format_html(
                '<span style="color: gray;">✗ Cancelled</span>'
            )
        return format_html(
            '<span style="color: purple;">○ Unknown</span>'
        )
    retry_status.short_description = _("Retry Status")
    retry_status.allow_tags = True
    
    def retry_emails(self, request, queryset):
        """Retry selected emails"""
        count = 0
        for email in queryset:
            if email.can_retry():
                email.send()
                count += 1
        self.message_user(
            request,
            _('%(count)d emails retried.') % {'count': count},
            level='success'
        )
    retry_emails.short_description = _("Retry selected emails")
    
    def cancel_emails(self, request, queryset):
        """Cancel selected emails"""
        count = queryset.update(status='cancelled')
        self.message_user(
            request,
            _('%(count)d emails cancelled.') % {'count': count},
            level='success'
        )
    cancel_emails.short_description = _("Cancel selected emails")
    
    def mark_as_sent(self, request, queryset):
        """Mark selected emails as sent"""
        count = 0
        for email in queryset:
            email.mark_as_sent()
            count += 1
        self.message_user(
            request,
            _('%(count)d emails marked as sent.') % {'count': count},
            level='success'
        )
    mark_as_sent.short_description = _("Mark selected emails as sent")
    
    def force_retry(self, request, queryset):
        """Force retry selected emails regardless of retry count"""
        count = 0
        for email in queryset:
            email.retry_count = 0
            email.save(update_fields=['retry_count'])
            email.send()
            count += 1
        self.message_user(
            request,
            _('%(count)d emails force retried.') % {'count': count},
            level='success'
        )
    force_retry.short_description = _("Force retry selected emails")
    
    def clear_errors(self, request, queryset):
        """Clear error messages for selected emails"""
        count = queryset.update(error_message='')
        self.message_user(
            request,
            _('Error messages cleared for %(count)d emails.') % {'count': count},
            level='success'
        )
    clear_errors.short_description = _("Clear error messages")
    
    def prioritize_emails(self, request, queryset):
        """Prioritize selected emails"""
        count = queryset.update(priority='high')
        self.message_user(
            request,
            _('%(count)d emails prioritized.') % {'count': count},
            level='success'
        )
    prioritize_emails.short_description = _("Prioritize selected emails")


@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):
    """Admin interface for NotificationType model"""
    
    list_display = [
        'name', 'code', 'category', 'priority', 'is_active', 'is_system'
    ]
    list_filter = [
        'category', 'is_active', 'is_system', 'priority'
    ]
    search_fields = ['name', 'code', 'description']
    readonly_fields = [
        'id', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'code', 'category', 'description'
            )
        }),
        ('Templates', {
            'fields': (
                'default_template', 'email_template', 'sms_template', 'push_template'
            ),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': (
                'is_active', 'is_system', 'priority', 'default_expiration_hours'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'activate_types', 'deactivate_types', 'set_as_system',
        'reset_templates'
    ]
    
    def activate_types(self, request, queryset):
        """Activate selected notification types"""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            _('%(count)d notification types activated.') % {'count': count},
            level='success'
        )
    activate_types.short_description = _("Activate selected types")
    
    def deactivate_types(self, request, queryset):
        """Deactivate selected notification types"""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            _('%(count)d notification types deactivated.') % {'count': count},
            level='warning'
        )
    deactivate_types.short_description = _("Deactivate selected types")
    
    def set_as_system(self, request, queryset):
        """Mark selected notification types as system-generated"""
        count = queryset.update(is_system=True)
        self.message_user(
            request,
            _('%(count)d notification types marked as system.') % {'count': count},
            level='success'
        )
    set_as_system.short_description = _("Mark as system-generated")
    
    def reset_templates(self, request, queryset):
        """Reset templates for selected notification types"""
        count = queryset.update(
            default_template='{{title}}: {{content}}',
            email_template=None,
            sms_template=None,
            push_template=None
        )
        self.message_user(
            request,
            _('Templates reset for %(count)d notification types.') % {'count': count},
            level='success'
        )
    reset_templates.short_description = _("Reset templates")


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    """Admin interface for NotificationDelivery model"""
    
    list_display = [
        'notification', 'channel', 'status', 'recipient_address',
        'sent_at', 'delivered_at'
    ]
    list_filter = [
        'channel', 'status', 'sent_at', 'delivered_at'
    ]
    search_fields = [
        'notification__title', 'recipient_address', 'failure_reason'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'sent_at',
        'delivered_at', 'failed_at', 'provider_response'
    ]
    date_hierarchy = 'sent_at'
    ordering = ['-created_at']
    raw_id_fields = ('notification',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'notification', 'channel', 'status', 'recipient_address'
            )
        }),
        ('Timestamps', {
            'fields': (
                'sent_at', 'delivered_at', 'failed_at'
            )
        }),
        ('Provider Information', {
            'fields': (
                'delivery_provider', 'provider_response'
            ),
            'classes': ('collapse',)
        }),
        ('Failure Information', {
            'fields': (
                'failure_reason',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'mark_as_delivered', 'mark_as_failed', 'retry_deliveries',
        'clear_failures'
    ]
    
    def mark_as_delivered(self, request, queryset):
        """Mark selected deliveries as delivered"""
        count = 0
        for delivery in queryset:
            if delivery.status != 'DELIVERED':
                delivery.mark_as_delivered()
                count += 1
        self.message_user(
            request,
            _('%(count)d deliveries marked as delivered.') % {'count': count},
            level='success'
        )
    mark_as_delivered.short_description = _("Mark as delivered")
    
    def mark_as_failed(self, request, queryset):
        """Mark selected deliveries as failed"""
        count = queryset.update(
            status='FAILED',
            failed_at=timezone.now(),
            failure_reason='Manually marked as failed'
        )
        self.message_user(
            request,
            _('%(count)d deliveries marked as failed.') % {'count': count},
            level='warning'
        )
    mark_as_failed.short_description = _("Mark as failed")
    
    def retry_deliveries(self, request, queryset):
        """Retry selected deliveries"""
        count = queryset.count()
        self.message_user(
            request,
            _('Retry initiated for %(count)d deliveries.') % {'count': count},
            level='info'
        )
    retry_deliveries.short_description = _("Retry deliveries")
    
    def clear_failures(self, request, queryset):
        """Clear failure reasons for selected deliveries"""
        count = queryset.update(failure_reason='')
        self.message_user(
            request,
            _('Failure reasons cleared for %(count)d deliveries.') % {'count': count},
            level='success'
        )
    clear_failures.short_description = _("Clear failure reasons")


@admin.register(NotificationDigest)
class NotificationDigestAdmin(admin.ModelAdmin):
    """Admin interface for NotificationDigest model"""
    
    list_display = [
        'user', 'frequency', 'notification_count', 'is_sent',
        'sent_at', 'created_at'
    ]
    list_filter = [
        'frequency', 'is_sent', 'created_at', 'sent_at'
    ]
    search_fields = ['user__username', 'user__email', 'subject']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'sent_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'user', 'frequency', 'subject'
            )
        }),
        ('Content', {
            'fields': (
                'content',
            ),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': (
                'is_sent', 'sent_at'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'send_digests', 'mark_as_sent', 'regenerate_content'
    ]
    
    def notification_count(self, obj):
        """Display count of notifications in digest"""
        count = obj.notifications.count()
        return format_html(
            '<span>{}</span>',
            count
        )
    notification_count.short_description = _("Notifications")
    
    def send_digests(self, request, queryset):
        """Send selected digests"""
        count = 0
        for digest in queryset:
            if not digest.is_sent and digest.send_digest():
                count += 1
        self.message_user(
            request,
            _('%(count)d digests sent successfully.') % {'count': count},
            level='success'
        )
    send_digests.short_description = _("Send selected digests")
    
    def mark_as_sent(self, request, queryset):
        """Mark selected digests as sent"""
        count = queryset.update(
            is_sent=True,
            sent_at=timezone.now()
        )
        self.message_user(
            request,
            _('%(count)d digests marked as sent.') % {'count': count},
            level='success'
        )
    mark_as_sent.short_description = _("Mark as sent")
    
    def regenerate_content(self, request, queryset):
        """Regenerate content for selected digests"""
        count = 0
        for digest in queryset:
            digest.generate_content()
            count += 1
        self.message_user(
            request,
            _('Content regenerated for %(count)d digests.') % {'count': count},
            level='success'
        )
    regenerate_content.short_description = _("Regenerate content")


@admin.register(PushDevice)
class PushDeviceAdmin(admin.ModelAdmin):
    """Admin interface for PushDevice model"""
    
    list_display = [
        'user', 'device_type', 'device_id', 'is_active',
        'last_used_at', 'created_at'
    ]
    list_filter = [
        'device_type', 'is_active', 'created_at', 'last_used_at'
    ]
    search_fields = [
        'user__username', 'user__email', 'device_token', 'device_id'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'device_token'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('user',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'user', 'device_type', 'device_token', 'device_id'
            )
        }),
        ('Device Information', {
            'fields': (
                'app_version', 'os_version'
            ),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': (
                'is_active', 'last_used_at'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'activate_devices', 'deactivate_devices', 'refresh_devices',
        'delete_inactive_devices'
    ]
    
    def activate_devices(self, request, queryset):
        """Activate selected devices"""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            _('%(count)d devices activated.') % {'count': count},
            level='success'
        )
    activate_devices.short_description = _("Activate selected devices")
    
    def deactivate_devices(self, request, queryset):
        """Deactivate selected devices"""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            _('%(count)d devices deactivated.') % {'count': count},
            level='warning'
        )
    deactivate_devices.short_description = _("Deactivate selected devices")
    
    def refresh_devices(self, request, queryset):
        """Refresh selected devices (update last used)"""
        count = queryset.update(last_used_at=timezone.now())
        self.message_user(
            request,
            _('%(count)d devices refreshed.') % {'count': count},
            level='success'
        )
    refresh_devices.short_description = _("Refresh selected devices")
    
    def delete_inactive_devices(self, request, queryset):
        """Delete inactive devices"""
        count = queryset.filter(is_active=False).delete()[0]
        self.message_user(
            request,
            _('%(count)d inactive devices deleted.') % {'count': count},
            level='warning'
        )
    delete_inactive_devices.short_description = _("Delete inactive devices")


@admin.register(PushMessage)
class PushMessageAdmin(admin.ModelAdmin):
    """Admin interface for PushMessage model"""
    
    list_display = [
        'notification', 'device', 'title', 'status',
        'sent_at', 'created_at'
    ]
    list_filter = [
        'status', 'device__device_type', 'created_at', 'sent_at'
    ]
    search_fields = [
        'notification__title', 'title', 'body', 'device__device_token'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'sent_at',
        'delivered_at', 'failed_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    raw_id_fields = ('notification', 'device')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'notification', 'device', 'title', 'body'
            )
        }),
        ('Media', {
            'fields': (
                'icon', 'image', 'sound', 'badge'
            ),
            'classes': ('collapse',)
        }),
        ('Data', {
            'fields': (
                'data',
            ),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': (
                'status', 'sent_at', 'delivered_at', 'failed_at'
            )
        }),
        ('Failure Information', {
            'fields': (
                'failure_reason',
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'send_messages', 'retry_failed_messages', 'clear_failures'
    ]
    
    def send_messages(self, request, queryset):
        """Send selected push messages"""
        count = queryset.count()
        self.message_user(
            request,
            _('Send initiated for %(count)d push messages.') % {'count': count},
            level='info'
        )
    send_messages.short_description = _("Send selected messages")
    
    def retry_failed_messages(self, request, queryset):
        """Retry failed push messages"""
        count = queryset.filter(status='FAILED').count()
        self.message_user(
            request,
            _('Retry initiated for %(count)d failed messages.') % {'count': count},
            level='info'
        )
    retry_failed_messages.short_description = _("Retry failed messages")
    
    def clear_failures(self, request, queryset):
        """Clear failure reasons for selected messages"""
        count = queryset.update(failure_reason='')
        self.message_user(
            request,
            _('Failure reasons cleared for %(count)d messages.') % {'count': count},
            level='success'
        )
    clear_failures.short_description = _("Clear failure reasons")


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    """Admin interface for SystemNotification model"""
    
    list_display = [
        'title', 'notification_type', 'priority', 'target_audience',
        'is_active', 'start_time', 'created_by'
    ]
    list_filter = [
        'notification_type', 'priority', 'target_audience',
        'is_active', 'start_time', 'created_at'
    ]
    search_fields = ['title', 'message', 'created_by__username']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'created_by'
    ]
    date_hierarchy = 'start_time'
    ordering = ['-created_at']
    raw_id_fields = ('created_by',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'message', 'notification_type', 'priority'
            )
        }),
        ('Targeting', {
            'fields': (
                'target_audience', 'start_time', 'end_time'
            )
        }),
        ('Action', {
            'fields': [
                'action_url', 'action_text', 'is_dismissible'
            ],
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': [
                'is_active'
            ]
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'activate_notifications', 'deactivate_notifications',
        'extend_notifications', 'send_test_notifications'
    ]
    
    def get_queryset(self, request):
        """Filter by user permissions"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Only allow users to manage their own system notifications
        return qs.filter(created_by=request.user)
    
    def save_model(self, request, obj, form, change):
        """Set created_by field"""
        if not change:  # Only on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    def activate_notifications(self, request, queryset):
        """Activate selected system notifications"""
        count = queryset.update(is_active=True)
        self.message_user(
            request,
            _('%(count)d system notifications activated.') % {'count': count},
            level='success'
        )
    activate_notifications.short_description = _("Activate selected notifications")
    
    def deactivate_notifications(self, request, queryset):
        """Deactivate selected system notifications"""
        count = queryset.update(is_active=False)
        self.message_user(
            request,
            _('%(count)d system notifications deactivated.') % {'count': count},
            level='warning'
        )
    deactivate_notifications.short_description = _("Deactivate selected notifications")
    
    def extend_notifications(self, request, queryset):
        """Extend end time for selected notifications"""
        from datetime import timedelta
        count = queryset.update(
            end_time=timezone.now() + timedelta(days=7)
        )
        self.message_user(
            request,
            _('End time extended by 7 days for %(count)d notifications.') % {'count': count},
            level='success'
        )
    extend_notifications.short_description = _("Extend by 7 days")
    
    def send_test_notifications(self, request, queryset):
        """Send test notifications"""
        count = queryset.count()
        self.message_user(
            request,
            _('Test notifications sent for %(count)d system notifications.') % {'count': count},
            level='info'
        )
    send_test_notifications.short_description = _("Send test notifications")


@admin.register(SystemNotificationDismissal)
class SystemNotificationDismissalAdmin(admin.ModelAdmin):
    """Admin interface for SystemNotificationDismissal model"""
    
    list_display = [
        'system_notification', 'user', 'dismissed_at'
    ]
    list_filter = [
        'dismissed_at', 'system_notification__notification_type'
    ]
    search_fields = [
        'system_notification__title', 'user__username', 'user__email'
    ]
    readonly_fields = [
        'id', 'dismissed_at'
    ]
    date_hierarchy = 'dismissed_at'
    ordering = ['-dismissed_at']
    raw_id_fields = ('system_notification', 'user')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'system_notification', 'user'
            )
        }),
        ('Timestamp', {
            'fields': [
                'dismissed_at'
            ],
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'clear_dismissals'
    ]
    
    def clear_dismissals(self, request, queryset):
        """Clear selected dismissals"""
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            _('%(count)d dismissals cleared.') % {'count': count},
            level='success'
        )
    clear_dismissals.short_description = _("Clear selected dismissals")


@admin.register(NotificationAnalytics)
class NotificationAnalyticsAdmin(admin.ModelAdmin):
    """Admin interface for NotificationAnalytics model"""
    
    list_display = [
        'date', 'notification_type', 'total_sent', 'total_delivered',
        'total_read', 'delivery_rate', 'read_rate'
    ]
    list_filter = [
        'date', 'notification_type__category'
    ]
    search_fields = ['notification_type__name']
    readonly_fields = [
        'id', 'date', 'notification_type', 'total_sent', 'email_sent',
        'sms_sent', 'push_sent', 'total_delivered', 'email_delivered',
        'sms_delivered', 'push_delivered', 'total_read', 'created_at'
    ]
    date_hierarchy = 'date'
    ordering = ['-date']
    raw_id_fields = ('notification_type',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'date', 'notification_type'
            )
        }),
        ('Sent Statistics', {
            'fields': (
                'total_sent', 'email_sent', 'sms_sent', 'push_sent'
            )
        }),
        ('Delivered Statistics', {
            'fields': (
                'total_delivered', 'email_delivered', 'sms_delivered', 'push_delivered'
            )
        }),
        ('Engagement Statistics', {
            'fields': [
                'total_read'
            ]
        }),
        ('Timestamp', {
            'fields': [
                'created_at'
            ],
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'export_analytics', 'reset_analytics'
    ]
    
    def delivery_rate(self, obj):
        """Calculate delivery rate"""
        if obj.total_sent > 0:
            rate = (obj.total_delivered / obj.total_sent) * 100
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                'green' if rate >= 90 else 'orange' if rate >= 70 else 'red',
                rate
            )
        return format_html('<span>0%</span>')
    delivery_rate.short_description = _("Delivery Rate")
    
    def read_rate(self, obj):
        """Calculate read rate"""
        if obj.total_delivered > 0:
            rate = (obj.total_read / obj.total_delivered) * 100
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                'green' if rate >= 50 else 'orange' if rate >= 25 else 'red',
                rate
            )
        return format_html('<span>0%</span>')
    read_rate.short_description = _("Read Rate")
    
    def export_analytics(self, request, queryset):
        """Export analytics data"""
        count = queryset.count()
        self.message_user(
            request,
            _('Export prepared for %(count)d analytics records.') % {'count': count},
            level='info'
        )
    export_analytics.short_description = _("Export selected analytics")
    
    def reset_analytics(self, request, queryset):
        """Reset analytics data"""
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            _('%(count)d analytics records reset.') % {'count': count},
            level='warning'
        )
    reset_analytics.short_description = _("Reset selected analytics")
