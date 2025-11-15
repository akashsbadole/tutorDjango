"""
Multi-channel notification delivery utilities.
This module provides functionality to:
1. Send notifications via multiple channels
2. Channel-specific formatting
3. Channel-specific delivery logic
4. Channel fallback mechanisms
5. Channel preference management
"""

from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils import timezone
import json
import logging
import requests

from .models import (
    Notification, NotificationDelivery, PushDevice, PushMessage,
    NotificationPreference
)

logger = logging.getLogger(__name__)


class BaseNotificationChannel:
    """
    Base class for notification channels.
    """
    
    def __init__(self, name):
        self.name = name
        self.enabled = True
    
    def send(self, notification, recipient):
        """
        Send notification via this channel.
        
        Args:
            notification: The notification to send
            recipient: The recipient user
            
        Returns:
            dict: Result of sending attempt
        """
        raise NotImplementedError("Subclasses must implement send method")
    
    def format_message(self, notification):
        """
        Format message for this channel.
        
        Args:
            notification: The notification to format
            
        Returns:
            dict: Formatted message data
        """
        return {
            'title': notification.title,
            'content': notification.content,
            'data': self._get_message_data(notification)
        }
    
    def _get_message_data(self, notification):
        """Get additional data for message formatting."""
        return {
            'notification_id': str(notification.id),
            'notification_type': notification.notification_type,
            'priority': notification.priority,
            'created_at': notification.created_at.isoformat(),
            'action_url': notification.action_url,
            'action_text': notification.action_text,
            'sender': notification.sender.get_full_name() if notification.sender else 'System',
        }
    
    def can_send(self, notification, recipient):
        """
        Check if notification can be sent via this channel.
        
        Args:
            notification: The notification to send
            recipient: The recipient user
            
        Returns:
            bool: True if can send, False otherwise
        """
        try:
            preference = NotificationPreference.objects.get(user=recipient)
            
            # Check if channel is enabled
            if self.name == 'email' and not preference.email_enabled:
                return False
            elif self.name == 'push' and not preference.push_enabled:
                return False
            elif self.name == 'in_app' and not preference.in_app_enabled:
                return False
            
            # Check if notification type is enabled for this channel
            if self.name == 'email':
                return preference.get_email_setting(notification.notification_type)
            elif self.name == 'push':
                return preference.get_push_setting(notification.notification_type)
            elif self.name == 'in_app':
                return preference.get_in_app_setting(notification.notification_type)
            
            return True
            
        except NotificationPreference.DoesNotExist:
            # Default to enabled if no preference exists
            return True


class EmailChannel(BaseNotificationChannel):
    """
    Email notification channel.
    """
    
    def __init__(self):
        super().__init__('email')
        self.from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
    
    def send(self, notification, recipient):
        """
        Send notification via email.
        """
        try:
            # Check if we can send
            if not self.can_send(notification, recipient):
                return {
                    'success': False,
                    'error': 'Channel not enabled for this notification type',
                    'channel': self.name
                }
            
            # Get email template or use default
            subject = notification.title
            body = self._render_email_body(notification)
            
            # Send email
            send_mail(
                subject=subject,
                message="",
                html_message=body,
                from_email=self.from_email,
                recipient_list=[recipient.email],
                fail_silently=False
            )
            
            # Update notification
            notification.email_sent = True
            notification.email_sent_at = timezone.now()
            notification.save(update_fields=['email_sent', 'email_sent_at'])
            
            # Create delivery record
            delivery = NotificationDelivery.objects.create(
                notification=notification,
                channel='EMAIL',
                status='sent',
                sent_at=timezone.now(),
                recipient_address=recipient.email
            )
            
            return {
                'success': True,
                'delivery_id': delivery.pk,
                'channel': self.name
            }
            
        except Exception as e:
            logger.error(f"Failed to send email notification {notification.pk}: {e}")
            return {
                'success': False,
                'error': str(e),
                'channel': self.name
            }
    
    def _render_email_body(self, notification):
        """Render HTML email body."""
        try:
            # Try to use email template
            from .models import NotificationTemplate
            
            template = NotificationTemplate.objects.get(
                notification_type=notification.notification_type,
                is_default=True,
                is_active=True
            )
            
            context = self._get_message_data(notification)
            return template.render_body(notification)
            
        except Exception:
            # Use default template
            return render_to_string('notifications/email_notification.html', {
                'notification': notification,
                'recipient': notification.recipient,
                'sender': notification.sender,
            })


class PushChannel(BaseNotificationChannel):
    """
    Push notification channel.
    """
    
    def __init__(self):
        super().__init__('push')
        self.providers = {
            'fcm': self._send_fcm,
            'apns': self._send_apns,
            'webpush': self._send_webpush
        }
        self.default_provider = getattr(settings, 'PUSH_PROVIDER', 'fcm')
    
    def send(self, notification, recipient):
        """
        Send notification via push.
        """
        try:
            # Check if we can send
            if not self.can_send(notification, recipient):
                return {
                    'success': False,
                    'error': 'Channel not enabled for this notification type',
                    'channel': self.name
                }
            
            # Get user's active devices
            devices = PushDevice.objects.filter(
                user=recipient,
                is_active=True
            )
            
            if not devices.exists():
                return {
                    'success': False,
                    'error': 'No active devices found',
                    'channel': self.name
                }
            
            results = []
            success_count = 0
            
            for device in devices:
                result = self._send_to_device(notification, device)
                results.append(result)
                
                if result['success']:
                    success_count += 1
            
            # Update notification
            if success_count > 0:
                notification.push_sent = True
                notification.push_sent_at = timezone.now()
                notification.save(update_fields=['push_sent', 'push_sent_at'])
            
            return {
                'success': success_count > 0,
                'results': results,
                'success_count': success_count,
                'total_devices': devices.count(),
                'channel': self.name
            }
            
        except Exception as e:
            logger.error(f"Failed to send push notification {notification.pk}: {e}")
            return {
                'success': False,
                'error': str(e),
                'channel': self.name
            }
    
    def _send_to_device(self, notification, device):
        """Send notification to a specific device."""
        provider_func = self.providers.get(device.device_type.lower(), self.providers['fcm'])
        
        message_data = self.format_message(notification)
        
        # Add device-specific data
        if device.device_type == 'IOS':
            message_data['badge'] = 1
            message_data['sound'] = 'default'
        
        return provider_func(device, message_data)
    
    def _send_fcm(self, device, message_data):
        """Send via Firebase Cloud Messaging."""
        try:
            # Get FCM settings
            fcm_key = getattr(settings, 'FCM_SERVER_KEY', '')
            fcm_url = getattr(settings, 'FCM_URL', 'https://fcm.googleapis.com/fcm/send')
            
            # Prepare payload
            payload = {
                'to': device.device_token,
                'notification': {
                    'title': message_data['title'],
                    'body': message_data['content'],
                    'sound': message_data.get('sound', 'default'),
                    'badge': message_data.get('badge', 0)
                },
                'data': message_data['data']
            }
            
            # Send request
            headers = {
                'Authorization': f'key={fcm_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                fcm_url,
                data=json.dumps(payload),
                headers=headers,
                timeout=10
            )
            
            # Create push message record
            push_message = PushMessage.objects.create(
                notification=message_data['data']['notification_id'],
                device=device,
                title=message_data['title'],
                body=message_data['content'],
                sound=message_data.get('sound', 'default'),
                badge=message_data.get('badge'),
                data=message_data['data']
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success', 0) > 0:
                    push_message.status = 'sent'
                    push_message.sent_at = timezone.now()
                    push_message.provider_response = result
                    push_message.save(update_fields=['status', 'sent_at', 'provider_response'])
                    
                    return {
                        'success': True,
                        'message_id': push_message.pk,
                        'response': result
                    }
            
            # Handle failure
            push_message.status = 'failed'
            push_message.failed_at = timezone.now()
            push_message.failure_reason = response.text
            push_message.save(update_fields=['status', 'failed_at', 'failure_reason'])
            
            return {
                'success': False,
                'error': response.text,
                'message_id': push_message.pk
            }
            
        except Exception as e:
            logger.error(f"FCM send error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_apns(self, device, message_data):
        """Send via Apple Push Notification Service."""
        # Implementation would depend on APNS library
        # This is a placeholder implementation
        return {
            'success': False,
            'error': 'APNS not implemented'
        }
    
    def _send_webpush(self, device, message_data):
        """Send via Web Push API."""
        # Implementation would depend on web-push library
        # This is a placeholder implementation
        return {
            'success': False,
            'error': 'Web Push not implemented'
        }


class InAppChannel(BaseNotificationChannel):
    """
    In-app notification channel.
    """
    
    def __init__(self):
        super().__init__('in_app')
    
    def send(self, notification, recipient):
        """
        "Send" notification via in-app channel.
        
        In-app notifications are stored in the database
        and retrieved by the frontend via API.
        """
        try:
            # Check if we can send
            if not self.can_send(notification, recipient):
                return {
                    'success': False,
                    'error': 'Channel not enabled for this notification type',
                    'channel': self.name
                }
            
            # In-app notifications are created as "sent" by default
            # No additional action needed
            
            # Create delivery record
            delivery = NotificationDelivery.objects.create(
                notification=notification,
                channel='IN_APP',
                status='delivered',
                sent_at=timezone.now(),
                delivered_at=timezone.now(),
                recipient_address=str(recipient.pk)
            )
            
            return {
                'success': True,
                'delivery_id': delivery.pk,
                'channel': self.name
            }
            
        except Exception as e:
            logger.error(f"Failed to create in-app notification {notification.pk}: {e}")
            return {
                'success': False,
                'error': str(e),
                'channel': self.name
            }


class SMSChannel(BaseNotificationChannel):
    """
    SMS notification channel.
    """
    
    def __init__(self):
        super().__init__('sms')
        self.provider = getattr(settings, 'SMS_PROVIDER', 'twilio')
    
    def send(self, notification, recipient):
        """
        Send notification via SMS.
        """
        try:
            # Check if we can send
            if not self.can_send(notification, recipient):
                return {
                    'success': False,
                    'error': 'Channel not enabled for this notification type',
                    'channel': self.name
                }
            
            # Get phone number from user profile
            try:
                phone_number = recipient.profile.phone_number
            except AttributeError:
                return {
                    'success': False,
                    'error': 'Recipient has no phone number',
                    'channel': self.name
                }
            
            if not phone_number:
                return {
                    'success': False,
                    'error': 'No phone number available',
                    'channel': self.name
                }
            
            # Send via provider
            if self.provider == 'twilio':
                result = self._send_twilio(notification, phone_number)
            else:
                result = {
                    'success': False,
                    'error': f'Unknown SMS provider: {self.provider}',
                    'channel': self.name
                }
            
            # Create delivery record
            if result['success']:
                NotificationDelivery.objects.create(
                    notification=notification,
                    channel='SMS',
                    status='sent',
                    sent_at=timezone.now(),
                    recipient_address=phone_number
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to send SMS notification {notification.pk}: {e}")
            return {
                'success': False,
                'error': str(e),
                'channel': self.name
            }
    
    def _send_twilio(self, notification, phone_number):
        """Send SMS via Twilio."""
        try:
            from twilio.rest import Client
            
            # Get Twilio credentials
            account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
            auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
            from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
            
            # Initialize client
            client = Client(account_sid, auth_token)
            
            # Send message
            message = client.messages.create(
                body=notification.content,
                from_=from_number,
                to=phone_number
            )
            
            return {
                'success': True,
                'message_id': message.sid,
                'channel': self.name
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'channel': self.name
            }


class NotificationChannelManager:
    """
    Manages multiple notification channels.
    """
    
    def __init__(self):
        self.channels = {
            'email': EmailChannel(),
            'push': PushChannel(),
            'in_app': InAppChannel(),
            'sms': SMSChannel()
        }
        self.default_channels = ['in_app', 'email']  # Default channels
    
    def send_notification(self, notification, channels=None, fallback=True):
        """
        Send notification via specified channels.
        
        Args:
            notification: The notification to send
            channels: List of channels to use (None for defaults)
            fallback: Whether to use fallback channels on failure
            
        Returns:
            dict: Results of sending attempts
        """
        if channels is None:
            channels = self.default_channels
        
        results = {}
        successful_channels = []
        failed_channels = []
        
        for channel_name in channels:
            if channel_name not in self.channels:
                failed_channels.append(channel_name)
                continue
            
            channel = self.channels[channel_name]
            result = channel.send(notification, notification.recipient)
            results[channel_name] = result
            
            if result['success']:
                successful_channels.append(channel_name)
            else:
                failed_channels.append(channel_name)
                
                # Try fallback channels
                if fallback:
                    fallback_result = self._try_fallback(
                        notification, channel_name, successful_channels
                    )
                    if fallback_result:
                        results[f"{channel_name}_fallback"] = fallback_result
                        if fallback_result['success']:
                            successful_channels.append(fallback_result['channel'])
        
        return {
            'notification_id': notification.pk,
            'successful_channels': successful_channels,
            'failed_channels': failed_channels,
            'results': results,
            'overall_success': len(successful_channels) > 0
        }
    
    def _try_fallback(self, notification, failed_channel, successful_channels):
        """
        Try fallback channels for a failed channel.
        """
        # Define fallback order
        fallback_order = {
            'email': ['push', 'in_app', 'sms'],
            'push': ['email', 'in_app', 'sms'],
            'sms': ['email', 'push', 'in_app'],
            'in_app': []  # No fallback for in-app
        }
        
        for fallback_channel in fallback_order.get(failed_channel, []):
            if fallback_channel in successful_channels:
                continue  # Already tried this channel
            
            if fallback_channel in self.channels:
                channel = self.channels[fallback_channel]
                
                # Check if channel is enabled for this notification type
                if channel.can_send(notification, notification.recipient):
                    result = channel.send(notification, notification.recipient)
                    if result['success']:
                        return {
                            'success': True,
                            'channel': fallback_channel,
                            'original_channel': failed_channel,
                            'message': f"Fallback via {fallback_channel}"
                        }
        
        return None
    
    def get_channel(self, name):
        """Get a specific channel by name."""
        return self.channels.get(name)
    
    def add_channel(self, name, channel):
        """Add a new channel."""
        self.channels[name] = channel
    
    def remove_channel(self, name):
        """Remove a channel."""
        if name in self.channels:
            del self.channels[name]


# Global instance
channel_manager = NotificationChannelManager()


def send_notification(notification, channels=None, fallback=True):
    """Convenience function to send notification via channels."""
    return channel_manager.send_notification(notification, channels, fallback)


def get_channel(name):
    """Convenience function to get a specific channel."""
    return channel_manager.get_channel(name)