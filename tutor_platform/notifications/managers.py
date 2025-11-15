from django.db import models
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class NotificationManager(models.Manager):
    """Custom manager for Notification model with efficient queries"""
    
    def get_unread_count(self, user):
        """Get unread notification count for user with caching"""
        cache_key = f"unread_notifications_{user.id}"
        count = cache.get(cache_key)
        
        if count is None:
            count = self.filter(
                recipient=user,
                is_read=False
            ).count()
            cache.set(cache_key, count, timeout=300)  # Cache for 5 minutes
        
        return count
    
    def get_recent_notifications(self, user, limit=10):
        """Get recent notifications for user"""
        return self.filter(
            recipient=user
        ).select_related(
            'sender', 'content_type'
        ).order_by('-created_at')[:limit]
    
    def get_filtered_notifications(self, user, filters=None):
        """Get filtered notifications based on provided filters"""
        queryset = self.filter(recipient=user)
        
        if not filters:
            filters = {}
        
        # Filter by read status
        read_status = filters.get('read_status')
        if read_status == 'read':
            queryset = queryset.filter(is_read=True)
        elif read_status == 'unread':
            queryset = queryset.filter(is_read=False)
        
        # Filter by type
        notification_type = filters.get('notification_type')
        if notification_type:
            queryset = queryset.filter(notification_type=notification_type)
        
        # Filter by priority
        priority = filters.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by date range
        date_from = filters.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        date_to = filters.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Search
        search = filters.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search)
            )
        
        return queryset.select_related('sender', 'content_type').order_by('-created_at')
    
    def mark_all_as_read(self, user):
        """Mark all notifications as read for user"""
        count = self.filter(
            recipient=user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        # Clear cache
        cache.delete(f"unread_notifications_{user.id}")
        return count
    
    def get_notification_stats(self, user):
        """Get notification statistics for user"""
        stats = self.filter(recipient=user).aggregate(
            total_count=Count('id'),
            unread_count=Count('id', filter=Q(is_read=False)),
            read_count=Count('id', filter=Q(is_read=True)),
        )
        
        # Add counts by type
        type_stats = self.filter(recipient=user).values(
            'notification_type'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        stats['by_type'] = {item['notification_type']: item['count'] for item in type_stats}
        
        return stats
    
    def get_expired_notifications(self):
        """Get expired notifications"""
        return self.filter(
            expires_at__lt=timezone.now()
        )
    
    def get_notifications_for_digest(self, user, frequency):
        """Get notifications for digest based on frequency"""
        now = timezone.now()
        
        if frequency == 'hourly':
            cutoff = now - timezone.timedelta(hours=1)
        elif frequency == 'daily':
            cutoff = now - timezone.timedelta(days=1)
        elif frequency == 'weekly':
            cutoff = now - timezone.timedelta(weeks=1)
        else:
            return self.none()
        
        return self.filter(
            recipient=user,
            created_at__gte=cutoff,
            is_read=False
        ).exclude(
            notification_type='SYSTEM'  # Exclude system notifications from digest
        )
    
    def bulk_create_with_delivery(self, notifications):
        """Bulk create notifications with delivery tracking"""
        created_notifications = self.bulk_create(notifications)
        
        # Create delivery records for each notification
        deliveries = []
        for notification in created_notifications:
            deliveries.append(
                NotificationDelivery(
                    notification=notification,
                    channel='IN_APP',
                    status='DELIVERED',
                    delivered_at=timezone.now()
                )
            )
        
        NotificationDelivery.objects.bulk_create(deliveries)
        return created_notifications


class EmailQueueManager(models.Manager):
    """Custom manager for EmailQueue model with batch processing"""
    
    def get_pending_emails(self, limit=50):
        """Get pending emails for processing"""
        return self.filter(
            status=self.model.Status.PENDING
        ).select_related(
            'recipient', 'notification'
        ).order_by('created_at')[:limit]
    
    def get_retry_emails(self, limit=50):
        """Get emails that need to be retried"""
        return self.filter(
            status=self.model.Status.FAILED,
            retry_count__lt=models.F('max_retries'),
            next_retry_at__lte=timezone.now()
        ).select_related(
            'recipient', 'notification'
        ).order_by('next_retry_at')[:limit]
    
    def get_emails_for_processing(self, limit=50, include_retry=False):
        """Get emails that need to be processed"""
        emails = self.get_pending_emails(limit)
        
        if include_retry:
            retry_emails = self.get_retry_emails(limit - len(emails))
            emails = list(emails) + list(retry_emails)
        
        return emails
    
    def get_failed_emails(self, days=7):
        """Get emails that failed in the last N days"""
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.filter(
            status=self.model.Status.FAILED,
            updated_at__gte=cutoff
        ).select_related('recipient')
    
    def get_processing_stats(self):
        """Get email processing statistics"""
        stats = self.aggregate(
            total=Count('id'),
            pending=Count('id', filter=Q(status='PENDING')),
            processing=Count('id', filter=Q(status='PROCESSING')),
            sent=Count('id', filter=Q(status='SENT')),
            failed=Count('id', filter=Q(status='FAILED')),
        )
        
        # Add retry stats
        retry_stats = self.filter(
            retry_count__gt=0
        ).aggregate(
            total_retries=Sum('retry_count'),
            avg_retries=models.Avg('retry_count')
        )
        
        stats.update(retry_stats)
        return stats
    
    def cleanup_old_sent_emails(self, days=30):
        """Clean up old sent emails"""
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.filter(
            status=self.model.Status.SENT,
            sent_at__lt=cutoff
        ).delete()
    
    def mark_emails_as_processing(self, email_ids):
        """Mark emails as processing to avoid duplicate processing"""
        return self.filter(
            id__in=email_ids,
            status=self.model.Status.PENDING
        ).update(
            status=self.model.Status.PROCESSING
        )
    
    def get_emails_by_priority(self, limit=50):
        """Get emails ordered by priority"""
        # This would require adding a priority field to EmailQueue
        return self.filter(
            status=self.model.Status.PENDING
        ).select_related(
            'recipient', 'notification'
        ).order_by('-created_at')[:limit]


class PushNotificationManager(models.Manager):
    """Custom manager for PushMessage model with device targeting"""
    
    def get_pending_push_messages(self, limit=100):
        """Get pending push messages"""
        return self.filter(
            status=self.model.Status.PENDING
        ).select_related(
            'notification', 'device', 'device__user'
        ).order_by('created_at')[:limit]
    
    def get_messages_for_device(self, device, limit=10):
        """Get recent messages for a specific device"""
        return self.filter(
            device=device
        ).select_related(
            'notification'
        ).order_by('-created_at')[:limit]
    
    def get_failed_messages(self, hours=24):
        """Get failed messages from the last N hours"""
        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        return self.filter(
            status=self.model.Status.FAILED,
            failed_at__gte=cutoff
        ).select_related('device', 'notification')
    
    def get_delivery_stats(self, hours=24):
        """Get push delivery statistics"""
        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        
        stats = self.filter(
            created_at__gte=cutoff
        ).aggregate(
            total=Count('id'),
            sent=Count('id', filter=Q(status='SENT')),
            delivered=Count('id', filter=Q(status='DELIVERED')),
            failed=Count('id', filter=Q(status='FAILED')),
        )
        
        # Add device type breakdown
        device_stats = self.filter(
            created_at__gte=cutoff
        ).values(
            'device__device_type'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        stats['by_device_type'] = {item['device__device_type']: item['count'] for item in device_stats}
        
        return stats
    
    def create_push_for_notification(self, notification, devices):
        """Create push messages for a notification across multiple devices"""
        messages = []
        
        for device in devices:
            if not device.is_active:
                continue
                
            messages.append(
                self.model(
                    notification=notification,
                    device=device,
                    title=notification.title,
                    body=notification.content,
                    data={
                        'notification_id': str(notification.id),
                        'action_url': notification.action_url,
                        'type': notification.notification_type
                    }
                )
            )
        
        return self.bulk_create(messages)
    
    def get_active_devices_for_user(self, user):
        """Get all active devices for a user"""
        return PushDevice.objects.filter(
            user=user,
            is_active=True
        ).order_by('-last_used_at')
    
    def cleanup_old_messages(self, days=7):
        """Clean up old delivered messages"""
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.filter(
            status__in=['DELIVERED', 'FAILED'],
            created_at__lt=cutoff
        ).delete()
    
    def retry_failed_messages(self, max_retries=3):
        """Retry failed messages that haven't exceeded max retries"""
        return self.filter(
            status=self.model.Status.FAILED,
            retry_count__lt=max_retries
        ).update(
            status=self.model.Status.PENDING,
            retry_count=models.F('retry_count') + 1
        )


# Import models here to avoid circular imports
from .models import Notification, NotificationDelivery, EmailQueue, PushDevice, PushMessage