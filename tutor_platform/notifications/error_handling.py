"""
Error handling utilities for notification delivery failures.
This module provides functionality to:
1. Handle delivery errors gracefully
2. Implement retry logic with exponential backoff
3. Track error patterns
4. Provide fallback mechanisms
5. Generate error reports
"""

from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.core.mail import mail_admins
import logging

from .models import (
    Notification, NotificationDelivery, EmailQueue, PushMessage
)

logger = logging.getLogger(__name__)


class NotificationErrorHandler:
    """
    Handles errors in notification delivery.
    
    This class provides methods to:
    1. Process delivery errors
    2. Implement retry logic
    3. Track error patterns
    4. Provide fallback mechanisms
    5. Generate error reports
    """
    
    def __init__(self):
        self.error_patterns = {}
        self.retry_limits = {
            'email': 3,      # Max 3 retries for email
            'push': 2,       # Max 2 retries for push
            'sms': 2,        # Max 2 retries for SMS
            'in_app': 0,     # No retries for in-app
        }
    
    def handle_delivery_error(self, delivery, error_message, channel='email'):
        """
        Handle a delivery error with appropriate retry logic.
        
        Args:
            delivery: The delivery record that failed
            error_message: The error message
            channel: The delivery channel
            
        Returns:
            bool: True if error was handled, False otherwise
        """
        # Log the error
        logger.error(f"Delivery error for {delivery.notification.pk} via {channel}: {error_message}")
        
        # Update delivery record
        delivery.status = 'failed'
        delivery.failed_at = timezone.now()
        delivery.failure_reason = error_message
        delivery.save(update_fields=['status', 'failed_at', 'failure_reason'])
        
        # Check if we should retry
        if self.should_retry(delivery, channel):
            # Schedule retry with exponential backoff
            self.schedule_retry(delivery, channel)
            return True
        
        # Track error pattern
        self.track_error_pattern(error_message, channel)
        
        # Try fallback mechanism
        self.try_fallback(delivery.notification, channel)
        
        # Notify admins of critical errors
        if self.is_critical_error(error_message):
            self.notify_admins(delivery.notification, error_message, channel)
        
        return True
    
    def should_retry(self, delivery, channel):
        """
        Determine if a failed delivery should be retried.
        
        Args:
            delivery: The delivery record
            channel: The delivery channel
            
        Returns:
            bool: True if should retry, False otherwise
        """
        # Check retry limit
        max_retries = self.retry_limits.get(channel, 0)
        if delivery.retry_count >= max_retries:
            return False
        
        # Check if error is retryable
        error_message = delivery.failure_reason or ""
        non_retryable_errors = [
            'invalid recipient',
            'user unsubscribed',
            'blocked',
            'permanent failure'
        ]
        
        for error in non_retryable_errors:
            if error.lower() in error_message.lower():
                return False
        
        return True
    
    def schedule_retry(self, delivery, channel):
        """
        Schedule a retry for a failed delivery.
        
        Args:
            delivery: The delivery record to retry
            channel: The delivery channel
        """
        # Calculate exponential backoff delay
        delay_minutes = 2 ** delivery.retry_count  # 2^retry_count minutes
        max_delay = 60 * 24  # Max 24 hours
        delay_minutes = min(delay_minutes, max_delay)
        
        retry_at = timezone.now() + timedelta(minutes=delay_minutes)
        
        # Update delivery record
        delivery.retry_count += 1
        delivery.next_retry_at = retry_at
        delivery.status = 'pending'
        delivery.save(update_fields=['retry_count', 'next_retry_at', 'status'])
        
        logger.info(f"Scheduled retry #{delivery.retry_count} for {delivery.notification.pk} at {retry_at}")
        
        # For email, create/update queue entry
        if channel == 'email':
            try:
                email_queue, created = EmailQueue.objects.get_or_create(
                    notification=delivery.notification,
                    recipient=delivery.notification.recipient,
                    subject=delivery.notification.title,
                    body=delivery.notification.content,
                    defaults={
                        'status': 'PENDING',
                        'retry_count': delivery.retry_count,
                        'next_retry_at': retry_at,
                        'error_message': delivery.failure_reason
                    }
                )
                
                if not created:
                    email_queue.retry_count = delivery.retry_count
                    email_queue.next_retry_at = retry_at
                    email_queue.status = 'PENDING'
                    email_queue.error_message = delivery.failure_reason
                    email_queue.save(update_fields=[
                        'retry_count', 'next_retry_at', 'status', 'error_message'
                    ])
            except Exception as e:
                logger.error(f"Error creating email queue entry: {e}")
        
        # For push, create/update push message
        elif channel == 'push':
            try:
                # Get user's active devices
                devices = delivery.notification.recipient.push_devices.filter(is_active=True)
                
                for device in devices:
                    push_message, created = PushMessage.objects.get_or_create(
                        notification=delivery.notification,
                        device=device,
                        defaults={
                            'title': delivery.notification.title,
                            'body': delivery.notification.content,
                            'status': 'PENDING',
                            'retry_count': delivery.retry_count,
                            'failure_reason': delivery.failure_reason
                        }
                    )
                    
                    if not created:
                        push_message.retry_count = delivery.retry_count
                        push_message.status = 'PENDING'
                        push_message.failure_reason = delivery.failure_reason
                        push_message.save(update_fields=[
                            'retry_count', 'status', 'failure_reason'
                        ])
            except Exception as e:
                logger.error(f"Error creating push message entry: {e}")
    
    def track_error_pattern(self, error_message, channel):
        """
        Track error patterns to identify common issues.
        
        Args:
            error_message: The error message
            channel: The delivery channel
        """
        today = timezone.now().date()
        
        # Initialize pattern tracking for today
        if today not in self.error_patterns:
            self.error_patterns[today] = {}
        
        if channel not in self.error_patterns[today]:
            self.error_patterns[today][channel] = {}
        
        # Extract error type (simplified)
        error_type = self.classify_error(error_message)
        
        # Update pattern count
        if error_type not in self.error_patterns[today][channel]:
            self.error_patterns[today][channel][error_type] = 0
        
        self.error_patterns[today][channel][error_type] += 1
        
        # Log significant patterns
        if self.error_patterns[today][channel][error_type] >= 10:
            logger.warning(
                f"High error pattern detected: {error_type} "
                f"({self.error_patterns[today][channel][error_type]} times) "
                f"for {channel} today"
            )
    
    def classify_error(self, error_message):
        """
        Classify an error message into a category.
        
        Args:
            error_message: The error message to classify
            
        Returns:
            str: The error category
        """
        error_message = error_message.lower()
        
        # Define error categories
        categories = {
            'authentication': ['auth', 'login', 'credential', 'unauthorized'],
            'network': ['timeout', 'connection', 'network', 'dns'],
            'recipient': ['invalid', 'unknown', 'bounced', 'rejected'],
            'rate_limit': ['rate', 'limit', 'throttle', 'quota'],
            'content': ['format', 'invalid', 'missing', 'malformed'],
            'server': ['internal', 'error', 'exception', 'crash']
        }
        
        # Find matching category
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in error_message:
                    return category
        
        return 'other'
    
    def try_fallback(self, notification, failed_channel):
        """
        Try a fallback delivery method.
        
        Args:
            notification: The notification that failed
            failed_channel: The channel that failed
        """
        # Define fallback priorities
        fallback_order = {
            'email': ['push', 'in_app'],
            'push': ['email', 'in_app'],
            'sms': ['email', 'push'],
        }
        
        # Try fallback channels in order
        for fallback_channel in fallback_order.get(failed_channel, []):
            try:
                if fallback_channel == 'email':
                    notification.send_email_notification(force_send=True)
                elif fallback_channel == 'push':
                    notification.send_push_notification(force_send=True)
                elif fallback_channel == 'in_app':
                    # In-app is always available, no action needed
                    pass
                
                logger.info(f"Fallback delivery successful via {fallback_channel} for {notification.pk}")
                return True
                
            except Exception as e:
                logger.error(f"Fallback via {fallback_channel} failed: {e}")
                continue
        
        logger.warning(f"All fallback methods failed for {notification.pk}")
        return False
    
    def is_critical_error(self, error_message):
        """
        Determine if an error is critical.
        
        Args:
            error_message: The error message
            
        Returns:
            bool: True if error is critical
        """
        critical_indicators = [
            'database error',
            'configuration error',
            'authentication failed',
            'service unavailable',
            'critical'
        ]
        
        error_message = error_message.lower()
        for indicator in critical_indicators:
            if indicator in error_message:
                return True
        
        return False
    
    def notify_admins(self, notification, error_message, channel):
        """
        Notify administrators of critical errors.
        
        Args:
            notification: The notification that failed
            error_message: The error message
            channel: The delivery channel
        """
        subject = f"Critical Notification Delivery Error: {channel}"
        
        message = f"""
        A critical error occurred while delivering a notification:
        
        Notification ID: {notification.pk}
        Recipient: {notification.recipient.get_full_name() or notification.recipient.username}
        Channel: {channel}
        Error: {error_message}
        Time: {timezone.now()}
        
        Please investigate this issue immediately.
        """
        
        try:
            mail_admins(subject, message)
            logger.info(f"Admin notification sent for critical error on {notification.pk}")
        except Exception as e:
            logger.error(f"Failed to notify admins: {e}")
    
    def generate_error_report(self, days=7):
        """
        Generate a report of recent errors.
        
        Args:
            days: Number of days to include in report
            
        Returns:
            dict: Error report data
        """
        since = timezone.now() - timedelta(days=days)
        
        # Get failed deliveries
        failed_deliveries = NotificationDelivery.objects.filter(
            failed_at__gte=since,
            status='failed'
        )
        
        # Group by channel and error type
        channel_stats = {}
        error_types = {}
        
        for delivery in failed_deliveries:
            # Channel stats
            channel = delivery.channel
            if channel not in channel_stats:
                channel_stats[channel] = {'total': 0, 'retries': 0}
            
            channel_stats[channel]['total'] += 1
            channel_stats[channel]['retries'] += delivery.retry_count
            
            # Error type classification
            error_type = self.classify_error(delivery.failure_reason or "")
            if error_type not in error_types:
                error_types[error_type] = 0
            
            error_types[error_type] += 1
        
        # Get most common errors
        top_errors = sorted(
            error_types.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            'period': f"Last {days} days",
            'total_failures': failed_deliveries.count(),
            'by_channel': channel_stats,
            'by_error_type': error_types,
            'top_errors': top_errors,
            'generated_at': timezone.now()
        }
    
    def get_error_trends(self, days=30):
        """
        Analyze error trends over time.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            list: Daily error counts
        """
        since = timezone.now() - timedelta(days=days)
        
        # Get daily error counts
        from django.db.models.functions import TruncDate
        from django.db.models import Count
        
        daily_errors = NotificationDelivery.objects.filter(
            failed_at__gte=since,
            status='failed'
        ).annotate(
            date=TruncDate('failed_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return list(daily_errors)


# Global instance
error_handler = NotificationErrorHandler()


def handle_delivery_error(delivery, error_message, channel='email'):
    """Convenience function to handle delivery errors."""
    return error_handler.handle_delivery_error(delivery, error_message, channel)


def generate_error_report(days=7):
    """Convenience function to generate error report."""
    return error_handler.generate_error_report(days)