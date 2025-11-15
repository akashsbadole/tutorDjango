"""
Notification scheduling and timing controls.
This module provides functionality to:
1. Schedule notifications for specific times
2. Respect quiet hours
3. Handle timezone conversions
4. Implement delivery delays
5. Control notification frequency
"""

from datetime import datetime, timedelta, time
from django.utils import timezone
from django.db import models
from django.contrib.auth import get_user_model
import pytz
import logging

from .models import Notification, NotificationPreference

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationScheduler:
    """
    Handles scheduling and timing of notifications.
    
    This class provides methods to:
    1. Schedule notifications for specific times
    2. Respect user quiet hours
    3. Handle timezone conversions
    4. Implement delivery delays
    5. Control notification frequency
    """
    
    def __init__(self):
        self.default_timezone = 'UTC'
    
    def schedule_notification(self, notification, scheduled_at=None, delay_minutes=None):
        """
        Schedule a notification for a specific time or with a delay.
        
        Args:
            notification: The notification to schedule
            scheduled_at: Specific datetime to send the notification
            delay_minutes: Number of minutes to delay the notification
            
        Returns:
            The scheduled notification (may be the same or a new one)
        """
        if scheduled_at:
            if scheduled_at <= timezone.now():
                # Scheduled time is in the past, send now
                return notification
            notification.scheduled_at = scheduled_at
            notification.save(update_fields=['scheduled_at'])
            return notification
        
        if delay_minutes:
            scheduled_at = timezone.now() + timedelta(minutes=delay_minutes)
            notification.scheduled_at = scheduled_at
            notification.save(update_fields=['scheduled_at'])
            return notification
        
        return notification
    
    def is_quiet_hours(self, user):
        """
        Check if current time is within user's quiet hours.
        
        Args:
            user: The user to check quiet hours for
            
        Returns:
            True if current time is within quiet hours, False otherwise
        """
        try:
            preference = NotificationPreference.objects.get(user=user)
            return preference.is_in_quiet_hours()
        except NotificationPreference.DoesNotExist:
            return False
    
    def get_next_available_time(self, user, priority='medium'):
        """
        Get the next available time to send a notification to a user,
        respecting their quiet hours and other timing preferences.
        
        Args:
            user: The user to send notification to
            priority: Priority of the notification ('low', 'medium', 'high', 'urgent')
            
        Returns:
            datetime: The next available time to send the notification
        """
        # Urgent notifications bypass quiet hours
        if priority.lower() == 'urgent':
            return timezone.now()
        
        try:
            preference = NotificationPreference.objects.get(user=user)
            
            # If quiet hours are not enabled, send now
            if not preference.quiet_hours_enabled:
                return timezone.now()
            
            # Get user's timezone
            user_tz = pytz.timezone(preference.quiet_hours_timezone)
            current_time = timezone.now().astimezone(user_tz)
            
            # Get quiet hours start and end times
            start_time = preference.quiet_hours_start
            end_time = preference.quiet_hours_end
            
            if not start_time or not end_time:
                return timezone.now()
            
            # Check if we're currently in quiet hours
            if start_time <= end_time:
                # Normal case (e.g., 22:00 to 08:00)
                if start_time <= current_time.time() <= end_time:
                    # We're in quiet hours, schedule for after end time
                    tomorrow = current_time.date() + timedelta(days=1)
                    return user_tz.localize(
                        datetime.combine(tomorrow, end_time)
                    ).astimezone(pytz.UTC)
            else:
                # Overnight case (e.g., 22:00 to 08:00 next day)
                if current_time.time() >= start_time or current_time.time() <= end_time:
                    # We're in quiet hours
                    if current_time.time() >= start_time:
                        # Schedule for tomorrow after end time
                        tomorrow = current_time.date() + timedelta(days=1)
                        return user_tz.localize(
                            datetime.combine(tomorrow, end_time)
                        ).astimezone(pytz.UTC)
                    else:
                        # Schedule for later today after end time
                        return user_tz.localize(
                            datetime.combine(current_time.date(), end_time)
                        ).astimezone(pytz.UTC)
            
            return timezone.now()
            
        except NotificationPreference.DoesNotExist:
            return timezone.now()
        except Exception as e:
            logger.error(f"Error calculating next available time for user {user.pk}: {e}")
            return timezone.now()
    
    def should_throttle_notification(self, user, notification_type):
        """
        Check if a notification should be throttled based on recent notifications.
        
        Args:
            user: The user to check
            notification_type: Type of notification to check
            
        Returns:
            True if notification should be throttled, False otherwise
        """
        # Define throttle limits by notification type (in minutes)
        throttle_limits = {
            'MESSAGE': 1,      # 1 minute between messages
            'PROPOSAL': 5,     # 5 minutes between proposals
            'AWARD': 1,         # 1 minute between awards
            'SESSION': 2,        # 2 minutes between sessions
            'REVIEW': 5,        # 5 minutes between reviews
            'PAYMENT': 1,        # 1 minute between payments
            'SYSTEM': 10,        # 10 minutes between system notifications
        }
        
        limit = throttle_limits.get(notification_type, 5)  # Default 5 minutes
        
        # Check for recent notifications of the same type
        since = timezone.now() - timedelta(minutes=limit)
        recent_count = Notification.objects.filter(
            recipient=user,
            notification_type=notification_type,
            created_at__gte=since
        ).count()
        
        return recent_count > 0
    
    def can_send_notification_now(self, user, notification_type, priority='medium'):
        """
        Check if a notification can be sent now based on all timing rules.
        
        Args:
            user: The user to send notification to
            notification_type: Type of notification
            priority: Priority of the notification
            
        Returns:
            tuple: (can_send, reason, next_available_time)
        """
        # Check if it's quiet hours
        if self.is_quiet_hours(user) and priority.lower() != 'urgent':
            next_time = self.get_next_available_time(user, priority)
            return (False, "Quiet hours", next_time)
        
        # Check if notification should be throttled
        if self.should_throttle_notification(user, notification_type):
            return (False, "Throttled", timezone.now() + timedelta(minutes=5))
        
        return (True, None, None)
    
    def schedule_with_timing_controls(self, notification, user=None, priority='medium'):
        """
        Schedule a notification with all timing controls applied.
        
        Args:
            notification: The notification to schedule
            user: The user to send notification to (defaults to notification.recipient)
            priority: Priority of the notification
            
        Returns:
            The scheduled notification
        """
        if not user:
            user = notification.recipient
        
        # Check if we can send now
        can_send, reason, next_time = self.can_send_notification_now(
            user, notification.notification_type, priority
        )
        
        if not can_send and next_time:
            # Schedule for the next available time
            notification.scheduled_at = next_time
            notification.save(update_fields=['scheduled_at'])
            logger.info(f"Notification {notification.pk} scheduled for {next_time} due to {reason}")
        
        return notification


class NotificationFrequencyController:
    """
    Controls the frequency of notifications sent to users.
    """
    
    def __init__(self):
        pass
    
    def check_frequency_limits(self, user, notification_type):
        """
        Check if user has exceeded frequency limits for a notification type.
        
        Args:
            user: The user to check
            notification_type: Type of notification
            
        Returns:
            dict: {
                'allowed': bool,  # If notification is allowed
                'count': int,     # Current count
                'limit': int,     # Maximum allowed
                'reset_time': datetime  # When count resets
            }
        """
        # Define frequency limits by notification type
        frequency_limits = {
            'MESSAGE': {'hourly': 20, 'daily': 100},
            'PROPOSAL': {'hourly': 10, 'daily': 50},
            'AWARD': {'hourly': 5, 'daily': 25},
            'SESSION': {'hourly': 10, 'daily': 50},
            'REVIEW': {'hourly': 10, 'daily': 50},
            'PAYMENT': {'hourly': 20, 'daily': 100},
            'SYSTEM': {'hourly': 5, 'daily': 25},
        }
        
        limits = frequency_limits.get(notification_type, {'hourly': 10, 'daily': 50})
        
        # Check hourly limit
        hour_ago = timezone.now() - timedelta(hours=1)
        hourly_count = Notification.objects.filter(
            recipient=user,
            notification_type=notification_type,
            created_at__gte=hour_ago
        ).count()
        
        if hourly_count >= limits['hourly']:
            return {
                'allowed': False,
                'count': hourly_count,
                'limit': limits['hourly'],
                'reset_time': timezone.now() + timedelta(hours=1),
                'period': 'hourly'
            }
        
        # Check daily limit
        day_ago = timezone.now() - timedelta(days=1)
        daily_count = Notification.objects.filter(
            recipient=user,
            notification_type=notification_type,
            created_at__gte=day_ago
        ).count()
        
        if daily_count >= limits['daily']:
            return {
                'allowed': False,
                'count': daily_count,
                'limit': limits['daily'],
                'reset_time': timezone.now() + timedelta(days=1),
                'period': 'daily'
            }
        
        return {
            'allowed': True,
            'count': daily_count,
            'limit': limits['daily'],
            'reset_time': None,
            'period': None
        }


# Global instances
notification_scheduler = NotificationScheduler()
frequency_controller = NotificationFrequencyController()


def schedule_notification(notification, scheduled_at=None, delay_minutes=None):
    """
    Convenience function to schedule a notification.
    """
    return notification_scheduler.schedule_notification(
        notification, scheduled_at, delay_minutes
    )


def can_send_notification_now(user, notification_type, priority='medium'):
    """
    Convenience function to check if notification can be sent now.
    """
    return notification_scheduler.can_send_notification_now(
        user, notification_type, priority
    )


def check_frequency_limits(user, notification_type):
    """
    Convenience function to check frequency limits.
    """
    return frequency_controller.check_frequency_limits(user, notification_type)