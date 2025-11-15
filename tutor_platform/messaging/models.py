import uuid
import re
import secrets
import hashlib
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.validators import RegexValidator
from django.urls import reverse

from requirements.models import Award, Session

User = get_user_model()


def message_attachment_path(instance, filename):
    """Generate path for message attachment files"""
    return f"message_attachments/{instance.message.conversation.id}/{filename}"


def email_attachment_path(instance, filename):
    """Generate path for email attachment files"""
    return f"email_attachments/{instance.email_log.id}/{filename}"


def shared_file_path(instance, filename):
    """Generate path for shared files"""
    return f"shared_files/{instance.uploaded_by.id}/{filename}"


# Masked Email Communication Models

class MaskedEmail(models.Model):
    """Core model for privacy-focused email communication"""
    
    id = models.BigAutoField(primary_key=True)
    award = models.ForeignKey(
        Award,
        on_delete=models.CASCADE,
        related_name='masked_emails'
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='masked_emails_sent',
        limit_choices_to={'user_type': 'STUDENT'}
    )
    tutor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='masked_emails_received',
        limit_choices_to={'user_type': 'TUTOR'}
    )
    masked_address = models.EmailField(unique=True)
    student_real_email = models.EmailField()
    tutor_real_email = models.EmailField()
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = 'Masked Email'
        verbose_name_plural = 'Masked Emails'
        unique_together = ['award', 'student', 'tutor']
        indexes = [
            models.Index(fields=['award_id']),
            models.Index(fields=['student_id']),
            models.Index(fields=['tutor_id']),
            models.Index(fields=['masked_address']),
            models.Index(fields=['is_active']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['is_active', 'expires_at']),
        ]
    
    def __str__(self):
        return f"{self.masked_address} ({self.student.username} → {self.tutor.username})"
    
    def clean(self):
        """Validate the model data"""
        if self.expires_at <= timezone.now():
            raise ValidationError('Expires at must be in the future')
        
        if self.student == self.tutor:
            raise ValidationError('Student and tutor must be different users')
    
    def is_expired(self):
        """Check if masked email has expired"""
        return timezone.now() > self.expires_at
    
    def generate_masked_address(self):
        """Generate unique masked email"""
        # Create a unique hash based on award, student, tutor, and timestamp
        hash_input = f"{self.award.pk}-{self.student.pk}-{self.tutor.pk}-{timezone.now().timestamp()}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        
        # Generate masked email address
        domain = "masked.tutorplatform.com"  # This should be configurable in settings
        masked_address = f"msg-{hash_value}@{domain}"
        
        # Ensure uniqueness
        while MaskedEmail.objects.filter(masked_address=masked_address).exists():
            hash_value = hashlib.sha256(f"{hash_input}-{secrets.token_hex(4)}".encode()).hexdigest()[:16]
            masked_address = f"msg-{hash_value}@{domain}"
        
        self.masked_address = masked_address
        return masked_address
    
    def increment_usage(self):
        """Increment usage counter and update last_used_at"""
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])
    
    def save(self, *args, **kwargs):
        # Generate masked address if not provided
        if not self.masked_address:
            self.generate_masked_address()
        
        # Set default expiration if not provided (30 days from creation)
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        
        super().save(*args, **kwargs)


class EmailLog(models.Model):
    """Log all emails sent through masked addresses"""
    
    class Direction(models.TextChoices):
        STUDENT_TO_TUTOR = 'STUDENT_TO_TUTOR', 'Student to Tutor'
        TUTOR_TO_STUDENT = 'TUTOR_TO_STUDENT', 'Tutor to Student'
    
    id = models.BigAutoField(primary_key=True)
    masked_email = models.ForeignKey(
        MaskedEmail,
        on_delete=models.CASCADE,
        related_name='emails'
    )
    from_address = models.EmailField()
    to_address = models.EmailField()
    subject = models.CharField(max_length=255)
    body = models.TextField()
    direction = models.CharField(
        max_length=20,
        choices=Direction.choices
    )
    message_id = models.CharField(max_length=255, unique=True)
    in_reply_to = models.CharField(max_length=255, null=True, blank=True)
    attachments_count = models.PositiveIntegerField(default=0)
    size_bytes = models.PositiveIntegerField(default=0)
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'
        indexes = [
            models.Index(fields=['masked_email_id']),
            models.Index(fields=['from_address']),
            models.Index(fields=['to_address']),
            models.Index(fields=['direction']),
            models.Index(fields=['created_at']),
            models.Index(fields=['message_id']),
            models.Index(fields=['masked_email_id', 'created_at']),
        ]
    
    def __str__(self):
        return f"Email: {self.from_address} → {self.to_address} ({self.created_at})"
    
    def get_thread_id(self):
        """Extract thread ID for email threading"""
        # Use message_id or in_reply_to for threading
        return self.message_id.split('@')[0] if '@' in self.message_id else self.message_id
    
    def has_attachments(self):
        """Check if email has attachments"""
        return self.attachments_count > 0


class EmailAttachment(models.Model):
    """Store attachments for emails sent through masked addresses"""
    
    id = models.BigAutoField(primary_key=True)
    email_log = models.ForeignKey(
        EmailLog,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    is_scanned = models.BooleanField(default=False)
    scan_result = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Email Attachment'
        verbose_name_plural = 'Email Attachments'
    
    def __str__(self):
        return f"{self.filename} attached to {self.email_log}"


# Platform Messaging Models

class Conversation(models.Model):
    """Platform-based messaging between users"""
    
    id = models.BigAutoField(primary_key=True)
    award = models.ForeignKey(
        Award,
        on_delete=models.CASCADE,
        related_name='conversations',
        null=True,
        blank=True
    )
    participant1 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations_started'
    )
    participant2 = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='conversations_joined'
    )
    subject = models.CharField(max_length=200, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    participant1_last_read = models.DateTimeField(null=True, blank=True)
    participant2_last_read = models.DateTimeField(null=True, blank=True)
    participant1_deleted = models.BooleanField(default=False)
    participant2_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        indexes = [
            models.Index(fields=['award_id']),
            models.Index(fields=['participant1_id']),
            models.Index(fields=['participant2_id']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_message_at']),
            models.Index(fields=['participant1_id', 'is_active']),
            models.Index(fields=['participant2_id', 'is_active']),
        ]
    
    def __str__(self):
        return f"Conversation: {self.participant1.username} ↔ {self.participant2.username}"
    
    def clean(self):
        """Validate the model data"""
        if self.participant1 == self.participant2:
            raise ValidationError('Participants must be different users')
    
    def get_other_participant(self, user):
        """Return the other participant in conversation"""
        if user == self.participant1:
            return self.participant2
        elif user == self.participant2:
            return self.participant1
        return None
    
    def get_unread_count(self, user):
        """Count unread messages for user"""
        if user == self.participant1:
            last_read = self.participant1_last_read
        elif user == self.participant2:
            last_read = self.participant2_last_read
        else:
            return 0
        
        if not last_read:
            return self.messages.all().count()
        
        return self.messages.filter(created_at__gt=last_read).count()
    
    def mark_as_read(self, user):
        """Mark conversation as read for user"""
        now = timezone.now()
        if user == self.participant1:
            self.participant1_last_read = now
        elif user == self.participant2:
            self.participant2_last_read = now
        self.save(update_fields=['participant1_last_read', 'participant2_last_read'])
    
    def can_participant_access(self, user):
        """Check if user can access conversation"""
        return user in [self.participant1, self.participant2] and self.is_active


class Message(models.Model):
    """Individual messages in conversations"""
    
    class MessageType(models.TextChoices):
        TEXT = 'TEXT', 'Text'
        FILE = 'FILE', 'File'
        SYSTEM = 'SYSTEM', 'System'
        NOTIFICATION = 'NOTIFICATION', 'Notification'
    
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    message_type = models.CharField(
        max_length=20,
        choices=MessageType.choices,
        default=MessageType.TEXT
    )
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    parent_message = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='replies',
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        indexes = [
            models.Index(fields=['conversation_id']),
            models.Index(fields=['sender_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_read']),
            models.Index(fields=['parent_message_id']),
            models.Index(fields=['conversation_id', 'created_at']),
        ]
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.username} in {self.conversation}"
    
    def clean(self):
        """Validate the model data"""
        # Sender must be one of the conversation participants
        if self.sender not in [self.conversation.participant1, self.conversation.participant2]:
            raise ValidationError('Sender must be a participant in the conversation')
        
        # Parent message must belong to same conversation
        if self.parent_message and self.parent_message.conversation != self.conversation:
            raise ValidationError('Parent message must belong to the same conversation')
        
        # Content cannot be empty for text messages
        if self.message_type == self.MessageType.TEXT and not self.content.strip():
            raise ValidationError('Text messages cannot have empty content')
    
    def can_edit(self):
        """Check if message can be edited"""
        # Can edit if not deleted, is text message, and created within last 15 minutes
        if self.is_deleted or self.message_type != self.MessageType.TEXT:
            return False
        
        time_diff = timezone.now() - self.created_at
        return time_diff.total_seconds() < 900  # 15 minutes
    
    def can_delete(self):
        """Check if message can be deleted"""
        # Can delete if not already deleted
        return not self.is_deleted
    
    def get_thread(self):
        """Get message thread (replies)"""
        return self.replies.all().order_by('created_at')
    
    def save(self, *args, **kwargs):
        # Update conversation's last_message_at when saving a new message
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            self.conversation.last_message_at = self.created_at
            self.conversation.save(update_fields=['last_message_at'])
    
    def contains_contact_info(self):
        """Check if message contains personal contact information"""
        # Phone number patterns
        phone_patterns = [
            r'\b\d{10}\b',  # 10-digit numbers
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # US format
            r'\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # International
        ]
        
        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Check for phone numbers
        for pattern in phone_patterns:
            if re.search(pattern, self.content):
                return True
        
        # Check for email addresses
        if re.search(email_pattern, self.content):
            return True
        
        return False


class MessageAttachment(models.Model):
    """Attachments for platform messages"""
    
    id = models.BigAutoField(primary_key=True)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to=message_attachment_path)
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    thumbnail = models.ImageField(
        upload_to='message_thumbnails/',
        null=True,
        blank=True
    )
    is_scanned = models.BooleanField(default=False)
    scan_result = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Message Attachment'
        verbose_name_plural = 'Message Attachments'
    
    def __str__(self):
        return f"{self.filename} attached to message {self.message.id}"


# File Sharing Models

class SharedFile(models.Model):
    """General file sharing between users"""
    
    id = models.BigAutoField(primary_key=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shared_files'
    )
    shared_with = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_files'
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='shared_files',
        null=True,
        blank=True
    )
    award = models.ForeignKey(
        Award,
        on_delete=models.CASCADE,
        related_name='shared_files',
        null=True,
        blank=True
    )
    file = models.FileField(upload_to=shared_file_path)
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True, null=True)
    download_count = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=False)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_scanned = models.BooleanField(default=False)
    scan_result = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_downloaded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Shared File'
        verbose_name_plural = 'Shared Files'
        indexes = [
            models.Index(fields=['uploaded_by_id']),
            models.Index(fields=['shared_with_id']),
            models.Index(fields=['conversation_id']),
            models.Index(fields=['award_id']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.filename} shared by {self.uploaded_by.username}"
    
    def is_expired(self):
        """Check if file has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def increment_download(self):
        """Increment download counter"""
        self.download_count += 1
        self.last_downloaded_at = timezone.now()
        self.save(update_fields=['download_count', 'last_downloaded_at'])
    
    def can_access(self, user):
        """Check if user can access file"""
        # Owner can always access
        if user == self.uploaded_by:
            return True
        
        # Intended recipient can access if not expired
        if user == self.shared_with and not self.is_expired():
            return True
        
        # Public files can be accessed by conversation participants
        if self.is_public and self.conversation:
            return user in [self.conversation.participant1, self.conversation.participant2]
        
        return False


# Online Class Models

class OnlineClass(models.Model):
    """Store online class URLs and details"""
    
    class Platform(models.TextChoices):
        ZOOM = 'ZOOM', 'Zoom'
        GOOGLE_MEET = 'GOOGLE_MEET', 'Google Meet'
        SKYPE = 'SKYPE', 'Skype'
        TEAMS = 'TEAMS', 'Microsoft Teams'
        CUSTOM = 'CUSTOM', 'Custom'
    
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        POSTPONED = 'POSTPONED', 'Postponed'
    
    class RecurrenceType(models.TextChoices):
        NONE = 'NONE', 'None'
        DAILY = 'DAILY', 'Daily'
        WEEKLY = 'WEEKLY', 'Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'
    
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name='online_classes'
    )
    host = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='hosted_classes'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    meeting_url = models.URLField()
    meeting_id = models.CharField(max_length=100, blank=True, null=True)
    password = models.CharField(max_length=50, blank=True, null=True)
    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
        default=Platform.CUSTOM
    )
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    max_participants = models.PositiveIntegerField(default=2)
    is_recording = models.BooleanField(default=False)
    recording_url = models.URLField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    join_url_participant = models.URLField(blank=True, null=True)
    join_url_host = models.URLField(blank=True, null=True)
    settings = models.JSONField(default=dict)
    timezone = models.CharField(max_length=50, default='UTC')
    is_recurring = models.BooleanField(default=False)
    recurrence_type = models.CharField(
        max_length=20,
        choices=RecurrenceType.choices,
        default=RecurrenceType.NONE
    )
    recurrence_end_date = models.DateField(null=True, blank=True)
    waiting_list_enabled = models.BooleanField(default=False)
    max_waiting_list = models.PositiveIntegerField(default=10)
    reminder_sent = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True, null=True)
    rescheduled_from = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rescheduled_to'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Online Class'
        verbose_name_plural = 'Online Classes'
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['host_id']),
            models.Index(fields=['scheduled_start']),
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_start', 'status']),
            models.Index(fields=['is_recurring']),
            models.Index(fields=['recurrence_type']),
        ]
    
    def __str__(self):
        return f"Online Class: {self.title} ({self.scheduled_start})"
    
    def clean(self):
        """Validate the model data"""
        if self.scheduled_end <= self.scheduled_start:
            raise ValidationError('Scheduled end must be after scheduled start')
        
        if self.actual_start and self.actual_end:
            if self.actual_end <= self.actual_start:
                raise ValidationError('Actual end must be after actual start')
        
        if self.max_participants <= 0:
            raise ValidationError('Max participants must be positive')
        
        if self.is_recurring and self.recurrence_type == self.RecurrenceType.NONE:
            raise ValidationError('Recurrence type must be specified for recurring classes')
    
    def is_joinable(self):
        """Check if class can be joined"""
        now = timezone.now()
        return (
            self.status == self.Status.SCHEDULED and
            self.scheduled_start <= now <= self.scheduled_end
        )
    
    def get_duration(self):
        """Calculate class duration"""
        if self.actual_start and self.actual_end:
            return (self.actual_end - self.actual_start).total_seconds() / 60
        elif self.scheduled_start and self.scheduled_end:
            return (self.scheduled_end - self.scheduled_start).total_seconds() / 60
        return 0
    
    def get_participant_count(self):
        """Get current participant count"""
        return self.participants.filter(is_active=True).count()
    
    def is_full(self):
        """Check if class is at maximum capacity"""
        return self.get_participant_count() >= self.max_participants
    
    def get_waiting_list_count(self):
        """Get current waiting list count"""
        return self.waiting_list.filter(is_active=True).count()
    
    def is_waiting_list_full(self):
        """Check if waiting list is at maximum capacity"""
        return self.get_waiting_list_count() >= self.max_waiting_list
    
    def generate_join_urls(self):
        """Generate join URLs for participants"""
        # This would typically integrate with the specific platform's API
        # For now, we'll use the meeting_url as a placeholder
        if not self.join_url_participant:
            self.join_url_participant = self.meeting_url
        if not self.join_url_host:
            self.join_url_host = self.meeting_url
        self.save(update_fields=['join_url_participant', 'join_url_host'])
    
    def send_reminder(self):
        """Mark reminder as sent"""
        self.reminder_sent = True
        self.save(update_fields=['reminder_sent'])
    
    def cancel(self, reason=None):
        """Cancel the class"""
        self.status = self.Status.CANCELLED
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancellation_reason'])
    
    def postpone(self, new_start_time, new_end_time):
        """Postpone the class to a new time"""
        self.status = self.Status.POSTPONED
        self.scheduled_start = new_start_time
        self.scheduled_end = new_end_time
        self.save(update_fields=['status', 'scheduled_start', 'scheduled_end'])


class ClassParticipant(models.Model):
    """Track participants in online classes"""
    
    class Role(models.TextChoices):
        HOST = 'HOST', 'Host'
        PARTICIPANT = 'PARTICIPANT', 'Participant'
        OBSERVER = 'OBSERVER', 'Observer'
    
    id = models.BigAutoField(primary_key=True)
    online_class = models.ForeignKey(
        OnlineClass,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='class_participations'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PARTICIPANT
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Class Participant'
        verbose_name_plural = 'Class Participants'
        unique_together = ['online_class', 'user']
        indexes = [
            models.Index(fields=['online_class_id']),
            models.Index(fields=['user_id']),
            models.Index(fields=['joined_at']),
            models.Index(fields=['online_class_id', 'user_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} in {self.online_class.title}"
    
    def calculate_duration(self):
        """Calculate participation duration"""
        if self.joined_at and self.left_at:
            return (self.left_at - self.joined_at).total_seconds() / 60
        return 0


class ClassRecording(models.Model):
    """Store recordings of online classes"""
    
    class RecordingStatus(models.TextChoices):
        PROCESSING = 'PROCESSING', 'Processing'
        AVAILABLE = 'AVAILABLE', 'Available'
        FAILED = 'FAILED', 'Failed'
        EXPIRED = 'EXPIRED', 'Expired'
    
    id = models.BigAutoField(primary_key=True)
    online_class = models.ForeignKey(
        OnlineClass,
        on_delete=models.CASCADE,
        related_name='recordings'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    recording_url = models.URLField()
    recording_id = models.CharField(max_length=100, blank=True, null=True)
    platform_recording_id = models.CharField(max_length=100, blank=True, null=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    file_size_bytes = models.PositiveIntegerField(default=0)
    thumbnail_url = models.URLField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=RecordingStatus.choices,
        default=RecordingStatus.PROCESSING
    )
    is_public = models.BooleanField(default=False)
    password_protected = models.BooleanField(default=False)
    password = models.CharField(max_length=50, blank=True, null=True)
    download_enabled = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Class Recording'
        verbose_name_plural = 'Class Recordings'
        indexes = [
            models.Index(fields=['online_class_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"Recording: {self.title} ({self.online_class.title})"
    
    def is_expired(self):
        """Check if recording has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_download_count(self):
        """Increment download count"""
        self.download_count += 1
        self.save(update_fields=['download_count'])


class ClassSchedule(models.Model):
    """Store recurring class schedules"""
    
    class RecurrencePattern(models.TextChoices):
        DAILY = 'DAILY', 'Daily'
        WEEKLY = 'WEEKLY', 'Weekly'
        BIWEEKLY = 'BIWEEKLY', 'Bi-weekly'
        MONTHLY = 'MONTHLY', 'Monthly'
        CUSTOM = 'CUSTOM', 'Custom'
    
    id = models.BigAutoField(primary_key=True)
    online_class = models.ForeignKey(
        OnlineClass,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    recurrence_pattern = models.CharField(
        max_length=20,
        choices=RecurrencePattern.choices,
        default=RecurrencePattern.WEEKLY
    )
    recurrence_days = models.JSONField(default=list)  # Days of week for weekly pattern
    recurrence_interval = models.PositiveIntegerField(default=1)  # Every N weeks/days
    start_date = models.DateField()
    end_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    timezone = models.CharField(max_length=50, default='UTC')
    max_participants = models.PositiveIntegerField(default=2)
    is_active = models.BooleanField(default=True)
    exceptions = models.JSONField(default=list)  # Dates to skip
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Class Schedule'
        verbose_name_plural = 'Class Schedules'
        indexes = [
            models.Index(fields=['online_class_id']),
            models.Index(fields=['is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"Schedule: {self.title} ({self.recurrence_pattern})"
    
    def get_next_occurrence(self, from_date=None):
        """Get next scheduled occurrence"""
        if not from_date:
            from_date = timezone.now().date()
        
        # Simple implementation for weekly pattern
        if self.recurrence_pattern == self.RecurrencePattern.WEEKLY:
            days_of_week = self.recurrence_days if self.recurrence_days else [0]  # Default to Monday
            current_weekday = from_date.weekday()
            
            # Find next occurrence day
            for day_offset in range(7):
                check_day = (current_weekday + day_offset) % 7
                if check_day in days_of_week:
                    next_date = from_date + timezone.timedelta(days=day_offset)
                    if self.start_date <= next_date <= self.end_date:
                        return next_date
            
            return None
        
        # For other patterns, implement as needed
        return None
    
    def generate_occurrences(self, start_date, end_date):
        """Generate all occurrences within a date range"""
        occurrences = []
        
        if self.recurrence_pattern == self.RecurrencePattern.WEEKLY:
            current_date = max(start_date, self.start_date)
            while current_date <= min(end_date, self.end_date):
                if current_date.weekday() in (self.recurrence_days or []):
                    # Check if this date is not in exceptions
                    if current_date.isoformat() not in (self.exceptions or []):
                        occurrences.append(current_date)
                current_date += timezone.timedelta(days=1)
        
        return occurrences


class ClassResource(models.Model):
    """Store resources shared in online classes"""
    
    class ResourceType(models.TextChoices):
        DOCUMENT = 'DOCUMENT', 'Document'
        PRESENTATION = 'PRESENTATION', 'Presentation'
        VIDEO = 'VIDEO', 'Video'
        AUDIO = 'AUDIO', 'Audio'
        IMAGE = 'IMAGE', 'Image'
        LINK = 'LINK', 'Link'
        OTHER = 'OTHER', 'Other'
    
    id = models.BigAutoField(primary_key=True)
    online_class = models.ForeignKey(
        OnlineClass,
        on_delete=models.CASCADE,
        related_name='resources'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_resources'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    resource_type = models.CharField(
        max_length=20,
        choices=ResourceType.choices,
        default=ResourceType.DOCUMENT
    )
    file = models.FileField(
        upload_to='class_resources/',
        blank=True,
        null=True
    )
    file_size = models.PositiveIntegerField(default=0)
    url = models.URLField(blank=True, null=True)
    thumbnail = models.ImageField(
        upload_to='resource_thumbnails/',
        blank=True,
        null=True
    )
    is_public = models.BooleanField(default=True)
    download_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Class Resource'
        verbose_name_plural = 'Class Resources'
        indexes = [
            models.Index(fields=['online_class_id']),
            models.Index(fields=['uploaded_by_id']),
            models.Index(fields=['resource_type']),
            models.Index(fields=['is_public']),
            models.Index(fields=['order']),
        ]
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"Resource: {self.title} ({self.online_class.title})"
    
    def increment_download_count(self):
        """Increment download count"""
        self.download_count += 1
        self.save(update_fields=['download_count'])
    
    def increment_view_count(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def get_file_size_display(self):
        """Get formatted file size"""
        if self.file_size == 0:
            return "0 bytes"
        
        size_names = ["bytes", "KB", "MB", "GB"]
        i = 0
        size = float(self.file_size)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"


class ClassAttendance(models.Model):
    """Track attendance for online classes"""
    
    class AttendanceStatus(models.TextChoices):
        ATTENDED = 'ATTENDED', 'Attended'
        ABSENT = 'ABSENT', 'Absent'
        LATE = 'LATE', 'Late'
        LEFT_EARLY = 'LEFT_EARLY', 'Left Early'
        NO_SHOW = 'NO_SHOW', 'No Show'
    
    id = models.BigAutoField(primary_key=True)
    online_class = models.ForeignKey(
        OnlineClass,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    status = models.CharField(
        max_length=20,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.NO_SHOW
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    engagement_score = models.PositiveIntegerField(default=0)  # 0-100 scale
    notes = models.TextField(blank=True, null=True)
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='marked_attendance'
    )
    marked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Class Attendance'
        verbose_name_plural = 'Class Attendance Records'
        unique_together = ['online_class', 'user']
        indexes = [
            models.Index(fields=['online_class_id']),
            models.Index(fields=['user_id']),
            models.Index(fields=['status']),
            models.Index(fields=['joined_at']),
        ]
    
    def __str__(self):
        return f"Attendance: {self.user.username} in {self.online_class.title}"
    
    def calculate_duration(self):
        """Calculate attendance duration"""
        if self.joined_at and self.left_at:
            return (self.left_at - self.joined_at).total_seconds() / 60
        return 0
    
    def calculate_engagement_score(self):
        """Calculate engagement score based on various factors"""
        # Base score from attendance duration
        if self.duration_minutes <= 0:
            return 0
        
        class_duration = self.online_class.get_duration()
        if class_duration <= 0:
            return 0
        
        # Calculate attendance percentage
        attendance_percentage = min(100, (self.duration_minutes / class_duration) * 100)
        
        # Adjust for status
        if self.status == self.AttendanceStatus.ATTENDED:
            score = attendance_percentage
        elif self.status == self.AttendanceStatus.LATE:
            score = max(0, attendance_percentage - 10)  # Deduct 10% for being late
        elif self.status == self.AttendanceStatus.LEFT_EARLY:
            score = max(0, attendance_percentage - 15)  # Deduct 15% for leaving early
        else:
            score = 0
        
        return int(score)
    
    def save(self, *args, **kwargs):
        # Calculate duration if join and leave times are set
        if self.joined_at and self.left_at and not self.duration_minutes:
            self.duration_minutes = int(self.calculate_duration())
        
        # Calculate engagement score if not set
        if not self.engagement_score:
            self.engagement_score = self.calculate_engagement_score()
        
        super().save(*args, **kwargs)


class ClassWaitingList(models.Model):
    """Manage waiting list for online classes"""
    
    id = models.BigAutoField(primary_key=True)
    online_class = models.ForeignKey(
        OnlineClass,
        on_delete=models.CASCADE,
        related_name='waiting_list'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='waiting_list_entries'
    )
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)
    notified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Class Waiting List'
        verbose_name_plural = 'Class Waiting Lists'
        unique_together = ['online_class', 'user']
        indexes = [
            models.Index(fields=['online_class_id']),
            models.Index(fields=['user_id']),
            models.Index(fields=['is_active']),
            models.Index(fields=['joined_at']),
        ]
        ordering = ['joined_at']
    
    def __str__(self):
        return f"Waiting List: {self.user.username} for {self.online_class.title}"
    
    def notify_user(self):
        """Mark user as notified"""
        self.notified = True
        self.notified_at = timezone.now()
        self.save(update_fields=['notified', 'notified_at'])


# Communication Preferences and Settings

class CommunicationPreference(models.Model):
    """User preferences for communication"""
    
    class EmailFrequency(models.TextChoices):
        IMMEDIATE = 'IMMEDIATE', 'Immediate'
        HOURLY = 'HOURLY', 'Hourly'
        DAILY = 'DAILY', 'Daily'
        NEVER = 'NEVER', 'Never'
    
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='communication_preferences'
    )
    allow_platform_messages = models.BooleanField(default=True)
    allow_email_communication = models.BooleanField(default=True)
    allow_file_sharing = models.BooleanField(default=True)
    allow_online_classes = models.BooleanField(default=True)
    email_notification_frequency = models.CharField(
        max_length=20,
        choices=EmailFrequency.choices,
        default=EmailFrequency.IMMEDIATE
    )
    auto_reply_message = models.TextField(blank=True, null=True)
    is_auto_reply_enabled = models.BooleanField(default=False)
    working_hours_start = models.TimeField(null=True, blank=True)
    working_hours_end = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Communication Preference'
        verbose_name_plural = 'Communication Preferences'
    
    def __str__(self):
        return f"Communication preferences for {self.user.username}"
    
    def is_within_working_hours(self):
        """Check if current time is within working hours"""
        if not self.working_hours_start or not self.working_hours_end:
            return True
        
        # Get current time in user's timezone
        try:
            from django.utils import timezone as django_tz
            import pytz
            
            user_tz = pytz.timezone(self.timezone)
            current_time = django_tz.now().astimezone(user_tz).time()
            
            return (
                self.working_hours_start <= current_time <= self.working_hours_end
            )
        except Exception:
            # If timezone conversion fails, assume it's within working hours
            return True


class BlockedUser(models.Model):
    """Users blocked from communication"""
    
    id = models.BigAutoField(primary_key=True)
    blocker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_users'
    )
    blocked = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_by'
    )
    reason = models.CharField(max_length=255, blank=True, null=True)
    is_permanent = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Blocked User'
        verbose_name_plural = 'Blocked Users'
        unique_together = ['blocker', 'blocked']
        indexes = [
            models.Index(fields=['blocker_id']),
            models.Index(fields=['blocked_id']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"
    
    def clean(self):
        """Validate the model data"""
        if self.blocker == self.blocked:
            raise ValidationError('Blocker and blocked must be different users')
        
        if not self.is_permanent and not self.expires_at:
            raise ValidationError('Expires at must be set for temporary blocks')
        
        if self.expires_at and self.expires_at <= timezone.now():
            raise ValidationError('Expires at must be in the future')
    
    def is_active(self):
        """Check if block is still active"""
        if self.is_permanent:
            return True
        
        if self.expires_at:
            return timezone.now() < self.expires_at
        
        return False
