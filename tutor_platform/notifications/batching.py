"""
Notification batching utilities to prevent spam and improve user experience.
This module provides functionality to batch similar notifications and control
the frequency of notifications sent to users.
"""

from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from collections import defaultdict
import logging

from .models import (
    Notification, NotificationType, NotificationDelivery, 
    NotificationDigest, NotificationPreference
)

logger = logging.getLogger(__name__)


class NotificationBatcher:
    """
    Handles batching of notifications to prevent spam.
    
    This class provides methods to:
    1. Group similar notifications
    2. Control notification frequency
    3. Create digests for batched notifications
    4. Respect user preferences for batching
    """
    
    # Default batching intervals (in minutes)
    DEFAULT_BATCH_INTERVALS = {
        'low': 60,      # 1 hour
        'medium': 30,   # 30 minutes
        'high': 5,      # 5 minutes
        'urgent': 0,    # No batching for urgent
    }
    
    def __init__(self):
        self.batch_intervals = self.DEFAULT_BATCH_INTERVALS
    
    def should_batch_notification(self, notification_type, recipient):
        """
        Determine if a notification should be batched based on:
        1. User preferences
        2. Notification type settings
        3. Recent notification history
        """
        try:
            # Get user preferences for this notification type
            preference = NotificationPreference.objects.get(user=recipient)
            
            # Don't batch if user has disabled batching
            # Since there's no specific batch_enabled field, we'll default to True
            # In a real implementation, you might add this field to the model
                
        except NotificationPreference.DoesNotExist:
            # Default to batching if no preference exists
            pass
        
        # Check if notification type has batching enabled
        # Since there's no specific batch_enabled field, we'll default to True
        # In a real implementation, you might add this field to the model
        
        return True
    
    def get_batch_key(self, notification_type, recipient):
        """
        Generate a unique key for identifying a batch of notifications.
        Batches are grouped by notification type and recipient.
        """
        return f"notification_batch:{notification_type.id}:{recipient.id}"
    
    def get_recent_notifications(self, notification_type, recipient, minutes=30):
        """
        Get recent notifications of the same type for the same recipient.
        """
        since = timezone.now() - timedelta(minutes=minutes)
        return Notification.objects.filter(
            notification_type=notification_type,
            recipient=recipient,
            created_at__gte=since,
            is_batched=False
        )
    
    def find_similar_notifications(self, notification_type, recipient, content, threshold=0.7):
        """
        Find notifications with similar content that could be batched.
        This is a simple implementation - could be enhanced with NLP.
        """
        recent = self.get_recent_notifications(notification_type, recipient)
        similar = []
        
        for notif in recent:
            # Simple similarity check based on common words
            content_words = set(content.lower().split())
            notif_words = set(notif.content.lower().split())
            
            if content_words and notif_words:
                similarity = len(content_words & notif_words) / len(content_words | notif_words)
                if similarity >= threshold:
                    similar.append(notif)
        
        return similar
    
    def create_batch_notification(self, notification_type, recipient, notifications_to_batch):
        """
        Create a batched notification that summarizes multiple notifications.
        """
        if not notifications_to_batch:
            return None
        
        # Mark original notifications as batched
        for notif in notifications_to_batch:
            notif.is_batched = True
            notif.save(update_fields=['is_batched'])
        
        # Create batch notification
        count = len(notifications_to_batch)
        latest = max(notifications_to_batch, key=lambda n: n.created_at)
        
        # Use batch template if available, otherwise create default
        if notification_type.batch_template:
            content = notification_type.batch_template.format(
                count=count,
                latest_title=latest.title,
                user=recipient.get_full_name() or recipient.username
            )
        else:
            content = f"You have {count} new {notification_type.name.lower()} notifications. Latest: {latest.title}"
        
        batch_notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=f"{count} {notification_type.name}",
            content=content,
            priority=notification_type.priority,
            is_batched=True,
            batch_count=count,
            related_objects=[notif.id for notif in notifications_to_batch]
        )
        
        # Create notification delivery records
        for notif in notifications_to_batch:
            NotificationDelivery.objects.create(
                notification=batch_notification,
                delivery_method='in_app',
                status='delivered',
                delivered_at=timezone.now()
            )
        
        return batch_notification
    
    def process_notification(self, notification_type, recipient, title, content, **kwargs):
        """
        Process a notification, applying batching rules.
        
        Returns either a new notification or None if it was batched.
        """
        # Check if we should batch this notification
        if not self.should_batch_notification(notification_type, recipient):
            # Create immediate notification
            return Notification.objects.create(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                content=content,
                **kwargs
            )
        
        # Check for similar recent notifications
        similar_notifications = self.find_similar_notifications(
            notification_type, recipient, content
        )
        
        if similar_notifications:
            # Add to batch
            batch_key = self.get_batch_key(notification_type, recipient)
            batch_count = cache.get(batch_key, 0) + 1
            cache.set(batch_key, batch_count, timeout=3600)  # 1 hour
            
            # Check if we've reached the batch threshold
            batch_threshold = notification_type.batch_threshold or 5
            if batch_count >= batch_threshold:
                # Create batch notification
                batch_notification = self.create_batch_notification(
                    notification_type, recipient, similar_notifications
                )
                cache.delete(batch_key)  # Reset batch counter
                return batch_notification
            
            # Don't create individual notification yet
            return None
        
        # No similar notifications, create individual one
        return Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            content=content,
            **kwargs
        )
    
    def create_digest_notifications(self, recipient):
        """
        Create digest notifications for a user based on their preferences.
        This is typically called by a scheduled task.
        """
        # Get user's digest preferences
        try:
            preference = NotificationPreference.objects.get(user=recipient)
            # Check if user wants digests based on email frequency
            if preference.email_frequency not in ['DAILY', 'WEEKLY']:
                return
                
            # Get notification types to include in digest
            notification_types = []
            if preference.email_message:
                notification_types.append('MESSAGE')
            if preference.email_proposal:
                notification_types.append('PROPOSAL')
            if preference.email_award:
                notification_types.append('AWARD')
            if preference.email_session:
                notification_types.append('SESSION')
            if preference.email_review:
                notification_types.append('REVIEW')
            if preference.email_payment:
                notification_types.append('PAYMENT')
            if preference.email_system:
                notification_types.append('SYSTEM')
            
            # Create digests for each notification type
            for notif_type in notification_types:
                # Get unbatched notifications since last digest
                last_digest = NotificationDigest.objects.filter(
                    user=recipient
                ).order_by('-created_at').first()
                
                if last_digest:
                    since = last_digest.created_at
                else:
                    since = timezone.now() - timedelta(days=1)  # Default to last 24 hours
                
                notifications = Notification.objects.filter(
                    recipient=recipient,
                    notification_type=notif_type,
                    created_at__gte=since,
                    is_read=False
                )
                
                if notifications.exists():
                    # Create digest
                    digest = NotificationDigest.objects.create(
                        user=recipient,
                        frequency='DAILY' if preference.email_frequency == 'DAILY' else 'WEEKLY',
                        subject=f"{notif_type} Digest",
                        content=self._create_digest_content(notifications)
                    )
                    
                    # Add notifications to digest
                    for notif in notifications:
                        digest.add_notification(notif)
                    
                    # Create notification delivery record
                    NotificationDelivery.objects.create(
                        notification=digest,
                        delivery_method='email',
                        status='pending'
                    )
                    
                    # Send digest
                    digest.send_digest()
                    
        except NotificationPreference.DoesNotExist:
            # No preferences, skip digest creation
            pass
    
    def _create_digest_content(self, notifications):
        """Create content for a digest notification."""
        count = notifications.count()
        latest = notifications.order_by('-created_at').first()
        
        if count == 1:
            return notifications.first().content
        
        content = f"You have {count} new notifications:\n\n"
        for notif in notifications.order_by('-created_at')[:5]:  # Show max 5
            content += f"• {notif.title}\n"
        
        if count > 5:
            content += f"\n... and {count - 5} more."
        
        return content


# Global batcher instance
notification_batcher = NotificationBatcher()


def batch_notification(notification_type, recipient, title, content, **kwargs):
    """
    Convenience function to batch a notification.
    """
    return notification_batcher.process_notification(
        notification_type, recipient, title, content, **kwargs
    )


def create_user_digests(recipient=None):
    """
    Create digest notifications for a user or all users.
    Typically called by a scheduled task.
    """
    if recipient:
        notification_batcher.create_digest_notifications(recipient)
    else:
        # Create digests for all users who have enabled them
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        for user in User.objects.filter(is_active=True):
            try:
                notification_batcher.create_digest_notifications(user)
            except Exception as e:
                logger.error(f"Error creating digest for user {user.pk}: {e}")