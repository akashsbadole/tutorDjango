"""
Notification analytics and tracking utilities.
This module provides functionality to:
1. Track notification engagement
2. Analyze delivery performance
3. Generate analytics reports
4. Track conversion rates
5. Monitor user preferences
"""

from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q, F, Sum, Case, When, IntegerField
from django.db.models.functions import TruncDate, TruncHour
from django.contrib.auth import get_user_model
import json
import logging

from .models import (
    Notification, NotificationType, NotificationDelivery,
    NotificationPreference
)

# Import the model class with an alias to avoid name conflict
from .models import NotificationAnalytics as NotificationAnalyticsModel

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationTracker:
    """
    Tracks notification events and engagement.
    """
    
    def __init__(self):
        pass
    
    def track_notification_sent(self, notification, channel='in_app'):
        """
        Track when a notification is sent via a specific channel.
        """
        # Create delivery record
        delivery = NotificationDelivery.objects.create(
            notification=notification,
            channel=channel,
            status='sent',
            sent_at=timezone.now(),
            recipient_address=self._get_recipient_address(notification, channel)
        )
        
        # Update analytics
        self._update_analytics(notification, channel, 'sent')
        
        return delivery
    
    def track_notification_delivered(self, delivery, provider_response=None):
        """
        Track when a notification is successfully delivered.
        """
        delivery.status = 'delivered'
        delivery.delivered_at = timezone.now()
        if provider_response:
            delivery.provider_response = provider_response
        delivery.save(update_fields=['status', 'delivered_at', 'provider_response'])
        
        # Update analytics
        self._update_analytics(delivery.notification, delivery.channel, 'delivered')
        
        return delivery
    
    def track_notification_read(self, notification):
        """
        Track when a notification is read by the user.
        """
        if not notification.is_read:
            notification.mark_as_read()
        
        # Update analytics
        self._update_analytics(notification, 'in_app', 'read')
    
    def track_notification_clicked(self, notification, action_url=None):
        """
        Track when a user clicks on a notification.
        """
        # Store click event (could be enhanced with a separate model)
        click_data = {
            'notification_id': str(notification.id),
            'clicked_at': timezone.now().isoformat(),
            'action_url': action_url or notification.action_url
        }
        
        # Log click event
        logger.info(f"Notification clicked: {json.dumps(click_data)}")
        
        # Update analytics
        self._update_analytics(notification, 'in_app', 'clicked')
    
    def track_notification_failed(self, delivery, error_message):
        """
        Track when a notification delivery fails.
        """
        delivery.status = 'failed'
        delivery.failed_at = timezone.now()
        delivery.failure_reason = error_message
        delivery.save(update_fields=['status', 'failed_at', 'failure_reason'])
        
        # Update analytics
        self._update_analytics(delivery.notification, delivery.channel, 'failed')
        
        return delivery
    
    def _get_recipient_address(self, notification, channel):
        """Get the recipient address for a specific channel."""
        if channel == 'email':
            return notification.recipient.email
        elif channel == 'sms':
            # Assuming phone number is stored in user profile
            try:
                return notification.recipient.profile.phone_number
            except AttributeError:
                return None
        elif channel == 'push':
            # Get device token
            device = notification.recipient.push_devices.filter(is_active=True).first()
            return device.device_token if device else None
        else:
            return str(notification.recipient.pk)
    
    def _update_analytics(self, notification, channel, event_type):
        """Update analytics counters for a notification event."""
        today = timezone.now().date()
        
        # Get or create analytics record
        analytics, created = NotificationAnalyticsModel.objects.get_or_create(
            date=today,
            notification_type=notification.notification_type,
            defaults={
                'total_sent': 0,
                'email_sent': 0,
                'sms_sent': 0,
                'push_sent': 0,
                'total_delivered': 0,
                'email_delivered': 0,
                'sms_delivered': 0,
                'push_delivered': 0,
                'total_read': 0,
            }
        )
        
        # Update counters based on event type
        if event_type == 'sent':
            analytics.total_sent += 1
            if channel == 'email':
                analytics.email_sent += 1
            elif channel == 'sms':
                analytics.sms_sent += 1
            elif channel == 'push':
                analytics.push_sent += 1
        elif event_type == 'delivered':
            analytics.total_delivered += 1
            if channel == 'email':
                analytics.email_delivered += 1
            elif channel == 'sms':
                analytics.sms_delivered += 1
            elif channel == 'push':
                analytics.push_delivered += 1
        elif event_type == 'read':
            analytics.total_read += 1
        
        analytics.save()


class NotificationAnalytics:
    """
    Provides analytics and reporting for notifications.
    """
    
    def __init__(self):
        self.tracker = NotificationTracker()
    
    def get_delivery_stats(self, days=30):
        """
        Get delivery statistics for the last N days.
        """
        since = timezone.now() - timedelta(days=days)
        
        # Overall stats
        total_sent = Notification.objects.filter(created_at__gte=since).count()
        total_delivered = NotificationDelivery.objects.filter(
            sent_at__gte=since,
            status='delivered'
        ).count()
        total_failed = NotificationDelivery.objects.filter(
            sent_at__gte=since,
            status='failed'
        ).count()
        
        # By channel
        channel_stats = NotificationDelivery.objects.filter(
            sent_at__gte=since
        ).values('channel').annotate(
            sent=Count('id'),
            delivered=Count('id', filter=Q(status='delivered')),
            failed=Count('id', filter=Q(status='failed'))
        )
        
        # By type
        type_stats = Notification.objects.filter(
            created_at__gte=since
        ).values('notification_type').annotate(
            sent=Count('id'),
            delivered=Count('deliveries', filter=Q(deliveries__status='delivered')),
            read=Count('id', filter=Q(is_read=True))
        )
        
        return {
            'summary': {
                'total_sent': total_sent,
                'total_delivered': total_delivered,
                'total_failed': total_failed,
                'delivery_rate': (total_delivered / total_sent * 100) if total_sent > 0 else 0
            },
            'by_channel': list(channel_stats),
            'by_type': list(type_stats)
        }
    
    def get_engagement_stats(self, days=30):
        """
        Get user engagement statistics.
        """
        since = timezone.now() - timedelta(days=days)
        
        # Read rates by type
        read_stats = Notification.objects.filter(
            created_at__gte=since
        ).values('notification_type').annotate(
            total=Count('id'),
            read=Count('id', filter=Q(is_read=True)),
            read_rate=Avg(
                Case(
                    When(is_read=True, then=1),
                    default=0,
                    output_field=IntegerField()
                ) * 100
            )
        )
        
        # Time to read (average)
        avg_read_time = Notification.objects.filter(
            created_at__gte=since,
            is_read=True,
            read_at__isnull=False
        ).aggregate(
            avg_time=Avg(F('read_at') - F('created_at'))
        )['avg_time']
        
        # Click tracking (if implemented)
        # This would require a separate model to track clicks
        
        return {
            'by_type': list(read_stats),
            'avg_read_time': avg_read_time
        }
    
    def get_user_preferences_stats(self):
        """
        Get statistics on user notification preferences.
        """
        # Email frequency distribution
        email_freq_stats = NotificationPreference.objects.values(
            'email_frequency'
        ).annotate(
            count=Count('id')
        )
        
        # Channel enablement
        channel_stats = NotificationPreference.objects.aggregate(
            email_enabled=Count('id', filter=Q(email_enabled=True)),
            push_enabled=Count('id', filter=Q(push_enabled=True)),
            in_app_enabled=Count('id', filter=Q(in_app_enabled=True)),
            quiet_hours_enabled=Count('id', filter=Q(quiet_hours_enabled=True))
        )
        
        # Type preferences
        type_preferences = {
            'email_message': NotificationPreference.objects.filter(email_message=True).count(),
            'email_proposal': NotificationPreference.objects.filter(email_proposal=True).count(),
            'email_award': NotificationPreference.objects.filter(email_award=True).count(),
            'email_session': NotificationPreference.objects.filter(email_session=True).count(),
            'email_review': NotificationPreference.objects.filter(email_review=True).count(),
            'email_payment': NotificationPreference.objects.filter(email_payment=True).count(),
            'email_system': NotificationPreference.objects.filter(email_system=True).count(),
        }
        
        return {
            'email_frequency': list(email_freq_stats),
            'channel_preferences': channel_stats,
            'type_preferences': type_preferences
        }
    
    def get_time_series_data(self, days=30, granularity='day'):
        """
        Get time series data for notification metrics.
        """
        since = timezone.now() - timedelta(days=days)
        
        if granularity == 'hour':
            trunc_func = TruncHour('created_at')
            date_format = 'YYYY-MM-DD HH24:MI'
        else:
            trunc_func = TruncDate('created_at')
            date_format = 'YYYY-MM-DD'
        
        # Sent notifications over time
        sent_data = Notification.objects.filter(
            created_at__gte=since
        ).annotate(
            period=trunc_func
        ).values('period').annotate(
            count=Count('id')
        ).order_by('period')
        
        # Delivery rates over time
        delivery_data = NotificationDelivery.objects.filter(
            sent_at__gte=since
        ).annotate(
            period=trunc_func
        ).values('period').annotate(
            sent=Count('id'),
            delivered=Count('id', filter=Q(status='delivered')),
            failed=Count('id', filter=Q(status='failed'))
        ).order_by('period')
        
        return {
            'sent': list(sent_data),
            'delivery': list(delivery_data)
        }
    
    def get_top_notifications(self, days=30, metric='sent'):
        """
        Get top performing notifications.
        """
        since = timezone.now() - timedelta(days=days)
        
        if metric == 'sent':
            # Most sent notification types
            return Notification.objects.filter(
                created_at__gte=since
            ).values('notification_type').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
        
        elif metric == 'read':
            # Highest read rate
            return Notification.objects.filter(
                created_at__gte=since
            ).values('notification_type').annotate(
                total=Count('id'),
                read=Count('id', filter=Q(is_read=True)),
                read_rate=Avg(
                    Case(
                        When(is_read=True, then=1),
                        default=0,
                        output_field=IntegerField()
                    ) * 100
                )
            ).filter(total__gte=5).order_by('-read_rate')[:10]
        
        elif metric == 'engagement':
            # Most engaging (combination of read and click rates)
            # This would require click tracking implementation
            return []
    
    def generate_report(self, start_date=None, end_date=None, format='json'):
        """
        Generate a comprehensive analytics report.
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        # Get all analytics data
        delivery_stats = self.get_delivery_stats(
            days=(end_date - start_date).days
        )
        engagement_stats = self.get_engagement_stats(
            days=(end_date - start_date).days
        )
        user_prefs = self.get_user_preferences_stats()
        
        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'delivery_stats': delivery_stats,
            'engagement_stats': engagement_stats,
            'user_preferences': user_prefs
        }
        
        if format == 'json':
            return json.dumps(report, indent=2, default=str)
        else:
            return report


# Global instances
notification_tracker = NotificationTracker()
notification_analytics = NotificationAnalytics()


def track_notification_sent(notification, channel='in_app'):
    """Convenience function to track notification sent."""
    return notification_tracker.track_notification_sent(notification, channel)


def track_notification_delivered(delivery, provider_response=None):
    """Convenience function to track notification delivered."""
    return notification_tracker.track_notification_delivered(delivery, provider_response)


def track_notification_read(notification):
    """Convenience function to track notification read."""
    return notification_tracker.track_notification_read(notification)


def track_notification_clicked(notification, action_url=None):
    """Convenience function to track notification clicked."""
    return notification_tracker.track_notification_clicked(notification, action_url)


def track_notification_failed(delivery, error_message):
    """Convenience function to track notification failed."""
    return notification_tracker.track_notification_failed(delivery, error_message)