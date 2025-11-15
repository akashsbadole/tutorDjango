"""
Notification expiration and cleanup utilities.
This module provides functionality to:
1. Handle notification expiration
2. Clean up old notifications
3. Manage notification retention policies
4. Auto-delete based on user preferences
"""

from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
import logging

from .models import (
    Notification, NotificationDelivery, NotificationDigest, 
    NotificationPreference, EmailQueue, PushMessage
)

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationCleaner:
    """
    Handles cleanup and expiration of notifications.
    
    This class provides methods to:
    1. Process expired notifications
    2. Clean up old notifications based on user preferences
    3. Clean up old delivery records
    4. Clean up old email queue entries
    5. Clean up old push messages
    """
    
    def __init__(self):
        self.default_retention_days = 30  # Default retention period
    
    def process_expired_notifications(self):
        """
        Process notifications that have expired.
        
        Expired notifications are marked as read and optionally deleted
        based on user preferences.
        """
        now = timezone.now()
        expired_notifications = Notification.objects.filter(
            expires_at__lte=now,
            is_read=False
        )
        
        count = expired_notifications.count()
        if count > 0:
            logger.info(f"Processing {count} expired notifications")
            
            with transaction.atomic():
                for notification in expired_notifications:
                    # Mark as read
                    notification.is_read = True
                    notification.read_at = now
                    notification.save(update_fields=['is_read', 'read_at'])
                    
                    # Log expiration
                    logger.info(f"Notification {notification.pk} expired and marked as read")
        
        return count
    
    def cleanup_old_notifications(self, days=None):
        """
        Clean up old notifications based on retention policy.
        
        Args:
            days: Number of days to retain notifications (overrides default)
            
        Returns:
            dict: Statistics about cleanup operation
        """
        if days is None:
            days = self.default_retention_days
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Get all notifications older than cutoff date
        old_notifications = Notification.objects.filter(
            created_at__lt=cutoff_date
        )
        
        stats = {
            'total': old_notifications.count(),
            'deleted': 0,
            'errors': 0
        }
        
        if stats['total'] == 0:
            logger.info("No old notifications to clean up")
            return stats
        
        logger.info(f"Cleaning up {stats['total']} notifications older than {days} days")
        
        # Process in batches to avoid memory issues
        batch_size = 1000
        processed = 0
        
        while processed < stats['total']:
            batch = old_notifications[:batch_size]
            
            with transaction.atomic():
                for notification in batch:
                    try:
                        # Check user's auto-delete preference
                        try:
                            preference = NotificationPreference.objects.get(user=notification.recipient)
                            
                            # Skip if user has auto-delete disabled
                            if not preference.auto_delete_read:
                                processed += 1
                                continue
                            
                            # Use user's preferred retention period
                            user_days = preference.auto_delete_days
                            user_cutoff = timezone.now() - timedelta(days=user_days)
                            
                            # Only delete if older than user's preference
                            if notification.created_at < user_cutoff:
                                notification.delete()
                                stats['deleted'] += 1
                        except NotificationPreference.DoesNotExist:
                            # Use default retention period
                            if notification.created_at < cutoff_date:
                                notification.delete()
                                stats['deleted'] += 1
                        
                        processed += 1
                        
                    except Exception as e:
                        logger.error(f"Error deleting notification {notification.pk}: {e}")
                        stats['errors'] += 1
                        processed += 1
            
            # Refresh the queryset
            old_notifications = Notification.objects.filter(
                created_at__lt=cutoff_date
            )
        
        logger.info(f"Cleaned up {stats['deleted']} notifications, {stats['errors']} errors")
        return stats
    
    def cleanup_delivery_records(self, days=90):
        """
        Clean up old delivery records.
        
        Args:
            days: Number of days to retain delivery records
            
        Returns:
            dict: Statistics about cleanup operation
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        old_deliveries = NotificationDelivery.objects.filter(
            created_at__lt=cutoff_date
        )
        
        count = old_deliveries.count()
        if count > 0:
            logger.info(f"Cleaning up {count} old delivery records")
            old_deliveries.delete()
        
        return {'deleted': count}
    
    def cleanup_email_queue(self, days=7):
        """
        Clean up old email queue entries.
        
        Args:
            days: Number of days to retain queue entries
            
        Returns:
            dict: Statistics about cleanup operation
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        old_entries = EmailQueue.objects.filter(
            created_at__lt=cutoff_date
        )
        
        stats = {
            'total': old_entries.count(),
            'deleted': 0,
            'failed': 0
        }
        
        if stats['total'] > 0:
            logger.info(f"Cleaning up {stats['total']} old email queue entries")
            
            with transaction.atomic():
                for entry in old_entries:
                    try:
                        # Don't delete pending entries
                        if entry.status == 'PENDING':
                            continue
                        
                        entry.delete()
                        stats['deleted'] += 1
                        
                        if entry.status == 'FAILED':
                            stats['failed'] += 1
                            
                    except Exception as e:
                        logger.error(f"Error deleting email queue entry {entry.pk}: {e}")
        
        logger.info(f"Cleaned up {stats['deleted']} email queue entries")
        return stats
    
    def cleanup_push_messages(self, days=30):
        """
        Clean up old push message records.
        
        Args:
            days: Number of days to retain push messages
            
        Returns:
            dict: Statistics about cleanup operation
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        old_messages = PushMessage.objects.filter(
            created_at__lt=cutoff_date
        )
        
        count = old_messages.count()
        if count > 0:
            logger.info(f"Cleaning up {count} old push message records")
            old_messages.delete()
        
        return {'deleted': count}
    
    def cleanup_digests(self, days=30):
        """
        Clean up old digest records.
        
        Args:
            days: Number of days to retain digests
            
        Returns:
            dict: Statistics about cleanup operation
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        old_digests = NotificationDigest.objects.filter(
            created_at__lt=cutoff_date
        )
        
        count = old_digests.count()
        if count > 0:
            logger.info(f"Cleaning up {count} old digest records")
            old_digests.delete()
        
        return {'deleted': count}
    
    def run_full_cleanup(self, notification_days=None, delivery_days=90, email_days=7, push_days=30):
        """
        Run a complete cleanup of all notification-related data.
        
        Args:
            notification_days: Days to retain notifications
            delivery_days: Days to retain delivery records
            email_days: Days to retain email queue entries
            push_days: Days to retain push messages
            
        Returns:
            dict: Combined statistics of all cleanup operations
        """
        logger.info("Starting full notification cleanup")
        
        results = {
            'expired_notifications': self.process_expired_notifications(),
            'old_notifications': self.cleanup_old_notifications(notification_days),
            'delivery_records': self.cleanup_delivery_records(delivery_days),
            'email_queue': self.cleanup_email_queue(email_days),
            'push_messages': self.cleanup_push_messages(push_days),
            'digests': self.cleanup_digests()
        }
        
        total_deleted = (
            results['old_notifications']['deleted'] +
            results['delivery_records']['deleted'] +
            results['email_queue']['deleted'] +
            results['push_messages']['deleted'] +
            results['digests']['deleted']
        )
        
        logger.info(f"Full cleanup completed. Total items deleted: {total_deleted}")
        return results


class NotificationExpirer:
    """
    Handles automatic expiration of notifications based on rules.
    """
    
    def __init__(self):
        self.expiration_rules = {
            'SYSTEM': 24 * 7,      # 1 week for system notifications
            'MESSAGE': 24 * 30,     # 30 days for messages
            'PROPOSAL': 24 * 14,    # 2 weeks for proposals
            'AWARD': 24 * 30,        # 30 days for awards
            'SESSION': 24 * 7,        # 1 week for sessions
            'REVIEW': 24 * 14,        # 2 weeks for reviews
            'PAYMENT': 24 * 30,       # 30 days for payments
        }
    
    def set_expiration_for_notification(self, notification):
        """
        Set expiration date for a notification based on its type.
        
        Args:
            notification: The notification to set expiration for
            
        Returns:
            The notification with updated expiration date
        """
        if notification.expires_at:
            return notification
        
        # Get expiration hours for notification type
        hours = self.expiration_rules.get(
            notification.notification_type, 
            24 * 30  # Default to 30 days
        )
        
        # Set expiration date
        notification.expires_at = timezone.now() + timedelta(hours=hours)
        notification.save(update_fields=['expires_at'])
        
        logger.info(f"Set expiration for notification {notification.pk}: {hours} hours")
        return notification
    
    def process_expiring_notifications(self, hours_ahead=24):
        """
        Process notifications that will expire soon.
        
        Args:
            hours_ahead: How many hours ahead to check for expiring notifications
            
        Returns:
            list: Notifications that will expire soon
        """
        soon = timezone.now() + timedelta(hours=hours_ahead)
        
        expiring = Notification.objects.filter(
            expires_at__lte=soon,
            expires_at__gt=timezone.now(),
            is_read=False
        )
        
        logger.info(f"Found {expiring.count()} notifications expiring in next {hours_ahead} hours")
        return list(expiring)
    
    def send_expiration_warnings(self):
        """
        Send warning notifications for notifications about to expire.
        """
        expiring = self.process_expiring_notifications(24)
        
        for notification in expiring:
            # Create a warning notification
            warning = Notification.objects.create(
                recipient=notification.recipient,
                title="Notification Expiring Soon",
                content=f"The notification '{notification.title}' will expire in 24 hours.",
                notification_type='SYSTEM',
                priority='LOW',
                related_object=notification
            )
            
            # Send the warning
            warning.send_email_notification()
            warning.send_push_notification()
        
        return len(expiring)


# Global instances
notification_cleaner = NotificationCleaner()
notification_expirer = NotificationExpirer()


def process_expired_notifications():
    """Convenience function to process expired notifications."""
    return notification_cleaner.process_expired_notifications()


def cleanup_old_notifications(days=None):
    """Convenience function to clean up old notifications."""
    return notification_cleaner.cleanup_old_notifications(days)


def run_full_cleanup(notification_days=None, delivery_days=90, email_days=7, push_days=30):
    """Convenience function to run full cleanup."""
    return notification_cleaner.run_full_cleanup(
        notification_days, delivery_days, email_days, push_days
    )


def set_expiration_for_notification(notification):
    """Convenience function to set expiration for a notification."""
    return notification_expirer.set_expiration_for_notification(notification)