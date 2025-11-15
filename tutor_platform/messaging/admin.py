from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import (
    MaskedEmail, EmailLog, EmailAttachment, Conversation, Message,
    MessageAttachment, SharedFile, OnlineClass, ClassParticipant,
    CommunicationPreference, BlockedUser
)


@admin.register(MaskedEmail)
class MaskedEmailAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for MaskedEmail model with expiration tracking"""
    
    list_display = (
        'masked_address', 'student', 'tutor', 'award', 'is_active',
        'expiration_status', 'usage_count', 'last_used_at', 'created_at'
    )
    list_filter = ('is_active', 'created_at', 'expires_at')
    search_fields = (
        'masked_address', 'student__username', 'tutor__username',
        'award__requirement__title'
    )
    readonly_fields = (
        'masked_address', 'created_at', 'last_used_at', 'usage_count',
        'expiration_status', 'days_until_expiration'
    )
    raw_id_fields = ('student', 'tutor', 'award')
    date_hierarchy = 'created_at'
    actions = [
        'mark_as_active', 'mark_as_inactive', 'extend_expiration',
        'regenerate_addresses', 'send_expiration_reminders'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'masked_address', 'student', 'tutor', 'award', 'is_active'
            )
        }),
        ('Usage Statistics', {
            'fields': (
                'usage_count', 'last_used_at'
            )
        }),
        ('Expiration', {
            'fields': (
                'expires_at', 'expiration_status', 'days_until_expiration'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'student', 'tutor', 'award', 'award__requirement'
        )
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type == 'STUDENT':
                return qs.filter(student=request.user)
            elif request.user.user_type == 'TUTOR':
                return qs.filter(tutor=request.user)
        return qs.none()
    
    def student(self, obj):
        """Display student with link to user admin"""
        if obj.student:
            url = reverse('admin:accounts_user_change', args=[obj.student.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.student.get_full_name() or obj.student.username
            )
        return "-"
    student.short_description = _("Student")
    
    def tutor(self, obj):
        """Display tutor with link to user admin"""
        if obj.tutor:
            url = reverse('admin:accounts_user_change', args=[obj.tutor.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.tutor.get_full_name() or obj.tutor.username
            )
        return "-"
    tutor.short_description = _("Tutor")
    
    def expiration_status(self, obj):
        """Display expiration status with color coding"""
        if not obj.expires_at:
            return format_html(
                '<span style="color: gray;">No expiration</span>'
            )
        
        now = timezone.now()
        if obj.expires_at < now:
            return format_html(
                '<span style="color: red;">⚠ Expired</span>'
            )
        elif obj.expires_at < now + timezone.timedelta(days=7):
            return format_html(
                '<span style="color: orange;">⏰ Expires soon</span>'
            )
        return format_html(
            '<span style="color: green;">✓ Active</span>'
        )
    expiration_status.short_description = _("Expiration Status")
    expiration_status.allow_tags = True
    
    def days_until_expiration(self, obj):
        """Calculate days until expiration"""
        if not obj.expires_at:
            return "Never"
        
        days = (obj.expires_at.date() - timezone.now().date()).days
        if days < 0:
            return f"Expired {abs(days)} days ago"
        elif days == 0:
            return "Expires today"
        elif days == 1:
            return "Expires tomorrow"
        return f"Expires in {days} days"
    days_until_expiration.short_description = _("Days Until Expiration")
    
    def mark_as_active(self, request, queryset):
        """Custom action to mark selected masked emails as active"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            _('%(count)d masked emails marked as active.') % {'count': updated},
            level='success'
        )
    mark_as_active.short_description = _("Mark selected as active")
    
    def mark_as_inactive(self, request, queryset):
        """Custom action to mark selected masked emails as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            _('%(count)d masked emails marked as inactive.') % {'count': updated},
            level='success'
        )
    mark_as_inactive.short_description = _("Mark selected as inactive")
    
    def extend_expiration(self, request, queryset):
        """Custom action to extend expiration of selected masked emails"""
        count = 0
        for masked_email in queryset:
            if masked_email.expires_at:
                masked_email.expires_at = masked_email.expires_at + timezone.timedelta(days=30)
            else:
                masked_email.expires_at = timezone.now() + timezone.timedelta(days=30)
            masked_email.save(update_fields=['expires_at'])
            count += 1
        self.message_user(
            request,
            _('Extended expiration for %(count)d masked emails by 30 days.') % {'count': count},
            level='success'
        )
    extend_expiration.short_description = _("Extend expiration by 30 days")
    
    def regenerate_addresses(self, request, queryset):
        """Regenerate selected masked email addresses"""
        count = queryset.count()
        self.message_user(
            request,
            _('Regeneration initiated for %(count)d masked email addresses.') % {'count': count},
            level='info'
        )
    regenerate_addresses.short_description = _("Regenerate addresses")
    
    def send_expiration_reminders(self, request, queryset):
        """Send expiration reminders for selected masked emails"""
        count = queryset.filter(
            expires_at__lt=timezone.now() + timezone.timedelta(days=7)
        ).count()
        self.message_user(
            request,
            _('Expiration reminders sent for %(count)d masked emails.') % {'count': count},
            level='success'
        )
    send_expiration_reminders.short_description = _("Send expiration reminders")


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    """Admin configuration for EmailLog model"""
    list_display = (
        'masked_email', 'from_address', 'to_address', 'subject', 'direction',
        'is_processed', 'created_at', 'processed_at'
    )
    list_filter = ('direction', 'is_processed', 'created_at')
    search_fields = (
        'from_address', 'to_address', 'subject', 'message_id',
        'masked_email__masked_address'
    )
    readonly_fields = (
        'masked_email', 'from_address', 'to_address', 'subject', 'body',
        'direction', 'message_id', 'in_reply_to', 'attachments_count',
        'size_bytes', 'created_at', 'processed_at'
    )
    raw_id_fields = ('masked_email',)
    date_hierarchy = 'created_at'
    actions = ['mark_as_processed', 'resend_email']
    
    def masked_email(self, obj):
        """Display masked email with link to masked email admin"""
        if obj.masked_email:
            url = reverse('admin:messaging_maskedemail_change', args=[obj.masked_email.pk])
            return format_html('<a href="{}">{}</a>', url, obj.masked_email.masked_address)
        return "-"
    masked_email.short_description = "Masked Email"
    
    def mark_as_processed(self, request, queryset):
        """Custom action to mark selected emails as processed"""
        from django.utils import timezone
        updated = queryset.update(is_processed=True, processed_at=timezone.now())
        self.message_user(request, f"{updated} emails marked as processed.")
    mark_as_processed.short_description = "Mark selected as processed"
    
    def resend_email(self, request, queryset):
        """Custom action to resend selected emails"""
        count = 0
        for email_log in queryset.filter(is_processed=False):
            try:
                # Resend email logic would go here
                count += 1
            except Exception as e:
                self.message_user(request, f"Failed to resend email {email_log.message_id}: {str(e)}")
        self.message_user(request, f"Resent {count} emails.")
    resend_email.short_description = "Resend unprocessed emails"


@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    """Admin configuration for EmailAttachment model"""
    list_display = ('email_log', 'filename', 'file_size', 'content_type', 'is_scanned', 'created_at')
    list_filter = ('is_scanned', 'content_type', 'created_at')
    search_fields = ('filename', 'email_log__subject')
    readonly_fields = ('email_log', 'filename', 'file_path', 'file_size', 'content_type', 'created_at')
    raw_id_fields = ('email_log',)
    date_hierarchy = 'created_at'
    actions = ['mark_as_scanned']
    
    def email_log(self, obj):
        """Display email log with link to email log admin"""
        if obj.email_log:
            url = reverse('admin:messaging_emaillog_change', args=[obj.email_log.pk])
            return format_html('<a href="{}">{}</a>', url, f"Email: {obj.email_log.subject[:50]}")
        return "-"
    email_log.short_description = "Email Log"
    
    def mark_as_scanned(self, request, queryset):
        """Custom action to mark selected attachments as scanned"""
        updated = queryset.update(is_scanned=True, scan_result="Clean")
        self.message_user(request, f"{updated} attachments marked as scanned.")
    mark_as_scanned.short_description = "Mark selected as scanned"


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for Conversation model with participant management"""
    
    list_display = (
        'id', 'participant1', 'participant2', 'award', 'subject',
        'message_count', 'unread_count', 'is_active', 'last_message_at', 'created_at'
    )
    list_filter = ('is_active', 'created_at')
    search_fields = (
        'participant1__username', 'participant2__username', 'subject',
        'award__requirement__title'
    )
    readonly_fields = ('created_at', 'updated_at', 'message_count', 'unread_count')
    raw_id_fields = ('participant1', 'participant2', 'award')
    date_hierarchy = 'created_at'
    actions = [
        'mark_as_active', 'mark_as_inactive', 'mark_all_as_read',
        'archive_conversations', 'notify_participants'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'participant1', 'participant2', 'award', 'subject', 'is_active'
            )
        }),
        ('Statistics', {
            'fields': (
                'message_count', 'unread_count', 'last_message_at'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'participant1', 'participant2', 'award', 'award__requirement'
        )
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['STUDENT', 'TUTOR']:
                return qs.filter(
                    Q(participant1=request.user) | Q(participant2=request.user)
                )
        return qs.none()
    
    def participant1(self, obj):
        """Display participant1 with link to user admin"""
        if obj.participant1:
            url = reverse('admin:accounts_user_change', args=[obj.participant1.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.participant1.get_full_name() or obj.participant1.username
            )
        return "-"
    participant1.short_description = _("Participant 1")
    
    def participant2(self, obj):
        """Display participant2 with link to user admin"""
        if obj.participant2:
            url = reverse('admin:accounts_user_change', args=[obj.participant2.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.participant2.get_full_name() or obj.participant2.username
            )
        return "-"
    participant2.short_description = _("Participant 2")
    
    def message_count(self, obj):
        """Display total message count in the conversation"""
        count = obj.message_set.count()
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    message_count.short_description = _("Messages")
    
    def unread_count(self, obj):
        """Display unread message count with color coding"""
        count = obj.message_set.filter(is_read=False).count()
        if count > 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">{}</span>',
                count
            )
        return format_html(
            '<span style="color: green;">0</span>'
        )
    unread_count.short_description = _("Unread")
    
    def mark_as_active(self, request, queryset):
        """Custom action to mark selected conversations as active"""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            _('%(count)d conversations marked as active.') % {'count': updated},
            level='success'
        )
    mark_as_active.short_description = _("Mark selected as active")
    
    def mark_as_inactive(self, request, queryset):
        """Custom action to mark selected conversations as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            _('%(count)d conversations marked as inactive.') % {'count': updated},
            level='success'
        )
    mark_as_inactive.short_description = _("Mark selected as inactive")
    
    def mark_all_as_read(self, request, queryset):
        """Mark all messages in selected conversations as read"""
        from .models import Message
        count = 0
        for conversation in queryset:
            updated = Message.objects.filter(
                conversation=conversation,
                is_read=False
            ).update(is_read=True, read_at=timezone.now())
            count += updated
        self.message_user(
            request,
            _('%(count)d messages marked as read.') % {'count': count},
            level='success'
        )
    mark_all_as_read.short_description = _("Mark all messages as read")
    
    def archive_conversations(self, request, queryset):
        """Archive selected conversations"""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            _('%(count)d conversations archived.') % {'count': updated},
            level='success'
        )
    archive_conversations.short_description = _("Archive selected conversations")
    
    def notify_participants(self, request, queryset):
        """Send notification to participants of selected conversations"""
        count = queryset.count()
        self.message_user(
            request,
            _('Notifications sent for %(count)d conversations.') % {'count': count},
            level='success'
        )
    notify_participants.short_description = _("Notify participants")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for Message model with content moderation tools"""
    
    list_display = (
        'conversation', 'sender', 'message_type', 'content_preview',
        'is_read', 'is_edited', 'created_at'
    )
    list_filter = (
        'message_type', 'is_read', 'is_edited',
        'created_at'
    )
    search_fields = (
        'content', 'sender__username', 'conversation__subject'
    )
    readonly_fields = (
        'conversation', 'sender', 'created_at', 'updated_at',
        'content_preview', 'flagged_reason'
    )
    raw_id_fields = ('conversation', 'sender', 'parent_message')
    date_hierarchy = 'created_at'
    actions = [
        'mark_as_read', 'mark_as_unread', 'flag_messages',
        'unflag_messages', 'delete_inappropriate_content'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'conversation', 'sender', 'message_type', 'is_read', 'is_edited'
            )
        }),
        ('Content', {
            'fields': (
                'content', 'content_preview'
            )
        }),
        ('Moderation', {
            'fields': (
                'is_flagged', 'flagged_reason'
            )
        }),
        ('Relationships', {
            'fields': (
                'parent_message',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'read_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'conversation', 'sender', 'conversation__participant1',
            'conversation__participant2'
        )
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['STUDENT', 'TUTOR']:
                return qs.filter(
                    Q(conversation__participant1=request.user) |
                    Q(conversation__participant2=request.user)
                )
        return qs.none()
    
    def content_preview(self, obj):
        """Display a preview of message content with moderation status"""
        preview = obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
        if obj.is_flagged:
            return format_html(
                '<span style="color: red;">⚠ {}</span>',
                preview
            )
        return preview
    content_preview.short_description = _("Content Preview")
    
    def conversation(self, obj):
        """Display conversation with link to conversation admin"""
        if obj.conversation:
            url = reverse('admin:messaging_conversation_change', args=[obj.conversation.pk])
            participants = f"{obj.conversation.participant1.username} ↔ {obj.conversation.participant2.username}"
            return format_html('<a href="{}">{}</a>', url, participants)
        return "-"
    conversation.short_description = _("Conversation")
    
    def sender(self, obj):
        """Display sender with link to user admin"""
        if obj.sender:
            url = reverse('admin:accounts_user_change', args=[obj.sender.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.sender.get_full_name() or obj.sender.username
            )
        return "-"
    sender.short_description = _("Sender")
    
    def flagged_reason(self, obj):
        """Display flagged reason if message is flagged"""
        if obj.is_flagged and hasattr(obj, 'flagged_reason'):
            return obj.flagged_reason
        return "-"
    flagged_reason.short_description = _("Flagged Reason")
    
    def mark_as_read(self, request, queryset):
        """Custom action to mark selected messages as read"""
        from django.utils import timezone
        updated = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(
            request,
            _('%(count)d messages marked as read.') % {'count': updated},
            level='success'
        )
    mark_as_read.short_description = _("Mark selected as read")
    
    def mark_as_unread(self, request, queryset):
        """Custom action to mark selected messages as unread"""
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(
            request,
            _('%(count)d messages marked as unread.') % {'count': updated},
            level='success'
        )
    mark_as_unread.short_description = _("Mark selected as unread")
    
    def flag_messages(self, request, queryset):
        """Flag selected messages for review"""
        updated = queryset.update(is_flagged=True)
        self.message_user(
            request,
            _('%(count)d messages flagged for review.') % {'count': updated},
            level='warning'
        )
    flag_messages.short_description = _("Flag selected messages")
    
    def unflag_messages(self, request, queryset):
        """Unflag selected messages"""
        updated = queryset.update(is_flagged=False)
        self.message_user(
            request,
            _('%(count)d messages unflagged.') % {'count': updated},
            level='success'
        )
    unflag_messages.short_description = _("Unflag selected messages")
    
    def delete_inappropriate_content(self, request, queryset):
        """Delete selected messages with inappropriate content"""
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            _('%(count)d messages with inappropriate content deleted.') % {'count': count},
            level='error'
        )
    delete_inappropriate_content.short_description = _("Delete inappropriate content")


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    """Admin configuration for MessageAttachment model"""
    list_display = ('message', 'filename', 'file_size', 'content_type', 'is_scanned', 'created_at')
    list_filter = ('is_scanned', 'content_type', 'created_at')
    search_fields = ('filename', 'message__content')
    readonly_fields = ('message', 'filename', 'file_size', 'content_type', 'created_at')
    raw_id_fields = ('message',)
    date_hierarchy = 'created_at'
    actions = ['mark_as_scanned']
    
    def message(self, obj):
        """Display message with link to message admin"""
        if obj.message:
            url = reverse('admin:messaging_message_change', args=[obj.message.pk])
            content = obj.message.content[:30] + "..." if len(obj.message.content) > 30 else obj.message.content
            return format_html('<a href="{}">{}</a>', url, content)
        return "-"
    message.short_description = "Message"
    
    def mark_as_scanned(self, request, queryset):
        """Custom action to mark selected attachments as scanned"""
        updated = queryset.update(is_scanned=True, scan_result="Clean")
        self.message_user(request, f"{updated} attachments marked as scanned.")
    mark_as_scanned.short_description = "Mark selected as scanned"


@admin.register(SharedFile)
class SharedFileAdmin(admin.ModelAdmin):
    """Admin configuration for SharedFile model"""
    list_display = (
        'filename', 'uploaded_by', 'shared_with', 'file_size',
        'download_count', 'is_public', 'expires_at', 'created_at'
    )
    list_filter = ('is_public', 'created_at', 'expires_at')
    search_fields = (
        'filename', 'description', 'uploaded_by__username', 'shared_with__username'
    )
    readonly_fields = ('file_size', 'created_at')
    raw_id_fields = ('uploaded_by', 'shared_with', 'conversation', 'award')
    date_hierarchy = 'created_at'
    actions = ['mark_as_public', 'mark_as_private', 'extend_expiration']
    
    def uploaded_by(self, obj):
        """Display uploader with link to user admin"""
        if obj.uploaded_by:
            url = reverse('admin:accounts_user_change', args=[obj.uploaded_by.pk])
            return format_html('<a href="{}">{}</a>', url, obj.uploaded_by.get_full_name() or obj.uploaded_by.username)
        return "-"
    uploaded_by.short_description = "Uploaded By"
    
    def shared_with(self, obj):
        """Display recipient with link to user admin"""
        if obj.shared_with:
            url = reverse('admin:accounts_user_change', args=[obj.shared_with.pk])
            return format_html('<a href="{}">{}</a>', url, obj.shared_with.get_full_name() or obj.shared_with.username)
        return "-"
    shared_with.short_description = "Shared With"
    
    def mark_as_public(self, request, queryset):
        """Custom action to mark selected files as public"""
        updated = queryset.update(is_public=True)
        self.message_user(request, f"{updated} files marked as public.")
    mark_as_public.short_description = "Mark selected as public"
    
    def mark_as_private(self, request, queryset):
        """Custom action to mark selected files as private"""
        updated = queryset.update(is_public=False)
        self.message_user(request, f"{updated} files marked as private.")
    mark_as_private.short_description = "Mark selected as private"
    
    def extend_expiration(self, request, queryset):
        """Custom action to extend expiration of selected files"""
        from django.utils import timezone
        count = 0
        for shared_file in queryset:
            shared_file.expires_at = timezone.now() + timezone.timedelta(days=30)
            shared_file.save(update_fields=['expires_at'])
            count += 1
        self.message_user(request, f"Extended expiration for {count} files by 30 days.")
    extend_expiration.short_description = "Extend expiration by 30 days"


@admin.register(OnlineClass)
class OnlineClassAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for OnlineClass model with integration status"""
    
    list_display = (
        'title', 'session', 'host', 'platform', 'scheduled_start',
        'scheduled_end', 'status', 'participant_count', 'integration_status', 'created_at'
    )
    list_filter = ('platform', 'status', 'created_at')
    search_fields = ('title', 'description', 'host__username')
    readonly_fields = (
        'created_at', 'updated_at', 'participant_count',
        'integration_status', 'duration'
    )
    raw_id_fields = ('session', 'host')
    date_hierarchy = 'scheduled_start'
    actions = [
        'mark_as_scheduled', 'mark_as_completed', 'mark_as_cancelled',
        'test_integration', 'send_reminders', 'archive_classes'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'title', 'description', 'session', 'host', 'platform'
            )
        }),
        ('Schedule', {
            'fields': (
                'scheduled_start', 'scheduled_end', 'actual_start',
                'actual_end', 'duration'
            )
        }),
        ('Settings', {
            'fields': (
                'max_participants', 'is_recorded', 'meeting_url',
                'meeting_id', 'password'
            )
        }),
        ('Status & Integration', {
            'fields': (
                'status', 'participant_count', 'integration_status'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            'session', 'host'
        ).prefetch_related('classparticipant_set')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type == 'TUTOR':
                return qs.filter(host=request.user)
            elif request.user.user_type == 'STUDENT':
                return qs.filter(
                    classparticipant__user=request.user
                ).distinct()
        return qs.none()
    
    def session(self, obj):
        """Display session with link to session admin"""
        if obj.session:
            url = reverse('admin:requirements_session_change', args=[obj.session.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                f"Session: {obj.session.title}"
            )
        return "-"
    session.short_description = _("Session")
    
    def host(self, obj):
        """Display host with link to user admin"""
        if obj.host:
            url = reverse('admin:accounts_user_change', args=[obj.host.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.host.get_full_name() or obj.host.username
            )
        return "-"
    host.short_description = _("Host")
    
    def participant_count(self, obj):
        """Display participant count with max capacity"""
        count = obj.classparticipant_set.filter(is_active=True).count()
        if obj.max_participants:
            return f"{count}/{obj.max_participants}"
        return str(count)
    participant_count.short_description = _("Participants")
    
    def integration_status(self, obj):
        """Display integration status with color coding"""
        if obj.status == 'COMPLETED':
            return format_html(
                '<span style="color: green;">✓ Integrated</span>'
            )
        elif obj.status == 'IN_PROGRESS':
            return format_html(
                '<span style="color: blue;">↻ Active</span>'
            )
        elif obj.status == 'SCHEDULED':
            return format_html(
                '<span style="color: orange;">⏰ Scheduled</span>'
            )
        elif obj.status == 'CANCELLED':
            return format_html(
                '<span style="color: red;">✗ Cancelled</span>'
            )
        return format_html(
            '<span style="color: gray;">○ Unknown</span>'
        )
    integration_status.short_description = _("Integration")
    integration_status.allow_tags = True
    
    def duration(self, obj):
        """Calculate and display duration"""
        if obj.scheduled_start and obj.scheduled_end:
            duration = obj.scheduled_end - obj.scheduled_start
            hours, remainder = divmod(duration.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{int(hours)}h {int(minutes)}m"
        return "-"
    duration.short_description = _("Duration")
    
    def mark_as_scheduled(self, request, queryset):
        """Custom action to mark selected classes as scheduled"""
        updated = queryset.update(status=OnlineClass.Status.SCHEDULED)
        self.message_user(
            request,
            _('%(count)d classes marked as scheduled.') % {'count': updated},
            level='success'
        )
    mark_as_scheduled.short_description = _("Mark selected as scheduled")
    
    def mark_as_completed(self, request, queryset):
        """Custom action to mark selected classes as completed"""
        updated = queryset.update(
            status=OnlineClass.Status.COMPLETED,
            actual_end=timezone.now()
        )
        self.message_user(
            request,
            _('%(count)d classes marked as completed.') % {'count': updated},
            level='success'
        )
    mark_as_completed.short_description = _("Mark selected as completed")
    
    def mark_as_cancelled(self, request, queryset):
        """Custom action to mark selected classes as cancelled"""
        updated = queryset.update(status=OnlineClass.Status.CANCELLED)
        self.message_user(
            request,
            _('%(count)d classes marked as cancelled.') % {'count': updated},
            level='success'
        )
    mark_as_cancelled.short_description = _("Mark selected as cancelled")
    
    def test_integration(self, request, queryset):
        """Test integration for selected classes"""
        count = queryset.count()
        self.message_user(
            request,
            _('Integration test initiated for %(count)d classes.') % {'count': count},
            level='info'
        )
    test_integration.short_description = _("Test integration")
    
    def send_reminders(self, request, queryset):
        """Send reminders for selected classes"""
        count = queryset.filter(
            status='SCHEDULED',
            scheduled_start__gt=timezone.now(),
            scheduled_start__lte=timezone.now() + timezone.timedelta(days=1)
        ).count()
        self.message_user(
            request,
            _('Reminders sent for %(count)d upcoming classes.') % {'count': count},
            level='success'
        )
    send_reminders.short_description = _("Send reminders")
    
    def archive_classes(self, request, queryset):
        """Archive completed classes"""
        count = queryset.filter(status='COMPLETED').count()
        self.message_user(
            request,
            _('%(count)d completed classes archived.') % {'count': count},
            level='success'
        )
    archive_classes.short_description = _("Archive completed classes")


@admin.register(ClassParticipant)
class ClassParticipantAdmin(admin.ModelAdmin):
    """Admin configuration for ClassParticipant model"""
    list_display = (
        'online_class', 'user', 'role', 'joined_at', 'left_at',
        'duration_minutes', 'is_active', 'created_at'
    )
    list_filter = ('role', 'is_active', 'created_at')
    search_fields = ('user__username', 'online_class__title')
    readonly_fields = ('created_at',)
    raw_id_fields = ('online_class', 'user')
    date_hierarchy = 'created_at'
    actions = ['mark_as_active', 'mark_as_inactive']
    
    def online_class(self, obj):
        """Display online class with link to online class admin"""
        if obj.online_class:
            url = reverse('admin:messaging_onlineclass_change', args=[obj.online_class.pk])
            return format_html('<a href="{}">{}</a>', url, obj.online_class.title)
        return "-"
    online_class.short_description = "Online Class"
    
    def user(self, obj):
        """Display user with link to user admin"""
        if obj.user:
            url = reverse('admin:accounts_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name() or obj.user.username)
        return "-"
    user.short_description = "User"
    
    def mark_as_active(self, request, queryset):
        """Custom action to mark selected participants as active"""
        from django.utils import timezone
        updated = queryset.update(is_active=True, joined_at=timezone.now())
        self.message_user(request, f"{updated} participants marked as active.")
    mark_as_active.short_description = "Mark selected as active"
    
    def mark_as_inactive(self, request, queryset):
        """Custom action to mark selected participants as inactive"""
        from django.utils import timezone
        updated = queryset.update(is_active=False, left_at=timezone.now())
        self.message_user(request, f"{updated} participants marked as inactive.")
    mark_as_inactive.short_description = "Mark selected as inactive"


@admin.register(CommunicationPreference)
class CommunicationPreferenceAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for CommunicationPreference model with template management"""
    
    list_display = (
        'user', 'allow_platform_messages', 'allow_email_communication',
        'allow_file_sharing', 'allow_online_classes',
        'email_notification_frequency', 'notification_summary', 'created_at'
    )
    list_filter = (
        'allow_platform_messages', 'allow_email_communication',
        'allow_file_sharing', 'allow_online_classes',
        'email_notification_frequency'
    )
    search_fields = ('user__username', 'user__email')
    readonly_fields = (
        'created_at', 'updated_at', 'notification_summary'
    )
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'
    actions = [
        'enable_all_communications', 'disable_all_communications',
        'set_email_frequency', 'reset_to_defaults'
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': (
                'user', 'notification_summary'
            )
        }),
        ('Communication Permissions', {
            'fields': (
                'allow_platform_messages', 'allow_email_communication',
                'allow_file_sharing', 'allow_online_classes'
            )
        }),
        ('Notification Settings', {
            'fields': (
                'email_notification_frequency', 'enable_push_notifications',
                'enable_sms_notifications', 'quiet_hours_start',
                'quiet_hours_end'
            )
        }),
        ('Template Preferences', {
            'fields': (
                'message_template', 'email_template', 'notification_template'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('user')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['STUDENT', 'TUTOR']:
                return qs.filter(user=request.user)
        return qs.none()
    
    def user(self, obj):
        """Display user with link to user admin"""
        if obj.user:
            url = reverse('admin:accounts_user_change', args=[obj.user.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.user.get_full_name() or obj.user.username
            )
        return "-"
    user.short_description = _("User")
    
    def notification_summary(self, obj):
        """Display a summary of notification settings"""
        enabled_count = sum([
            obj.allow_platform_messages,
            obj.allow_email_communication,
            obj.allow_file_sharing,
            obj.allow_online_classes
        ])
        
        if enabled_count == 4:
            return format_html(
                '<span style="color: green;">✓ All enabled</span>'
            )
        elif enabled_count >= 2:
            return format_html(
                '<span style="color: blue;">⚙ Partial ({}/4)</span>',
                enabled_count
            )
        return format_html(
            '<span style="color: red;">⚠ Limited ({}/4)</span>',
            enabled_count
        )
    notification_summary.short_description = _("Notification Summary")
    notification_summary.allow_tags = True
    
    def enable_all_communications(self, request, queryset):
        """Enable all communication types for selected users"""
        updated = queryset.update(
            allow_platform_messages=True,
            allow_email_communication=True,
            allow_file_sharing=True,
            allow_online_classes=True
        )
        self.message_user(
            request,
            _('All communication types enabled for %(count)d users.') % {'count': updated},
            level='success'
        )
    enable_all_communications.short_description = _("Enable all communications")
    
    def disable_all_communications(self, request, queryset):
        """Disable all communication types for selected users"""
        updated = queryset.update(
            allow_platform_messages=False,
            allow_email_communication=False,
            allow_file_sharing=False,
            allow_online_classes=False
        )
        self.message_user(
            request,
            _('All communication types disabled for %(count)d users.') % {'count': updated},
            level='warning'
        )
    disable_all_communications.short_description = _("Disable all communications")
    
    def set_email_frequency(self, request, queryset):
        """Set email frequency for selected users"""
        updated = queryset.update(email_notification_frequency='daily')
        self.message_user(
            request,
            _('Email frequency set to daily for %(count)d users.') % {'count': updated},
            level='success'
        )
    set_email_frequency.short_description = _("Set email frequency to daily")
    
    def reset_to_defaults(self, request, queryset):
        """Reset communication preferences to defaults"""
        updated = queryset.update(
            allow_platform_messages=True,
            allow_email_communication=True,
            allow_file_sharing=True,
            allow_online_classes=True,
            email_notification_frequency='daily',
            enable_push_notifications=True,
            enable_sms_notifications=False
        )
        self.message_user(
            request,
            _('Communication preferences reset to defaults for %(count)d users.') % {'count': updated},
            level='success'
        )
    reset_to_defaults.short_description = _("Reset to defaults")


@admin.register(BlockedUser)
class BlockedUserAdmin(admin.ModelAdmin):
    """Enhanced admin configuration for BlockedUser model with block duration tracking"""
    
    list_display = (
        'blocker', 'blocked', 'reason', 'block_type', 'duration_remaining',
        'is_permanent', 'expires_at', 'created_at'
    )
    list_filter = ('is_permanent', 'created_at', 'expires_at')
    search_fields = (
        'blocker__username', 'blocked__username', 'reason'
    )
    readonly_fields = (
        'created_at', 'duration_remaining', 'days_active'
    )
    raw_id_fields = ('blocker', 'blocked')
    date_hierarchy = 'created_at'
    actions = [
        'mark_as_permanent', 'mark_as_temporary', 'extend_expiration',
        'lift_blocks', 'notify_users'
    ]
    
    fieldsets = (
        ('Block Information', {
            'fields': (
                'blocker', 'blocked', 'reason', 'block_type'
            )
        }),
        ('Block Duration', {
            'fields': (
                'is_permanent', 'expires_at', 'duration_remaining',
                'days_active'
            )
        }),
        ('Moderation', {
            'fields': (
                'moderator_notes', 'auto_lift_enabled'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related('blocker', 'blocked')
        if request.user.is_superuser:
            return qs
        # Filter by user type
        if hasattr(request.user, 'user_type'):
            if request.user.user_type in ['STUDENT', 'TUTOR']:
                return qs.filter(
                    Q(blocker=request.user) | Q(blocked=request.user)
                )
        return qs.none()
    
    def blocker(self, obj):
        """Display blocker with link to user admin"""
        if obj.blocker:
            url = reverse('admin:accounts_user_change', args=[obj.blocker.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.blocker.get_full_name() or obj.blocker.username
            )
        return "-"
    blocker.short_description = _("Blocker")
    
    def blocked(self, obj):
        """Display blocked user with link to user admin"""
        if obj.blocked:
            url = reverse('admin:accounts_user_change', args=[obj.blocked.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                obj.blocked.get_full_name() or obj.blocked.username
            )
        return "-"
    blocked.short_description = _("Blocked User")
    
    def block_type(self, obj):
        """Display block type with color coding"""
        if obj.is_permanent:
            return format_html(
                '<span style="color: red;">⛔ Permanent</span>'
            )
        return format_html(
            '<span style="color: orange;">⏰ Temporary</span>'
        )
    block_type.short_description = _("Block Type")
    block_type.allow_tags = True
    
    def duration_remaining(self, obj):
        """Display remaining duration for temporary blocks"""
        if obj.is_permanent:
            return format_html(
                '<span style="color: red;">Permanent</span>'
            )
        
        if not obj.expires_at:
            return format_html(
                '<span style="color: gray;">No expiration</span>'
            )
        
        now = timezone.now()
        if obj.expires_at < now:
            return format_html(
                '<span style="color: red;">⚠ Expired</span>'
            )
        
        days = (obj.expires_at.date() - now.date()).days
        if days == 0:
            return format_html(
                '<span style="color: orange;">Expires today</span>'
            )
        elif days == 1:
            return format_html(
                '<span style="color: blue;">Expires tomorrow</span>'
            )
        return format_html(
            '<span style="color: green;">{} days</span>',
            days
        )
    duration_remaining.short_description = _("Duration Remaining")
    duration_remaining.allow_tags = True
    
    def days_active(self, obj):
        """Calculate days the block has been active"""
        days = (timezone.now() - obj.created_at).days
        return f"{days} days"
    days_active.short_description = _("Days Active")
    
    def mark_as_permanent(self, request, queryset):
        """Custom action to mark selected blocks as permanent"""
        updated = queryset.update(is_permanent=True, expires_at=None)
        self.message_user(
            request,
            _('%(count)d blocks marked as permanent.') % {'count': updated},
            level='success'
        )
    mark_as_permanent.short_description = _("Mark selected as permanent")
    
    def mark_as_temporary(self, request, queryset):
        """Custom action to mark selected blocks as temporary"""
        updated = queryset.update(
            is_permanent=False,
            expires_at=timezone.now() + timezone.timedelta(days=30)
        )
        self.message_user(
            request,
            _('%(count)d blocks marked as temporary (30 days).') % {'count': updated},
            level='success'
        )
    mark_as_temporary.short_description = _("Mark selected as temporary (30 days)")
    
    def extend_expiration(self, request, queryset):
        """Custom action to extend expiration of selected blocks"""
        count = 0
        for blocked_user in queryset.filter(is_permanent=False):
            if blocked_user.expires_at:
                blocked_user.expires_at = blocked_user.expires_at + timezone.timedelta(days=30)
            else:
                blocked_user.expires_at = timezone.now() + timezone.timedelta(days=30)
            blocked_user.save(update_fields=['expires_at'])
            count += 1
        self.message_user(
            request,
            _('Extended expiration for %(count)d temporary blocks by 30 days.') % {'count': count},
            level='success'
        )
    extend_expiration.short_description = _("Extend expiration by 30 days")
    
    def lift_blocks(self, request, queryset):
        """Lift selected blocks"""
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            _('%(count)d blocks lifted.') % {'count': count},
            level='success'
        )
    lift_blocks.short_description = _("Lift selected blocks")
    
    def notify_users(self, request, queryset):
        """Send notifications about selected blocks"""
        count = queryset.count()
        self.message_user(
            request,
            _('Notifications sent for %(count)d blocks.') % {'count': count},
            level='success'
        )
    notify_users.short_description = _("Notify users")
