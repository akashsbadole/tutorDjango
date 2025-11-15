import re
import uuid
import secrets
import hashlib
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import (
    MaskedEmail, Conversation, Message, BlockedUser, CommunicationPreference
)
from requirements.models import Award

User = get_user_model()


def generate_masked_email(award, student=None, tutor=None, expires_days=30):
    """
    Generate a unique masked email for communication between student and tutor.
    
    Args:
        award: Award object
        student: User object (optional, will use award.student if not provided)
        tutor: User object (optional, will use award.tutor if not provided)
        expires_days: Number of days until expiration (default: 30)
    
    Returns:
        MaskedEmail object
    """
    # Use award's student and tutor if not provided
    if not student:
        student = award.student
    if not tutor:
        tutor = award.tutor
    
    # Check if masked email already exists for this award
    existing = MaskedEmail.objects.filter(
        award=award,
        student=student,
        tutor=tutor
    ).first()
    
    if existing and not existing.is_expired():
        return existing
    
    # Create new masked email
    masked_email = MaskedEmail(
        award=award,
        student=student,
        tutor=tutor,
        student_real_email=student.email,
        tutor_real_email=tutor.email,
        expires_at=timezone.now() + timezone.timedelta(days=expires_days)
    )
    
    # Generate unique masked address
    masked_email.generate_masked_address()
    masked_email.save()
    
    return masked_email


def can_users_communicate(user1, user2, award=None):
    """
    Check if two users can communicate based on their relationship in the system.
    
    Args:
        user1: First user
        user2: Second user
        award: Award object (optional)
    
    Returns:
        Boolean indicating if users can communicate
    """
    # Users can't communicate with themselves
    if user1 == user2:
        return False
    
    # Check if either user has blocked the other
    if BlockedUser.objects.filter(
        Q(blocker=user1, blocked=user2) | 
        Q(blocker=user2, blocked=user1)
    ).exists():
        return False
    
    # If no award is provided, check if they have any shared awards
    if not award:
        return Award.objects.filter(
            Q(student=user1, tutor=user2) | 
            Q(student=user2, tutor=user1)
        ).exists()
    
    # If award is provided, check if both users are participants
    return award and (user1 in [award.student, award.tutor] and 
                      user2 in [award.student, award.tutor])


def create_conversation_if_allowed(user1, user2, award=None, subject=None):
    """
    Create a conversation between two users if they are allowed to communicate.
    
    Args:
        user1: First user (typically the creator)
        user2: Second user
        award: Award object (optional)
        subject: Subject for the conversation (optional)
    
    Returns:
        Conversation object or None if not allowed
    """
    # Check if users can communicate
    if not can_users_communicate(user1, user2, award):
        return None
    
    # Check if conversation already exists
    existing = Conversation.objects.filter(
        Q(participant1=user1, participant2=user2) |
        Q(participant1=user2, participant2=user1)
    ).first()
    
    if existing:
        return existing
    
    # Create new conversation
    conversation = Conversation(
        participant1=user1,
        participant2=user2,
        award=award,
        subject=subject
    )
    conversation.save()
    
    return conversation


def detect_personal_info(content):
    """
    Detect personal contact information in text content.
    
    Args:
        content: Text content to check
    
    Returns:
        Tuple of (contains_info, detected_patterns)
    """
    detected_patterns = []
    
    # Phone number patterns
    phone_patterns = [
        r'\b\d{10}\b',  # 10-digit numbers
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # US format
        r'\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # International
    ]
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Check for phone numbers
    for pattern in phone_patterns:
        if re.search(pattern, content):
            detected_patterns.append("phone_number")
    
    # Check for email addresses
    if re.search(email_pattern, content):
        detected_patterns.append("email_address")
    
    # Check for common messaging apps
    messaging_apps = [
        r'\bwhatsapp\b',
        r'\btelegram\b',
        r'\bsignal\b',
        r'\bwechat\b',
        r'\bfacebook messenger\b',
        r'\bdiscord\b',
        r'\bskype\b',
    ]
    
    for app_pattern in messaging_apps:
        if re.search(app_pattern, content, re.IGNORECASE):
            detected_patterns.append("messaging_app")
            break
    
    # Check for social media
    social_media = [
        r'\bfacebook\b',
        r'\binstagram\b',
        r'\btwitter\b',
        r'\blinkedin\b',
        r'\bsnapchat\b',
    ]
    
    for social_pattern in social_media:
        if re.search(social_pattern, content, re.IGNORECASE):
            detected_patterns.append("social_media")
            break
    
    return (len(detected_patterns) > 0, list(set(detected_patterns)))


def sanitize_content(content):
    """
    Remove or mask personal contact information from text content.
    
    Args:
        content: Text content to sanitize
    
    Returns:
        Sanitized text content
    """
    # Phone number patterns
    phone_patterns = [
        r'\b\d{10}\b',  # 10-digit numbers
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # US format
        r'\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # International
    ]
    
    # Email pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Replace phone numbers
    for pattern in phone_patterns:
        content = re.sub(pattern, '[PHONE NUMBER REMOVED]', content)
    
    # Replace email addresses
    content = re.sub(email_pattern, '[EMAIL ADDRESS REMOVED]', content)
    
    # Replace messaging app references
    messaging_apps = [
        r'\bwhatsapp\b',
        r'\btelegram\b',
        r'\bsignal\b',
        r'\bwechat\b',
        r'\bfacebook messenger\b',
        r'\bdiscord\b',
        r'\bskype\b',
    ]
    
    for app_pattern in messaging_apps:
        content = re.sub(app_pattern, '[MESSAGING APP REMOVED]', content, flags=re.IGNORECASE)
    
    # Replace social media references
    social_media = [
        r'\bfacebook\b',
        r'\binstagram\b',
        r'\btwitter\b',
        r'\blinkedin\b',
        r'\bsnapchat\b',
    ]
    
    for social_pattern in social_media:
        content = re.sub(social_pattern, '[SOCIAL MEDIA REMOVED]', content, flags=re.IGNORECASE)
    
    return content


def get_user_conversations(user):
    """
    Get all conversations for a user with additional context.
    
    Args:
        user: User object
    
    Returns:
        QuerySet of Conversation objects
    """
    return Conversation.objects.filter(
        Q(participant1=user) | Q(participant2=user),
        is_active=True
    ).select_related(
        'participant1', 'participant2', 'award'
    ).annotate(
        last_message_time=Max('messages__created_at'),
        unread_count=Count('messages', filter=Q(
            Q(messages__created_at__gt=user.communication_preferences.participant1_last_read if user == user else user.communication_preferences.participant2_last_read)
        ))
    ).order_by('-last_message_time')


def get_user_masked_emails(user):
    """
    Get all masked emails for a user.
    
    Args:
        user: User object
    
    Returns:
        QuerySet of MaskedEmail objects
    """
    return MaskedEmail.objects.filter(
        Q(student=user) | Q(tutor=user),
        is_active=True
    ).select_related('student', 'tutor', 'award')


def check_user_communication_preferences(user, communication_type='message'):
    """
    Check if user allows a specific type of communication.
    
    Args:
        user: User object
        communication_type: Type of communication ('message', 'email', 'file', 'class')
    
    Returns:
        Boolean indicating if user allows this type of communication
    """
    # Get or create communication preferences
    preferences, created = CommunicationPreference.objects.get_or_create(user=user)
    
    if communication_type == 'message':
        return preferences.allow_platform_messages
    elif communication_type == 'email':
        return preferences.allow_email_communication
    elif communication_type == 'file':
        return preferences.allow_file_sharing
    elif communication_type == 'class':
        return preferences.allow_online_classes
    
    return True  # Default to allowing


def validate_file_upload(file, allowed_types=None, max_size_mb=50):
    """
    Validate an uploaded file for security and size constraints.
    
    Args:
        file: Uploaded file object
        allowed_types: List of allowed MIME types (optional)
        max_size_mb: Maximum file size in MB (default: 50)
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not allowed_types:
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        ]
    
    # Check file size
    max_size_bytes = max_size_mb * 1024 * 1024
    if file.size > max_size_bytes:
        return (False, f"File size cannot exceed {max_size_mb}MB.")
    
    # Check file type
    if file.content_type not in allowed_types:
        return (False, f"File type {file.content_type} is not allowed.")
    
    # Basic file extension validation
    allowed_extensions = [
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf',
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.txt', '.zip', '.rar'
    ]
    
    file_extension = file.name.lower().split('.')[-1]
    if f'.{file_extension}' not in allowed_extensions:
        return (False, f"File extension .{file_extension} is not allowed.")
    
    return (True, None)


def generate_unique_token(length=32):
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Length of the token (default: 32)
    
    Returns:
        Random token string
    """
    return secrets.token_urlsafe(length)


def hash_content(content):
    """
    Create a hash of content for integrity verification.
    
    Args:
        content: Content to hash
    
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def extract_urls_from_text(text):
    """
    Extract all URLs from text content.
    
    Args:
        text: Text content to search for URLs
    
    Returns:
        List of URLs found in the text
    """
    # URL pattern
    url_pattern = r'https?://(?:[-\w.]|(?:\[[0-9]{1,3}\])+(?:[a-zA-Z0-9-]{2,4})?(?:/|[^\s])'
    
    # Find all URLs in the text
    urls = re.findall(url_pattern, text)
    
    return urls


def mask_email_in_text(text):
    """
    Replace email addresses in text with a masked version.
    
    Args:
        text: Text content containing email addresses
    
    Returns:
        Text with masked email addresses
    """
    # Email pattern
    email_pattern = r'\b([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+)\.([A-Z|a-z]{2,})\b'
    
    def mask_email(match):
        username = match.group(1)
        domain = match.group(2)
        tld = match.group(3)
        
        # Mask all but first and last characters of username
        if len(username) > 2:
            masked_username = username[0] + '*' * (len(username) - 2) + username[-1]
        else:
            masked_username = username
        
        return f"{masked_username}@{domain}.{tld}"
    
    # Replace all email addresses with masked versions
    return re.sub(email_pattern, mask_email, text)


def get_or_create_user_preferences(user):
    """
    Get or create communication preferences for a user.
    
    Args:
        user: User object
    
    Returns:
        CommunicationPreference object
    """
    preferences, created = CommunicationPreference.objects.get_or_create(user=user)
    
    # Set default values if newly created
    if created:
        preferences.allow_platform_messages = True
        preferences.allow_email_communication = True
        preferences.allow_file_sharing = True
        preferences.allow_online_classes = True
        preferences.email_notification_frequency = CommunicationPreference.EmailFrequency.IMMEDIATE
        preferences.timezone = 'UTC'
        preferences.save()
    
    return preferences


def check_conversation_access(user, conversation):
    """
    Check if a user can access a conversation.
    
    Args:
        user: User object
        conversation: Conversation object
    
    Returns:
        Boolean indicating if user can access the conversation
    """
    # Check if user is a participant
    if user not in [conversation.participant1, conversation.participant2]:
        return False
    
    # Check if conversation is active
    if not conversation.is_active:
        return False
    
    # Check if user has deleted the conversation
    if user == conversation.participant1 and conversation.participant1_deleted:
        return False
    
    if user == conversation.participant2 and conversation.participant2_deleted:
        return False
    
    return True


def get_message_thread(message):
    """
    Get all messages in a thread (replies to a message).
    
    Args:
        message: Parent message object
    
    Returns:
        QuerySet of Message objects (replies)
    """
    return Message.objects.filter(
        parent_message=message,
        is_deleted=False
    ).select_related('sender').order_by('created_at')


def format_file_size(size_bytes):
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: File size in bytes
    
    Returns:
        Formatted file size string
    """
    if size_bytes == 0:
        return "0 bytes"
    
    size_names = ["bytes", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def is_user_available_for_communication(user):
    """
    Check if a user is available for communication based on their preferences.
    
    Args:
        user: User object
    
    Returns:
        Boolean indicating if user is available
    """
    preferences = get_or_create_user_preferences(user)
    
    # Check if user is within working hours
    if not preferences.is_within_working_hours():
        return False
    
    # Check if auto-reply is enabled
    if preferences.is_auto_reply_enabled:
        return False
    
    return True


def send_communication_notification(recipient, sender, message_type, content):
    """
    Send a notification to a user about new communication.
    
    Args:
        recipient: User to receive the notification
        sender: User who sent the communication
        message_type: Type of message ('message', 'email', 'file', 'class')
        content: Content of the communication
    
    Returns:
        Boolean indicating if notification was sent
    """
    # Check if recipient allows this type of communication
    if not check_user_communication_preferences(recipient, message_type):
        return False
    
    # This would integrate with Django's notification system
    # For now, we'll just return True to indicate it would be sent
    return True


def cleanup_expired_masked_emails():
    """
    Clean up expired masked emails by marking them as inactive.
    
    Returns:
        Number of masked emails that were cleaned up
    """
    expired_emails = MaskedEmail.objects.filter(
        is_active=True,
        expires_at__lt=timezone.now()
    )
    
    count = expired_emails.count()
    expired_emails.update(is_active=False)
    
    return count


def cleanup_old_messages():
    """
    Clean up old deleted messages (older than 30 days).
    
    Returns:
        Number of messages that were cleaned up
    """
    cutoff_date = timezone.now() - timezone.timedelta(days=30)
    
    old_messages = Message.objects.filter(
        is_deleted=True,
        deleted_at__lt=cutoff_date
    )
    
    count = old_messages.count()
    old_messages.delete()
    
    return count


def get_conversation_statistics(conversation):
    """
    Get statistics for a conversation.
    
    Args:
        conversation: Conversation object
    
    Returns:
        Dictionary with conversation statistics
    """
    messages = conversation.messages.filter(is_deleted=False)
    
    total_messages = messages.count()
    sent_by_participant1 = messages.filter(sender=conversation.participant1).count()
    sent_by_participant2 = messages.filter(sender=conversation.participant2).count()
    
    # Count messages with attachments
    messages_with_attachments = messages.filter(attachments__isnull=False).distinct().count()
    
    # Get date of first and last message
    first_message = messages.order_by('created_at').first()
    last_message = messages.order_by('-created_at').first()
    
    return {
        'total_messages': total_messages,
        'sent_by_participant1': sent_by_participant1,
        'sent_by_participant2': sent_by_participant2,
        'messages_with_attachments': messages_with_attachments,
        'first_message_date': first_message.created_at if first_message else None,
        'last_message_date': last_message.created_at if last_message else None,
        'conversation_duration': (
            last_message.created_at - first_message.created_at
        ).total_seconds() / 3600 if first_message and last_message else 0  # in hours
    }


# Video Platform Integration Functions

def generate_zoom_meeting(online_class):
    """
    Generate a Zoom meeting for an online class.
    
    Args:
        online_class: OnlineClass object
    
    Returns:
        Dictionary with meeting details or None if failed
    """
    try:
        # This would integrate with Zoom API
        # For now, return mock data
        meeting_id = f"zoom-{secrets.token_hex(8)}"
        join_url_host = f"https://zoom.us/j/{meeting_id}?role=host"
        join_url_participant = f"https://zoom.us/j/{meeting_id}?role=participant"
        
        return {
            'meeting_id': meeting_id,
            'join_url_host': join_url_host,
            'join_url_participant': join_url_participant,
            'password': secrets.token_hex(6),
            'success': True
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def generate_google_meet_meeting(online_class):
    """
    Generate a Google Meet meeting for an online class.
    
    Args:
        online_class: OnlineClass object
    
    Returns:
        Dictionary with meeting details or None if failed
    """
    try:
        # This would integrate with Google Meet API
        # For now, return mock data
        meeting_id = f"meet-{secrets.token_hex(8)}"
        join_url = f"https://meet.google.com/{meeting_id}"
        
        return {
            'meeting_id': meeting_id,
            'join_url': join_url,
            'success': True
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def generate_teams_meeting(online_class):
    """
    Generate a Microsoft Teams meeting for an online class.
    
    Args:
        online_class: OnlineClass object
    
    Returns:
        Dictionary with meeting details or None if failed
    """
    try:
        # This would integrate with Microsoft Teams API
        # For now, return mock data
        meeting_id = f"teams-{secrets.token_hex(8)}"
        join_url = f"https://teams.microsoft.com/l/meetup-join/{meeting_id}"
        
        return {
            'meeting_id': meeting_id,
            'join_url': join_url,
            'success': True
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def generate_custom_meeting(online_class):
    """
    Generate a custom meeting URL for an online class.
    
    Args:
        online_class: OnlineClass object
    
    Returns:
        Dictionary with meeting details
    """
    meeting_id = f"custom-{secrets.token_hex(8)}"
    join_url = f"https://custom.tutorplatform.com/join/{meeting_id}"
    
    return {
        'meeting_id': meeting_id,
        'join_url': join_url,
        'success': True
    }


def create_meeting_for_platform(online_class):
    """
    Create a meeting based on the selected platform.
    
    Args:
        online_class: OnlineClass object
    
    Returns:
        Dictionary with meeting details
    """
    if online_class.platform == online_class.Platform.ZOOM:
        return generate_zoom_meeting(online_class)
    elif online_class.platform == online_class.Platform.GOOGLE_MEET:
        return generate_google_meet_meeting(online_class)
    elif online_class.platform == online_class.Platform.TEAMS:
        return generate_teams_meeting(online_class)
    else:
        return generate_custom_meeting(online_class)


# Calendar Integration Functions

def create_google_calendar_event(online_class, user):
    """
    Create a Google Calendar event for an online class.
    
    Args:
        online_class: OnlineClass object
        user: User object (who's calendar to add to)
    
    Returns:
        Dictionary with event details or None if failed
    """
    try:
        # This would integrate with Google Calendar API
        # For now, return mock data
        event_id = f"gcal-{secrets.token_hex(8)}"
        
        return {
            'event_id': event_id,
            'calendar_url': f"https://calendar.google.com/calendar/event?eid={event_id}",
            'success': True
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def create_outlook_calendar_event(online_class, user):
    """
    Create an Outlook Calendar event for an online class.
    
    Args:
        online_class: OnlineClass object
        user: User object (who's calendar to add to)
    
    Returns:
        Dictionary with event details or None if failed
    """
    try:
        # This would integrate with Outlook Calendar API
        # For now, return mock data
        event_id = f"outlook-{secrets.token_hex(8)}"
        
        return {
            'event_id': event_id,
            'calendar_url': f"https://outlook.live.com/calendar/0/deeplink/view/{event_id}",
            'success': True
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def sync_calendar_event(online_class, user, calendar_type='google'):
    """
    Sync an online class with user's calendar.
    
    Args:
        online_class: OnlineClass object
        user: User object
        calendar_type: Type of calendar ('google', 'outlook')
    
    Returns:
        Dictionary with sync result
    """
    if calendar_type == 'google':
        return create_google_calendar_event(online_class, user)
    elif calendar_type == 'outlook':
        return create_outlook_calendar_event(online_class, user)
    else:
        return {
            'success': False,
            'error': 'Unsupported calendar type'
        }


# Class Recording Functions

def start_class_recording(online_class):
    """
    Start recording for an online class.
    
    Args:
        online_class: OnlineClass object
    
    Returns:
        Dictionary with recording details or None if failed
    """
    try:
        # This would integrate with the platform's recording API
        # For now, create a mock recording
        recording = ClassRecording(
            online_class=online_class,
            title=f"Recording of {online_class.title}",
            description=f"Automatic recording of {online_class.title} on {online_class.scheduled_start}",
            recording_url=f"https://recordings.tutorplatform.com/{secrets.token_hex(8)}",
            recording_id=f"rec-{secrets.token_hex(8)}",
            platform_recording_id=f"plat-rec-{secrets.token_hex(8)}",
            status=ClassRecording.RecordingStatus.PROCESSING
        )
        recording.save()
        
        return {
            'recording_id': recording.id,
            'status': recording.status,
            'success': True
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def process_recording_completion(recording_id, duration_minutes=0, file_size_bytes=0):
    """
    Mark a recording as completed and update details.
    
    Args:
        recording_id: ID of ClassRecording object
        duration_minutes: Duration of recording in minutes
        file_size_bytes: Size of recording file in bytes
    
    Returns:
        Dictionary with result
    """
    try:
        recording = ClassRecording.objects.get(id=recording_id)
        recording.status = ClassRecording.RecordingStatus.AVAILABLE
        recording.duration_minutes = duration_minutes
        recording.file_size_bytes = file_size_bytes
        recording.save()
        
        return {
            'success': True,
            'recording_id': recording.id
        }
    except ClassRecording.DoesNotExist:
        return {
            'success': False,
            'error': 'Recording not found'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# Attendance Tracking Functions

def track_class_attendance(online_class, user, join_time=None, ip_address=None, user_agent=None):
    """
    Track when a user joins an online class.
    
    Args:
        online_class: OnlineClass object
        user: User object
        join_time: DateTime when user joined (optional)
        ip_address: IP address of user (optional)
        user_agent: User agent string (optional)
    
    Returns:
        ClassAttendance object or None if failed
    """
    try:
        attendance, created = ClassAttendance.objects.get_or_create(
            online_class=online_class,
            user=user,
            defaults={
                'joined_at': join_time or timezone.now(),
                'ip_address': ip_address,
                'user_agent': user_agent,
                'status': ClassAttendance.AttendanceStatus.ATTENDED
            }
        )
        
        if not created:
            attendance.joined_at = join_time or timezone.now()
            attendance.status = ClassAttendance.AttendanceStatus.ATTENDED
            attendance.save()
        
        return attendance
    except Exception as e:
        return None


def track_class_departure(online_class, user, leave_time=None):
    """
    Track when a user leaves an online class.
    
    Args:
        online_class: OnlineClass object
        user: User object
        leave_time: DateTime when user left (optional)
    
    Returns:
        ClassAttendance object or None if failed
    """
    try:
        attendance = ClassAttendance.objects.get(
            online_class=online_class,
            user=user
        )
        attendance.left_at = leave_time or timezone.now()
        attendance.duration_minutes = attendance.calculate_duration()
        attendance.save()
        
        return attendance
    except ClassAttendance.DoesNotExist:
        return None
    except Exception as e:
        return None


def calculate_engagement_score(attendance):
    """
    Calculate engagement score for a class attendance.
    
    Args:
        attendance: ClassAttendance object
    
    Returns:
        Integer engagement score (0-100)
    """
    return attendance.calculate_engagement_score()


# Class Analytics Functions

def get_class_analytics(online_class):
    """
    Get comprehensive analytics for an online class.
    
    Args:
        online_class: OnlineClass object
    
    Returns:
        Dictionary with analytics data
    """
    # Get attendance statistics
    total_participants = online_class.participants.count()
    attended_count = online_class.attendance_records.filter(
        attended=True
    ).count()
    
    # Get recording statistics
    total_recordings = online_class.recordings.count()
    total_views = online_class.recordings.aggregate(
        total_views=models.Sum('view_count')
    )['total_views'] or 0
    
    # Get resource statistics
    total_resources = online_class.resources.count()
    total_downloads = online_class.resources.aggregate(
        total_downloads=models.Sum('download_count')
    )['total_downloads'] or 0
    
    # Calculate attendance rate
    attendance_rate = (attended_count / total_participants * 100) if total_participants > 0 else 0
    
    # Calculate average engagement score
    avg_engagement = online_class.attendance_records.aggregate(
        avg_score=models.Avg('engagement_score')
    )['avg_score'] or 0
    
    return {
        'total_participants': total_participants,
        'attended_count': attended_count,
        'attendance_rate': round(attendance_rate, 2),
        'total_recordings': total_recordings,
        'total_views': total_views,
        'total_resources': total_resources,
        'total_downloads': total_downloads,
        'avg_engagement_score': round(avg_engagement, 2),
        'class_duration': online_class.get_duration()
    }


def get_class_revenue(online_class):
    """
    Calculate revenue for an online class.
    
    Args:
        online_class: OnlineClass object
    
    Returns:
        Dictionary with revenue data
    """
    # Get the session price if available
    try:
        session_price = online_class.session.award.price if online_class.session and online_class.session.award else 0
    except:
        session_price = 0
    
    # Calculate total revenue
    total_participants = online_class.participants.count()
    total_revenue = total_participants * session_price
    
    return {
        'session_price': session_price,
        'total_participants': total_participants,
        'total_revenue': total_revenue
    }


# Timezone Handling Functions

def convert_to_user_timezone(datetime_obj, user_timezone):
    """
    Convert a datetime object to user's timezone.
    
    Args:
        datetime_obj: DateTime object to convert
        user_timezone: Timezone string (e.g., 'America/New_York')
    
    Returns:
        DateTime object in user's timezone
    """
    try:
        import pytz
        tz = pytz.timezone(user_timezone)
        return timezone.localtime(datetime_obj, timezone=tz)
    except Exception:
        return datetime_obj


def get_user_timezone_display(user_timezone):
    """
    Get a user-friendly display of timezone.
    
    Args:
        user_timezone: Timezone string (e.g., 'America/New_York')
    
    Returns:
        Formatted timezone string
    """
    try:
        import pytz
        tz = pytz.timezone(user_timezone)
        now = timezone.now()
        local_time = now.astimezone(tz)
        offset = local_time.strftime('%z')
        return f"({offset}) {user_timezone}"
    except Exception:
        return user_timezone


def get_common_timezones():
    """
    Get a list of common timezones for selection.
    
    Returns:
        List of timezone tuples (value, label)
    """
    return [
        ('UTC', 'UTC (Coordinated Universal Time)'),
        ('America/New_York', 'Eastern Time (US & Canada)'),
        ('America/Chicago', 'Central Time (US & Canada)'),
        ('America/Denver', 'Mountain Time (US & Canada)'),
        ('America/Los_Angeles', 'Pacific Time (US & Canada)'),
        ('Europe/London', 'Greenwich Mean Time (London)'),
        ('Europe/Paris', 'Central European Time (Paris)'),
        ('Europe/Berlin', 'Central European Time (Berlin)'),
        ('Asia/Tokyo', 'Japan Standard Time (Tokyo)'),
        ('Asia/Shanghai', 'China Standard Time (Shanghai)'),
        ('Asia/Kolkata', 'India Standard Time (Kolkata)'),
        ('Australia/Sydney', 'Australian Eastern Time (Sydney)'),
    ]


# Class Management Functions

def send_class_reminder(online_class, user, reminder_type='email'):
    """
    Send a reminder for an upcoming class.
    
    Args:
        online_class: OnlineClass object
        user: User object to send reminder to
        reminder_type: Type of reminder ('email', 'push', 'sms')
    
    Returns:
        Dictionary with result
    """
    try:
        # This would integrate with notification system
        # For now, just mark as sent
        if not online_class.reminder_sent:
            online_class.send_reminder()
        
        return {
            'success': True,
            'message': f"Reminder sent to {user.username} for class {online_class.title}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def handle_class_cancellation(online_class, reason=None):
    """
    Handle cancellation of an online class.
    
    Args:
        online_class: OnlineClass object
        reason: Reason for cancellation (optional)
    
    Returns:
        Dictionary with result
    """
    try:
        online_class.cancel(reason)
        
        # Notify participants
        participants = online_class.participants.all()
        for participant in participants:
            # This would send actual notifications
            pass
        
        return {
            'success': True,
            'message': f"Class {online_class.title} has been cancelled"
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def handle_class_reschedule(online_class, new_start_time, new_end_time):
    """
    Handle rescheduling of an online class.
    
    Args:
        online_class: OnlineClass object
        new_start_time: New start time
        new_end_time: New end time
    
    Returns:
        Dictionary with result
    """
    try:
        online_class.postpone(new_start_time, new_end_time)
        
        # Notify participants
        participants = online_class.participants.all()
        for participant in participants:
            # This would send actual notifications
            pass
        
        return {
            'success': True,
            'message': f"Class {online_class.title} has been rescheduled"
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def manage_waiting_list(online_class, user, action='add'):
    """
    Add or remove a user from a class waiting list.
    
    Args:
        online_class: OnlineClass object
        user: User object
        action: Action to perform ('add', 'remove')
    
    Returns:
        Dictionary with result
    """
    try:
        if action == 'add':
            # Check if user is already on waiting list
            if ClassWaitingList.objects.filter(
                online_class=online_class,
                user=user,
                is_active=True
            ).exists():
                return {
                    'success': False,
                    'message': 'User is already on the waiting list'
                }
            
            # Check if waiting list is full
            if online_class.is_waiting_list_full():
                return {
                    'success': False,
                    'message': 'Waiting list is full'
                }
            
            # Add to waiting list
            waiting_entry = ClassWaitingList(
                online_class=online_class,
                user=user,
                is_active=True
            )
            waiting_entry.save()
            
            return {
                'success': True,
                'message': 'Added to waiting list'
            }
        
        elif action == 'remove':
            # Remove from waiting list
            waiting_entry = ClassWaitingList.objects.get(
                online_class=online_class,
                user=user
            )
            waiting_entry.is_active = False
            waiting_entry.save()
            
            return {
                'success': True,
                'message': 'Removed from waiting list'
            }
        
        else:
            return {
                'success': False,
                'error': 'Invalid action'
            }
    
    except ClassWaitingList.DoesNotExist:
        return {
            'success': False,
            'error': 'User not found on waiting list'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }