import uuid
import re
import time
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import logging
from django.db import models

from .models import MaskedEmail, EmailLog, EmailAttachment

logger = logging.getLogger(__name__)


class MaskedEmailBackend(BaseEmailBackend):
    """
    Custom email backend that handles masked email routing.
    
    This backend intercepts emails sent to masked addresses, routes them to the
    actual recipients, and logs all communications for privacy compliance.
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        
        # Get the real email backend to use for actual delivery
        self.real_backend_path = getattr(
            settings, 
            'MASKED_EMAIL_REAL_BACKEND', 
            'django.core.mail.backends.smtp.EmailBackend'
        )
        
        # Get masked email domain from settings
        self.masked_domain = getattr(
            settings,
            'MASKED_EMAIL_DOMAIN',
            'masked.tutorplatform.com'
        )
        
        # Initialize the real backend
        try:
            from django.utils.module_loading import import_string
            self.real_backend = import_string(self.real_backend_path)(
                fail_silently=fail_silently, **kwargs
            )
        except ImportError:
            if not fail_silently:
                raise ImproperlyConfigured(
                    f"Could not import email backend: {self.real_backend_path}"
                )
            self.real_backend = None
    
    def send_messages(self, email_messages):
        """
        Send a list of email messages.
        
        For each message, check if it's being sent to a masked address.
        If so, log it and route it to the actual recipient.
        """
        if not email_messages:
            return 0
        
        num_sent = 0
        
        for message in email_messages:
            try:
                if self._send_message(message):
                    num_sent += 1
            except Exception as e:
                if not self.fail_silently:
                    raise
                logger.error(f"Failed to send message: {e}")
        
        return num_sent
    
    def _send_message(self, message):
        """
        Process and send a single email message.
        """
        # Check if this is a message to a masked email address
        to_addresses = message.to
        masked_emails = []
        regular_emails = []
        
        # Separate masked and regular email addresses
        for addr in to_addresses:
            if self._is_masked_email(addr):
                masked_emails.append(addr)
            else:
                regular_emails.append(addr)
        
        # If there are masked emails, process them
        if masked_emails:
            for masked_addr in masked_emails:
                if not self._process_masked_email(message, masked_addr):
                    return False
        
        # If there are regular emails, send them through the real backend
        if regular_emails and self.real_backend:
            message.to = regular_emails
            return self.real_backend.send_messages([message]) > 0
        
        return True
    
    def _is_masked_email(self, email_address):
        """
        Check if an email address is a masked email address.
        """
        # Extract domain from email address
        try:
            domain = email_address.split('@')[1]
            return domain == self.masked_domain
        except (IndexError, AttributeError):
            return False
    
    def _process_masked_email(self, message, masked_address):
        """
        Process an email sent to a masked address.
        """
        try:
            # Find the masked email record
            masked_email = MaskedEmail.objects.get(
                masked_address=masked_address,
                is_active=True
            )
            
            # Check if the masked email has expired
            if masked_email.is_expired():
                logger.warning(f"Attempted to send to expired masked email: {masked_address}")
                return False
            
            # Determine the direction of the email
            from_address = message.from_email
            
            # Check if sender is the student or tutor
            if from_address == masked_email.student_real_email:
                direction = EmailLog.Direction.STUDENT_TO_TUTOR
                to_address = masked_email.tutor_real_email
            elif from_address == masked_email.tutor_real_email:
                direction = EmailLog.Direction.TUTOR_TO_STUDENT
                to_address = masked_email.student_real_email
            else:
                # Unauthorized sender
                logger.warning(f"Unauthorized sender {from_address} to masked email {masked_address}")
                return False
            
            # Check if either user has blocked the other
            from .models import BlockedUser
            if BlockedUser.objects.filter(
                blocker__email=to_address,
                blocked__email=from_address,
                expires_at__gt=timezone.now()
            ).exists():
                logger.info(f"Email blocked due to user block: {from_address} -> {to_address}")
                return False
            
            # Create email log entry
            email_log = EmailLog.objects.create(
                masked_email=masked_email,
                from_address=from_address,
                to_address=masked_address,  # Store the masked address as recipient
                subject=message.subject,
                body=message.body,
                direction=direction,
                message_id=self._generate_message_id(),
                in_reply_to=self._extract_reply_to(message),
                size_bytes=len(message.body.encode('utf-8')),
                is_processed=False
            )
            
            # Process attachments if any
            attachments_count = 0
            if hasattr(message, 'attachments') and message.attachments:
                for attachment in message.attachments:
                    if self._process_attachment(email_log, attachment):
                        attachments_count += 1
                
                # Update attachment count
                email_log.attachments_count = attachments_count
                email_log.save(update_fields=['attachments_count'])
            
            # Create a new email message to the actual recipient
            relay_message = EmailMessage(
                subject=message.subject,
                body=message.body,
                from_email=from_address,
                to=[to_address],
                cc=message.cc,
                bcc=message.bcc,
                reply_to=message.reply_to,
            )
            
            # Copy headers
            if hasattr(message, 'extra_headers') and message.extra_headers:
                relay_message.extra_headers = message.extra_headers
            
            # Copy attachments
            if hasattr(message, 'attachments') and message.attachments:
                for attachment in message.attachments:
                    relay_message.attach(attachment[0], attachment[1], attachment[2])
            
            # Send the relayed message through the real backend
            if self.real_backend:
                success = self.real_backend.send_messages([relay_message]) > 0
                
                # Update email log
                email_log.is_processed = success
                email_log.processed_at = timezone.now()
                
                if not success:
                    email_log.processing_error = "Failed to send through real backend"
                
                email_log.save(update_fields=['is_processed', 'processed_at', 'processing_error'])
                
                # Update masked email usage
                if success:
                    masked_email.increment_usage()
                
                return success
            else:
                # No real backend configured, just log the email
                email_log.is_processed = True
                email_log.processed_at = timezone.now()
                email_log.save(update_fields=['is_processed', 'processed_at'])
                masked_email.increment_usage()
                return True
                
        except MaskedEmail.DoesNotExist:
            logger.warning(f"Masked email not found: {masked_address}")
            return False
        except Exception as e:
            logger.error(f"Error processing masked email {masked_address}: {e}")
            return False
    
    def _generate_message_id(self):
        """
        Generate a unique message ID for email tracking.
        """
        return f"{uuid.uuid4()}@{self.masked_domain}"
    
    def _extract_reply_to(self, message):
        """
        Extract reply-to header for email threading.
        """
        if hasattr(message, 'reply_to') and message.reply_to:
            return message.reply_to[0] if message.reply_to else None
        
        # Check for In-Reply-To header in extra_headers
        if hasattr(message, 'extra_headers') and message.extra_headers:
            return message.extra_headers.get('In-Reply-To')
        
        return None
    
    def _process_attachment(self, email_log, attachment):
        """
        Process and store an email attachment.
        """
        try:
            filename, content, content_type = attachment
            
            # Generate a unique filename to avoid conflicts
            timestamp = int(time.time())
            unique_filename = f"{timestamp}_{filename}"
            
            # Save the attachment to storage
            path = f"email_attachments/{email_log.id}/{unique_filename}"
            saved_path = default_storage.save(path, ContentFile(content))
            
            # Create attachment record
            EmailAttachment.objects.create(
                email_log=email_log,
                filename=filename,
                file_path=saved_path,
                file_size=len(content) if isinstance(content, bytes) else len(content.encode('utf-8')),
                content_type=content_type,
                is_scanned=False,  # In a real implementation, you would scan for malware
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing attachment: {e}")
            return False
    
    def test_connection(self):
        """
        Test the connection to the email backend.
        """
        if self.real_backend:
            return self.real_backend.test_connection()
        return True


class MaskedEmailRouter:
    """
    Utility class to help route emails to masked addresses.
    """
    
    @staticmethod
    def create_masked_email(award, student, tutor, student_email, tutor_email, expires_days=30):
        """
        Create a new masked email for communication between student and tutor.
        """
        from django.utils import timezone
        
        # Check if a masked email already exists for this award
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
            student_real_email=student_email,
            tutor_real_email=tutor_email,
            expires_at=timezone.now() + timezone.timedelta(days=expires_days)
        )
        masked_email.save()
        
        return masked_email
    
    @staticmethod
    def get_conversation_emails(user):
        """
        Get all masked emails where the user is a participant.
        """
        return MaskedEmail.objects.filter(
            models.Q(student=user) | models.Q(tutor=user),
            is_active=True
        ).select_related('student', 'tutor', 'award')
    
    @staticmethod
    def get_email_logs(masked_email, direction=None):
        """
        Get email logs for a masked email, optionally filtered by direction.
        """
        queryset = EmailLog.objects.filter(masked_email=masked_email)
        
        if direction:
            queryset = queryset.filter(direction=direction)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def check_for_personal_info(content):
        """
        Check if content contains personal contact information.
        
        Returns a tuple of (contains_info, detected_patterns)
        """
        detected_patterns = []
        
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
        
        return (len(detected_patterns) > 0, detected_patterns)
    
    @staticmethod
    def sanitize_content(content):
        """
        Sanitize content by removing or masking personal contact information.
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