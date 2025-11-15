import uuid
import json
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from django.db.models import Count, Q

User = get_user_model()

# Import managers at the end to avoid circular imports


class Notification(models.Model):
    """Main notification model for all platform notifications"""
    
    class Type(models.TextChoices):
        MESSAGE = 'MESSAGE', _('Message')
        PROPOSAL = 'PROPOSAL', _('Proposal')
        AWARD = 'AWARD', _('Award')
        SESSION = 'SESSION', _('Session')
        REVIEW = 'REVIEW', _('Review')
        PAYMENT = 'PAYMENT', _('Payment')
        SYSTEM = 'SYSTEM', _('System')
    
    class Priority(models.TextChoices):
        LOW = 'LOW', _('Low')
        MEDIUM = 'MEDIUM', _('Medium')
        HIGH = 'HIGH', _('High')
        URGENT = 'URGENT', _('Urgent')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_notifications',
        verbose_name=_('recipient')
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_notifications',
        verbose_name=_('sender')
    )
    title = models.CharField(_('title'), max_length=200)
    content = models.TextField(_('content'))
    notification_type = models.CharField(
        _('notification type'),
        max_length=20,
        choices=Type.choices,
        default=Type.SYSTEM
    )
    priority = models.CharField(
        _('priority'),
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    is_read = models.BooleanField(_('read status'), default=False)
    read_at = models.DateTimeField(_('read at'), null=True, blank=True)
    
    # Generic foreign key to link to related objects
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.UUIDField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Action URL for direct navigation
    action_url = models.URLField(_('action URL'), blank=True, null=True)
    action_text = models.CharField(_('action text'), max_length=50, blank=True, null=True)
    
    # Email notification tracking
    email_sent = models.BooleanField(_('email sent'), default=False)
    email_sent_at = models.DateTimeField(_('email sent at'), null=True, blank=True)
    
    # Push notification tracking
    push_sent = models.BooleanField(_('push notification sent'), default=False)
    push_sent_at = models.DateTimeField(_('push notification sent at'), null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    expires_at = models.DateTimeField(_('expires at'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        indexes = [
            models.Index(fields=['recipient_id']),
            models.Index(fields=['sender_id']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['is_read']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['recipient_id', 'is_read']),
            models.Index(fields=['recipient_id', 'created_at']),
            models.Index(fields=['notification_type', 'priority']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} → {self.recipient.get_full_name()}"
    
    def clean(self):
        """Validate the model data"""
        if self.expires_at and self.expires_at <= timezone.now():
            raise ValidationError(_('Expires at must be in the future'))
        
        if self.read_at and not self.is_read:
            raise ValidationError(_('Read at can only be set when notification is marked as read'))
        
        if self.action_url and not self.action_text:
            raise ValidationError(_('Action text is required when action URL is provided'))
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def mark_as_unread(self):
        """Mark notification as unread"""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            self.save(update_fields=['is_read', 'read_at'])
    
    def is_expired(self):
        """Check if notification has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def send_email_notification(self, force_send=False):
        """Send email notification to recipient"""
        if self.email_sent and not force_send:
            return False
        
        # Check user's email notification preferences
        try:
            preferences = NotificationPreference.objects.get(user=self.recipient)
            if not preferences.email_enabled:
                return False
            
            # Check if user wants this type of notification
            if not preferences.get_email_setting(self.notification_type):
                return False
            
            # Check quiet hours
            if preferences.is_in_quiet_hours() and self.priority != self.Priority.URGENT:
                return False
                
        except NotificationPreference.DoesNotExist:
            # If no preferences exist, use default (send email)
            pass
        
        try:
            # Get email template or use default
            try:
                template = NotificationTemplate.objects.get(
                    notification_type=self.notification_type,
                    is_default=True,
                    is_active=True
                )
                subject = template.render_subject(self)
                body = template.render_body(self)
            except NotificationTemplate.DoesNotExist:
                subject = self.title
                body = self.content
            
            # Send email
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.recipient.email],
                html_message=body if self.notification_type != self.Type.SYSTEM else None,
            )
            
            # Update email sent status
            self.email_sent = True
            self.email_sent_at = timezone.now()
            self.save(update_fields=['email_sent', 'email_sent_at'])
            
            return True
            
        except Exception as e:
            # Log error and create email queue entry for retry
            EmailQueue.objects.create(
                notification=self,
                recipient=self.recipient,
                subject=self.title,
                body=self.content,
                status=EmailQueue.Status.FAILED,
                error_message=str(e)
            )
            return False
    
    def send_push_notification(self, force_send=False):
        """Send push notification to recipient"""
        if self.push_sent and not force_send:
            return False
        
        # Check user's push notification preferences
        try:
            preferences = NotificationPreference.objects.get(user=self.recipient)
            if not preferences.push_enabled:
                return False
            
            # Check if user wants this type of notification
            if not preferences.get_push_setting(self.notification_type):
                return False
            
            # Check quiet hours
            if preferences.is_in_quiet_hours() and self.priority != self.Priority.URGENT:
                return False
                
        except NotificationPreference.DoesNotExist:
            # If no preferences exist, use default (send push)
            pass
        
        try:
            # Here you would integrate with push notification service
            # For now, we'll just mark as sent
            self.push_sent = True
            self.push_sent_at = timezone.now()
            self.save(update_fields=['push_sent', 'push_sent_at'])
            
            return True
            
        except Exception as e:
            # Log error
            return False
    
    def get_absolute_url(self):
        """Get URL for notification detail"""
        return reverse('notifications:detail', kwargs={'pk': self.pk})


class NotificationPreference(models.Model):
    """User preferences for different notification types"""
    
    class EmailFrequency(models.TextChoices):
        IMMEDIATE = 'IMMEDIATE', _('Immediate')
        HOURLY = 'HOURLY', _('Hourly')
        DAILY = 'DAILY', _('Daily')
        WEEKLY = 'WEEKLY', _('Weekly')
        NEVER = 'NEVER', _('Never')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name=_('user')
    )
    
    # General notification settings
    email_enabled = models.BooleanField(_('email notifications enabled'), default=True)
    push_enabled = models.BooleanField(_('push notifications enabled'), default=True)
    in_app_enabled = models.BooleanField(_('in-app notifications enabled'), default=True)
    
    # Email notification settings by type
    email_message = models.BooleanField(_('email for messages'), default=True)
    email_proposal = models.BooleanField(_('email for proposals'), default=True)
    email_award = models.BooleanField(_('email for awards'), default=True)
    email_session = models.BooleanField(_('email for sessions'), default=True)
    email_review = models.BooleanField(_('email for reviews'), default=True)
    email_payment = models.BooleanField(_('email for payments'), default=True)
    email_system = models.BooleanField(_('email for system updates'), default=True)
    
    # Push notification settings by type
    push_message = models.BooleanField(_('push for messages'), default=True)
    push_proposal = models.BooleanField(_('push for proposals'), default=True)
    push_award = models.BooleanField(_('push for awards'), default=True)
    push_session = models.BooleanField(_('push for sessions'), default=True)
    push_review = models.BooleanField(_('push for reviews'), default=True)
    push_payment = models.BooleanField(_('push for payments'), default=True)
    push_system = models.BooleanField(_('push for system updates'), default=False)
    
    # In-app notification settings by type
    in_app_message = models.BooleanField(_('in-app for messages'), default=True)
    in_app_proposal = models.BooleanField(_('in-app for proposals'), default=True)
    in_app_award = models.BooleanField(_('in-app for awards'), default=True)
    in_app_session = models.BooleanField(_('in-app for sessions'), default=True)
    in_app_review = models.BooleanField(_('in-app for reviews'), default=True)
    in_app_payment = models.BooleanField(_('in-app for payments'), default=True)
    in_app_system = models.BooleanField(_('in-app for system updates'), default=True)
    
    # Email frequency settings
    email_frequency = models.CharField(
        _('email frequency'),
        max_length=20,
        choices=EmailFrequency.choices,
        default=EmailFrequency.IMMEDIATE
    )
    
    # Quiet hours configuration
    quiet_hours_enabled = models.BooleanField(_('quiet hours enabled'), default=False)
    quiet_hours_start = models.TimeField(_('quiet hours start'), null=True, blank=True)
    quiet_hours_end = models.TimeField(_('quiet hours end'), null=True, blank=True)
    quiet_hours_timezone = models.CharField(_('quiet hours timezone'), max_length=50, default='UTC')
    
    # Additional settings
    auto_delete_read = models.BooleanField(_('auto-delete read notifications'), default=False)
    auto_delete_days = models.PositiveIntegerField(
        _('auto-delete after days'),
        default=30,
        help_text=_('Number of days after which read notifications are automatically deleted')
    )
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['email_frequency']),
        ]
    
    def __str__(self):
        return f"Notification preferences for {self.user.get_full_name()}"
    
    def clean(self):
        """Validate the model data"""
        if self.quiet_hours_enabled:
            if not self.quiet_hours_start or not self.quiet_hours_end:
                raise ValidationError(_('Both quiet hours start and end must be set when quiet hours are enabled'))
        
        if self.auto_delete_read and self.auto_delete_days <= 0:
            raise ValidationError(_('Auto-delete days must be positive when auto-delete is enabled'))
    
    def get_email_setting(self, notification_type):
        """Get email setting for specific notification type"""
        type_map = {
            Notification.Type.MESSAGE: self.email_message,
            Notification.Type.PROPOSAL: self.email_proposal,
            Notification.Type.AWARD: self.email_award,
            Notification.Type.SESSION: self.email_session,
            Notification.Type.REVIEW: self.email_review,
            Notification.Type.PAYMENT: self.email_payment,
            Notification.Type.SYSTEM: self.email_system,
        }
        return type_map.get(notification_type, False)
    
    def get_push_setting(self, notification_type):
        """Get push setting for specific notification type"""
        type_map = {
            Notification.Type.MESSAGE: self.push_message,
            Notification.Type.PROPOSAL: self.push_proposal,
            Notification.Type.AWARD: self.push_award,
            Notification.Type.SESSION: self.push_session,
            Notification.Type.REVIEW: self.push_review,
            Notification.Type.PAYMENT: self.push_payment,
            Notification.Type.SYSTEM: self.push_system,
        }
        return type_map.get(notification_type, False)
    
    def get_in_app_setting(self, notification_type):
        """Get in-app setting for specific notification type"""
        type_map = {
            Notification.Type.MESSAGE: self.in_app_message,
            Notification.Type.PROPOSAL: self.in_app_proposal,
            Notification.Type.AWARD: self.in_app_award,
            Notification.Type.SESSION: self.in_app_session,
            Notification.Type.REVIEW: self.in_app_review,
            Notification.Type.PAYMENT: self.in_app_payment,
            Notification.Type.SYSTEM: self.in_app_system,
        }
        return type_map.get(notification_type, False)
    
    def is_in_quiet_hours(self):
        """Check if current time is within quiet hours"""
        if not self.quiet_hours_enabled:
            return False
        
        try:
            from django.utils import timezone as django_tz
            import pytz
            
            user_tz = pytz.timezone(self.quiet_hours_timezone)
            current_time = django_tz.now().astimezone(user_tz).time()
            
            # Ensure we have both start and end times
            if not self.quiet_hours_start or not self.quiet_hours_end:
                return False
                
            if self.quiet_hours_start <= self.quiet_hours_end:
                # Normal case (e.g., 22:00 to 08:00)
                return self.quiet_hours_start <= current_time <= self.quiet_hours_end
            else:
                # Overnight case (e.g., 22:00 to 08:00 next day)
                return current_time >= self.quiet_hours_start or current_time <= self.quiet_hours_end
                
        except Exception:
            # If timezone conversion fails, assume not in quiet hours
            return False


class NotificationTemplate(models.Model):
    """Templates for different notification types"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=100, unique=True)
    notification_type = models.CharField(
        _('notification type'),
        max_length=20,
        choices=Notification.Type.choices
    )
    subject_template = models.CharField(
        _('subject template'),
        max_length=200,
        help_text=_('Template for email subject. Use {{ variable }} for placeholders.')
    )
    body_template = models.TextField(
        _('body template'),
        help_text=_('Template for email body. Use {{ variable }} for placeholders.')
    )
    html_template = models.TextField(
        _('HTML template'),
        blank=True,
        null=True,
        help_text=_('HTML version of email body. Use {{ variable }} for placeholders.')
    )
    is_default = models.BooleanField(_('is default'), default=False)
    is_active = models.BooleanField(_('is active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        indexes = [
            models.Index(fields=['notification_type']),
            models.Index(fields=['is_default']),
            models.Index(fields=['is_active']),
        ]
        unique_together = ['notification_type', 'is_default']
    
    def __str__(self):
        return f"{self.name} ({self.notification_type})"
    
    def render_subject(self, notification):
        """Render subject template with notification data"""
        context = self._get_template_context(notification)
        return self.subject_template.format(**context)
    
    def render_body(self, notification):
        """Render body template with notification data"""
        context = self._get_template_context(notification)
        return self.body_template.format(**context)
    
    def render_html(self, notification):
        """Render HTML template with notification data"""
        if not self.html_template:
            return None
        
        context = self._get_template_context(notification)
        return self.html_template.format(**context)
    
    def _get_template_context(self, notification):
        """Get context dictionary for template rendering"""
        context = {
            'title': notification.title,
            'content': notification.content,
            'recipient_name': notification.recipient.get_full_name(),
            'recipient_username': notification.recipient.username,
            'sender_name': notification.sender.get_full_name() if notification.sender else 'System',
            'sender_username': notification.sender.username if notification.sender else 'System',
            'notification_type': notification.get_notification_type_display(),
            'priority': notification.get_priority_display(),
            'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'action_url': notification.action_url,
            'action_text': notification.action_text,
        }
        
        # Add related object context if available
        if notification.related_object:
            context['related_object'] = notification.related_object
            context['related_object_type'] = notification.content_type.name
            
            # Add specific object fields based on type
            if hasattr(notification.related_object, 'title'):
                context['related_object_title'] = notification.related_object.title
            if hasattr(notification.related_object, 'description'):
                context['related_object_description'] = notification.related_object.description
        
        return context


class EmailQueue(models.Model):
    """Queue for sending email notifications"""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING = 'PROCESSING', _('Processing')
        SENT = 'SENT', _('Sent')
        FAILED = 'FAILED', _('Failed')
        CANCELLED = 'CANCELLED', _('Cancelled')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='email_queue_entries',
        null=True,
        blank=True
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_queue_entries',
        verbose_name=_('recipient')
    )
    subject = models.CharField(_('subject'), max_length=200)
    body = models.TextField(_('body'))
    html_body = models.TextField(_('HTML body'), blank=True, null=True)
    from_email = models.EmailField(
        _('from email'),
        default=settings.DEFAULT_FROM_EMAIL
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    retry_count = models.PositiveIntegerField(_('retry count'), default=0)
    max_retries = models.PositiveIntegerField(_('max retries'), default=3)
    last_retry_at = models.DateTimeField(_('last retry at'), null=True, blank=True)
    next_retry_at = models.DateTimeField(_('next retry at'), null=True, blank=True)
    error_message = models.TextField(_('error message'), blank=True, null=True)
    sent_at = models.DateTimeField(_('sent at'), null=True, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Email Queue')
        verbose_name_plural = _('Email Queues')
        indexes = [
            models.Index(fields=['recipient_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['next_retry_at']),
            models.Index(fields=['status', 'next_retry_at']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['created_at']
    
    def __str__(self):
        return f"Email to {self.recipient.get_full_name()}: {self.subject}"
    
    def clean(self):
        """Validate the model data"""
        if self.retry_count > self.max_retries:
            raise ValidationError(_('Retry count cannot exceed max retries'))
        
        if self.status == self.Status.SENT and not self.sent_at:
            raise ValidationError(_('Sent at must be set when status is sent'))
    
    def can_retry(self):
        """Check if email can be retried"""
        return (
            self.status in [self.Status.FAILED, self.Status.CANCELLED] and
            self.retry_count < self.max_retries and
            (not self.next_retry_at or self.next_retry_at <= timezone.now())
        )
    
    def increment_retry(self):
        """Increment retry count and schedule next retry"""
        self.retry_count += 1
        self.last_retry_at = timezone.now()
        
        # Calculate exponential backoff for next retry (1h, 2h, 4h, etc.)
        import math
        delay_hours = math.pow(2, self.retry_count - 1)
        self.next_retry_at = timezone.now() + timezone.timedelta(hours=delay_hours)
        
        self.status = self.Status.PENDING
        self.save(update_fields=['retry_count', 'last_retry_at', 'next_retry_at', 'status'])
    
    def mark_as_sent(self):
        """Mark email as sent"""
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_failed(self, error_message):
        """Mark email as failed"""
        self.status = self.Status.FAILED
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])
    
    def send(self):
        """Attempt to send the email"""
        if self.status != self.Status.PENDING:
            return False


class NotificationType(models.Model):
    """Define types of notifications"""
    
    class Category(models.TextChoices):
        REQUIREMENT = 'REQUIREMENT', _('Requirement')
        PROPOSAL = 'PROPOSAL', _('Proposal')
        AWARD = 'AWARD', _('Award')
        PAYMENT = 'PAYMENT', _('Payment')
        MESSAGE = 'MESSAGE', _('Message')
        SYSTEM = 'SYSTEM', _('System')
        ADMIN = 'ADMIN', _('Admin')
    
    class Priority(models.TextChoices):
        LOW = 'LOW', _('Low')
        NORMAL = 'NORMAL', _('Normal')
        HIGH = 'HIGH', _('High')
        URGENT = 'URGENT', _('Urgent')
    
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(_('name'), max_length=100, unique=True)
    code = models.CharField(_('code'), max_length=50, unique=True, help_text=_('Machine-readable code'))
    category = models.CharField(_('category'), max_length=20, choices=Category.choices)
    description = models.TextField(_('description'), blank=True, null=True)
    default_template = models.TextField(_('default template'))
    email_template = models.TextField(_('email template'), blank=True, null=True)
    sms_template = models.TextField(_('SMS template'), blank=True, null=True)
    push_template = models.TextField(_('push template'), blank=True, null=True)
    is_active = models.BooleanField(_('is active'), default=True)
    is_system = models.BooleanField(_('is system'), default=False, help_text=_('System-generated notifications'))
    priority = models.CharField(_('priority'), max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    default_expiration_hours = models.PositiveIntegerField(_('default expiration hours'), default=720)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Notification Type')
        verbose_name_plural = _('Notification Types')
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['category']),
            models.Index(fields=['is_active']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_template(self, channel):
        """Get template for specific channel"""
        if channel == 'email' and self.email_template:
            return self.email_template
        elif channel == 'sms' and self.sms_template:
            return self.sms_template
        elif channel == 'push' and self.push_template:
            return self.push_template
        return self.default_template
    
    def render_template(self, context):
        """Render template with context"""
        template = self.default_template
        for key, value in context.items():
            template = template.replace(f'{{{{{key}}}}}', str(value))
        return template


class NotificationDelivery(models.Model):
    """Track delivery status of notifications"""
    
    class Channel(models.TextChoices):
        IN_APP = 'IN_APP', _('In-App')
        EMAIL = 'EMAIL', _('Email')
        SMS = 'SMS', _('SMS')
        PUSH = 'PUSH', _('Push')
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        SENT = 'SENT', _('Sent')
        DELIVERED = 'DELIVERED', _('Delivered')
        FAILED = 'FAILED', _('Failed')
        BOUNCED = 'BOUNCED', _('Bounced')
    
    id = models.BigAutoField(primary_key=True)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='deliveries'
    )
    channel = models.CharField(_('channel'), max_length=10, choices=Channel.choices)
    status = models.CharField(_('status'), max_length=20, choices=Status.choices, default=Status.PENDING)
    recipient_address = models.CharField(_('recipient address'), max_length=255)
    sent_at = models.DateTimeField(_('sent at'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('delivered at'), null=True, blank=True)
    failed_at = models.DateTimeField(_('failed at'), null=True, blank=True)
    failure_reason = models.TextField(_('failure reason'), blank=True, null=True)
    delivery_provider = models.CharField(_('delivery provider'), max_length=50, blank=True, null=True)
    provider_response = models.JSONField(_('provider response'), default=dict)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Notification Delivery')
        verbose_name_plural = _('Notification Deliveries')
        indexes = [
            models.Index(fields=['notification_id']),
            models.Index(fields=['channel']),
            models.Index(fields=['status']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['notification_id', 'channel']),
            models.Index(fields=['channel', 'status']),
        ]
    
    def __str__(self):
        return f"{self.notification.title} - {self.channel} - {self.status}"
    
    def mark_as_sent(self):
        """Mark delivery as sent"""
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_delivered(self):
        """Mark delivery as delivered"""
        self.status = self.Status.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_as_failed(self, reason):
        """Mark delivery as failed"""
        self.status = self.Status.FAILED
        self.failed_at = timezone.now()
        self.failure_reason = reason
        self.save(update_fields=['status', 'failed_at', 'failure_reason'])


class NotificationDigest(models.Model):
    """Digest notifications for batch sending"""
    
    class Frequency(models.TextChoices):
        HOURLY = 'HOURLY', _('Hourly')
        DAILY = 'DAILY', _('Daily')
        WEEKLY = 'WEEKLY', _('Weekly')
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_digests'
    )
    frequency = models.CharField(_('frequency'), max_length=10, choices=Frequency.choices)
    notifications = models.ManyToManyField(
        Notification,
        related_name='digests'
    )
    subject = models.CharField(_('subject'), max_length=255)
    content = models.TextField(_('content'))
    is_sent = models.BooleanField(_('is sent'), default=False)
    sent_at = models.DateTimeField(_('sent at'), null=True, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Notification Digest')
        verbose_name_plural = _('Notification Digests')
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['frequency']),
            models.Index(fields=['is_sent']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.frequency} digest"
    
    def add_notification(self, notification):
        """Add notification to digest"""
        self.notifications.add(notification)
    
    def generate_content(self):
        """Generate digest content"""
        notifications = self.notifications.all().order_by('-created_at')
        content_lines = [f"<h3>{self.subject}</h3>"]
        
        for notification in notifications:
            content_lines.append(f"""
                <div style="margin-bottom: 20px; padding: 10px; border-left: 3px solid #007bff;">
                    <h4>{notification.title}</h4>
                    <p>{notification.content}</p>
                    <small>Sent: {notification.created_at.strftime('%Y-%m-%d %H:%M')}</small>
                </div>
            """)
        
        self.content = ''.join(content_lines)
        self.save(update_fields=['content'])
        return self.content
    
    def send_digest(self):
        """Send digest email"""
        try:
            send_mail(
                subject=self.subject,
                message="",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.user.email],
                html_message=self.content,
                fail_silently=False,
            )
            
            self.is_sent = True
            self.sent_at = timezone.now()
            self.save(update_fields=['is_sent', 'sent_at'])
            
            return True
        except Exception as e:
            return False


class PushDevice(models.Model):
    """User push notification devices"""
    
    class DeviceType(models.TextChoices):
        IOS = 'IOS', _('iOS')
        ANDROID = 'ANDROID', _('Android')
        WEB = 'WEB', _('Web')
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='push_devices'
    )
    device_token = models.CharField(_('device token'), max_length=255)
    device_type = models.CharField(_('device type'), max_length=10, choices=DeviceType.choices)
    device_id = models.CharField(_('device ID'), max_length=255, blank=True, null=True)
    app_version = models.CharField(_('app version'), max_length=50, blank=True, null=True)
    os_version = models.CharField(_('OS version'), max_length=50, blank=True, null=True)
    is_active = models.BooleanField(_('is active'), default=True)
    last_used_at = models.DateTimeField(_('last used at'), null=True, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Push Device')
        verbose_name_plural = _('Push Devices')
        unique_together = ['user', 'device_token']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['device_token']),
            models.Index(fields=['device_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['user_id', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.device_type}"


class PushDeviceManager(models.Manager):
    """Custom manager for PushDevice model"""
    
    def get_active_devices_for_user(self, user):
        """Get all active devices for a user"""
        return self.filter(
            user=user,
            is_active=True
        ).order_by('-last_used_at')


class PushMessage(models.Model):
    """Push notification messages"""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        SENT = 'SENT', _('Sent')
        DELIVERED = 'DELIVERED', _('Delivered')
        FAILED = 'FAILED', _('Failed')
    
    id = models.BigAutoField(primary_key=True)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='push_messages'
    )
    device = models.ForeignKey(
        PushDevice,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    title = models.CharField(_('title'), max_length=255)
    body = models.TextField(_('body'))
    icon = models.URLField(_('icon'), blank=True, null=True)
    image = models.URLField(_('image'), blank=True, null=True)
    sound = models.CharField(_('sound'), max_length=100, default='default')
    badge = models.PositiveIntegerField(_('badge'), null=True, blank=True)
    data = models.JSONField(_('data'), default=dict)
    status = models.CharField(_('status'), max_length=20, choices=Status.choices, default=Status.PENDING)
    sent_at = models.DateTimeField(_('sent at'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('delivered at'), null=True, blank=True)
    failed_at = models.DateTimeField(_('failed at'), null=True, blank=True)
    failure_reason = models.TextField(_('failure reason'), blank=True, null=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Push Message')
        verbose_name_plural = _('Push Messages')
        indexes = [
            models.Index(fields=['notification_id']),
            models.Index(fields=['device_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['notification_id', 'device_id']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.device.device_type}"


class SystemNotification(models.Model):
    """System-wide notifications"""
    
    class Type(models.TextChoices):
        MAINTENANCE = 'MAINTENANCE', _('Maintenance')
        ANNOUNCEMENT = 'ANNOUNCEMENT', _('Announcement')
        WARNING = 'WARNING', _('Warning')
        INFO = 'INFO', _('Info')
    
    class Priority(models.TextChoices):
        LOW = 'LOW', _('Low')
        NORMAL = 'NORMAL', _('Normal')
        HIGH = 'HIGH', _('High')
        URGENT = 'URGENT', _('Urgent')
    
    class TargetAudience(models.TextChoices):
        ALL = 'ALL', _('All')
        STUDENTS = 'STUDENTS', _('Students')
        TUTORS = 'TUTORS', _('Tutors')
        ADMINS = 'ADMINS', _('Admins')
    
    id = models.BigAutoField(primary_key=True)
    title = models.CharField(_('title'), max_length=255)
    message = models.TextField(_('message'))
    notification_type = models.CharField(_('notification type'), max_length=20, choices=Type.choices)
    priority = models.CharField(_('priority'), max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    is_active = models.BooleanField(_('is active'), default=True)
    start_time = models.DateTimeField(_('start time'))
    end_time = models.DateTimeField(_('end time'), null=True, blank=True)
    target_audience = models.CharField(_('target audience'), max_length=10, choices=TargetAudience.choices, default=TargetAudience.ALL)
    action_url = models.URLField(_('action URL'), blank=True, null=True)
    action_text = models.CharField(_('action text'), max_length=100, blank=True, null=True)
    is_dismissible = models.BooleanField(_('is dismissible'), default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_system_notifications'
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('System Notification')
        verbose_name_plural = _('System Notifications')
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['start_time']),
            models.Index(fields=['end_time']),
            models.Index(fields=['target_audience']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return self.title
    
    def is_currently_active(self):
        """Check if notification is currently active"""
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.start_time:
            return False
        if self.end_time and now > self.end_time:
            return False
        return True
    
    def should_show_to_user(self, user):
        """Check if notification should show to user"""
        if not self.is_currently_active():
            return False
        
        if self.target_audience == self.TargetAudience.ALL:
            return True
        elif self.target_audience == self.TargetAudience.STUDENTS:
            return hasattr(user, 'user_type') and user.user_type == 'STUDENT'
        elif self.target_audience == self.TargetAudience.TUTORS:
            return hasattr(user, 'user_type') and user.user_type == 'TUTOR'
        elif self.target_audience == self.TargetAudience.ADMINS:
            return user.is_staff or user.is_superuser
        
        return False


class SystemNotificationDismissal(models.Model):
    """Track system notification dismissals"""
    
    id = models.BigAutoField(primary_key=True)
    system_notification = models.ForeignKey(
        SystemNotification,
        on_delete=models.CASCADE,
        related_name='dismissals'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dismissed_system_notifications'
    )
    dismissed_at = models.DateTimeField(_('dismissed at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('System Notification Dismissal')
        verbose_name_plural = _('System Notification Dismissals')
        unique_together = ['system_notification', 'user']
        indexes = [
            models.Index(fields=['system_notification_id']),
            models.Index(fields=['user_id']),
            models.Index(fields=['dismissed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} dismissed {self.system_notification.title}"


class NotificationAnalytics(models.Model):
    """Daily notification statistics"""
    
    id = models.BigAutoField(primary_key=True)
    date = models.DateField(_('date'))
    notification_type = models.ForeignKey(
        NotificationType,
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    total_sent = models.PositiveIntegerField(_('total sent'), default=0)
    email_sent = models.PositiveIntegerField(_('email sent'), default=0)
    sms_sent = models.PositiveIntegerField(_('SMS sent'), default=0)
    push_sent = models.PositiveIntegerField(_('push sent'), default=0)
    total_delivered = models.PositiveIntegerField(_('total delivered'), default=0)
    email_delivered = models.PositiveIntegerField(_('email delivered'), default=0)
    sms_delivered = models.PositiveIntegerField(_('SMS delivered'), default=0)
    push_delivered = models.PositiveIntegerField(_('push delivered'), default=0)
    total_read = models.PositiveIntegerField(_('total read'), default=0)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Notification Analytics')
        verbose_name_plural = _('Notification Analytics')
        unique_together = ['date', 'notification_type']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['notification_type_id']),
            models.Index(fields=['date', 'notification_type_id']),
        ]
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.date} - {self.notification_type.name}"


# Import managers at the end to avoid circular imports
from .managers import NotificationManager, EmailQueueManager, PushNotificationManager

# Assign custom managers to models
Notification.add_to_class('objects', NotificationManager())
EmailQueue.add_to_class('objects', EmailQueueManager())
PushMessage.add_to_class('objects', PushNotificationManager())
PushDevice.add_to_class('objects', PushDeviceManager())
