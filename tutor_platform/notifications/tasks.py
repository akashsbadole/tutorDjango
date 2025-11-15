from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.template.loader import render_to_string
import logging

from .models import (
    Notification, EmailQueue, PushMessage, NotificationDelivery,
    NotificationDigest, NotificationAnalytics, NotificationType
)
from .utils import create_notification, queue_email_for_notification

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_notification(self, email_queue_id):
    """Send email notification asynchronously"""
    try:
        email_queue = EmailQueue.objects.get(id=email_queue_id)
        return email_queue.send()
    except EmailQueue.DoesNotExist:
        logger.error(f"EmailQueue with id {email_queue_id} does not exist")
        return False
    except Exception as exc:
        logger.error(f"Error sending email {email_queue_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_push_notification(self, push_message_id):
    """Send push notification asynchronously"""
    try:
        push_message = PushMessage.objects.get(id=push_message_id)
        
        # Here you would integrate with actual push notification service
        # For now, we'll just mark as sent
        push_message.status = PushMessage.Status.SENT
        push_message.sent_at = timezone.now()
        push_message.save(update_fields=['status', 'sent_at'])
        
        # Create delivery record
        NotificationDelivery.objects.create(
            notification=push_message.notification,
            channel='PUSH',
            status='SENT',
            recipient_address=push_message.device.device_token,
            sent_at=timezone.now()
        )
        
        return True
    except PushMessage.DoesNotExist:
        logger.error(f"PushMessage with id {push_message_id} does not exist")
        return False
    except Exception as exc:
        logger.error(f"Error sending push notification {push_message_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task
def process_email_queue(limit=50, include_retry=False):
    """Process email queue for pending emails"""
    from .managers import EmailQueueManager
    
    # Get the custom manager
    email_manager = EmailQueueManager()
    email_manager.model = EmailQueue
    
    emails = email_manager.get_emails_for_processing(limit, include_retry)
    
    processed_count = 0
    success_count = 0
    failed_count = 0
    
    for email_queue in emails:
        try:
            with transaction.atomic():
                # Mark as processing to avoid duplicate processing
                email_manager.mark_emails_as_processing([email_queue.id])
                
                if email_queue.send():
                    success_count += 1
                else:
                    failed_count += 1
                
                processed_count += 1
        except Exception as e:
            logger.error(f"Error processing email {email_queue.id}: {str(e)}")
            failed_count += 1
    
    logger.info(f"Processed {processed_count} emails: {success_count} sent, {failed_count} failed")
    return {
        'processed': processed_count,
        'success': success_count,
        'failed': failed_count
    }


@shared_task
def process_push_notifications(limit=100):
    """Process pending push notifications"""
    from .managers import PushNotificationManager
    
    # Get the custom manager
    push_manager = PushNotificationManager()
    push_manager.model = PushMessage
    
    push_messages = push_manager.get_pending_push_messages(limit)
    
    processed_count = 0
    success_count = 0
    failed_count = 0
    
    for push_message in push_messages:
        try:
            send_push_notification(push_message.id)
            success_count += 1
        except Exception as e:
            logger.error(f"Error queuing push notification {push_message.id}: {str(e)}")
            failed_count += 1
        
        processed_count += 1
    
    logger.info(f"Processed {processed_count} push notifications: {success_count} queued, {failed_count} failed")
    return {
        'processed': processed_count,
        'success': success_count,
        'failed': failed_count
    }


@shared_task
def create_notification_digests():
    """Create notification digests for users based on their preferences"""
    from .models import NotificationPreference
    from .managers import NotificationManager
    
    # Get the custom manager
    notification_manager = NotificationManager()
    notification_manager.model = Notification
    
    digests_created = 0
    
    for preference in NotificationPreference.objects.filter(
        email_frequency__in=['daily', 'weekly']
    ):
        # Get notifications for digest
        notifications = notification_manager.get_notifications_for_digest(
            preference.user,
            preference.email_frequency
        )
        
        if notifications.exists():
            # Create digest
            digest = NotificationDigest.objects.create(
                user=preference.user,
                frequency=preference.email_frequency,
                subject=f"Your {preference.email_frequency} notifications"
            )
            
            # Add notifications to digest
            digest.notifications.add(*notifications)
            
            # Generate content
            digest.generate_content()
            
            # Queue email for digest
            queue_email_for_notification(digest)
            
            digests_created += 1
    
    logger.info(f"Created {digests_created} notification digests")
    return digests_created


@shared_task
def cleanup_expired_notifications():
    """Clean up expired notifications"""
    from .managers import NotificationManager
    
    # Get the custom manager
    notification_manager = NotificationManager()
    notification_manager.model = Notification
    
    expired_notifications = notification_manager.get_expired_notifications()
    count = expired_notifications.count()
    
    if count > 0:
        expired_notifications.delete()
        logger.info(f"Cleaned up {count} expired notifications")
    
    return count


@shared_task
def cleanup_old_read_notifications():
    """Clean up old read notifications based on user preferences"""
    from .models import NotificationPreference
    
    deleted_count = 0
    
    for preference in NotificationPreference.objects.filter(auto_delete_read=True):
        cutoff_date = timezone.now() - timezone.timedelta(days=preference.auto_delete_days)
        
        old_notifications = Notification.objects.filter(
            recipient=preference.user,
            is_read=True,
            read_at__lt=cutoff_date
        )
        
        count = old_notifications.count()
        if count > 0:
            old_notifications.delete()
            deleted_count += count
    
    logger.info(f"Cleaned up {deleted_count} old read notifications")
    return deleted_count


@shared_task
def update_notification_analytics():
    """Update daily notification analytics"""
    today = timezone.now().date()
    
    # Get all notification types
    notification_types = NotificationType.objects.filter(is_active=True)
    
    for notification_type in notification_types:
        # Count notifications sent today
        notifications = Notification.objects.filter(
            notification_type=notification_type.code,
            created_at__date=today
        )
        
        # Count by delivery status
        deliveries = NotificationDelivery.objects.filter(
            notification__in=notifications,
            created_at__date=today
        )
        
        total_sent = notifications.count()
        email_sent = deliveries.filter(channel='EMAIL').count()
        sms_sent = deliveries.filter(channel='SMS').count()
        push_sent = deliveries.filter(channel='PUSH').count()
        
        total_delivered = deliveries.filter(status='DELIVERED').count()
        email_delivered = deliveries.filter(channel='EMAIL', status='DELIVERED').count()
        sms_delivered = deliveries.filter(channel='SMS', status='DELIVERED').count()
        push_delivered = deliveries.filter(channel='PUSH', status='DELIVERED').count()
        
        total_read = notifications.filter(is_read=True).count()
        
        # Update or create analytics record
        analytics, created = NotificationAnalytics.objects.update_or_create(
            date=today,
            notification_type=notification_type,
            defaults={
                'total_sent': total_sent,
                'email_sent': email_sent,
                'sms_sent': sms_sent,
                'push_sent': push_sent,
                'total_delivered': total_delivered,
                'email_delivered': email_delivered,
                'sms_delivered': sms_delivered,
                'push_delivered': push_delivered,
                'total_read': total_read,
            }
        )
        
        if not created:
            # Update existing record
            analytics.total_sent = total_sent
            analytics.email_sent = email_sent
            analytics.sms_sent = sms_sent
            analytics.push_sent = push_sent
            analytics.total_delivered = total_delivered
            analytics.email_delivered = email_delivered
            analytics.sms_delivered = sms_delivered
            analytics.push_delivered = push_delivered
            analytics.total_read = total_read
            analytics.save()
    
    logger.info(f"Updated notification analytics for {today}")
    return today


@shared_task
def retry_failed_notifications():
    """Retry failed notifications"""
    from .managers import EmailQueueManager, PushNotificationManager
    
    # Get the custom managers
    email_manager = EmailQueueManager()
    email_manager.model = EmailQueue
    
    push_manager = PushNotificationManager()
    push_manager.model = PushMessage
    
    # Retry failed emails
    failed_emails = email_manager.get_retry_emails(limit=50)
    email_retry_count = 0
    
    for email in failed_emails:
        try:
            send_email_notification(email.id)
            email_retry_count += 1
        except Exception as e:
            logger.error(f"Error retrying email {email.id}: {str(e)}")
    
    # Retry failed push notifications
    failed_push = push_manager.get_failed_messages(hours=24)
    push_retry_count = 0
    
    for push in failed_push:
        try:
            send_push_notification(push.id)
            push_retry_count += 1
        except Exception as e:
            logger.error(f"Error retrying push notification {push.id}: {str(e)}")
    
    logger.info(f"Retried {email_retry_count} emails and {push_retry_count} push notifications")
    return {
        'email_retries': email_retry_count,
        'push_retries': push_retry_count
    }


@shared_task
def send_bulk_notifications(user_ids, title, content, notification_type='SYSTEM', priority='NORMAL'):
    """Send bulk notifications to multiple users"""
    from django.contrib.auth import get_user_model
    from .models import Notification
    
    User = get_user_model()
    users = User.objects.filter(id__in=user_ids)
    
    notifications_created = 0
    
    # Convert string values to enum values
    notification_type_enum = Notification.Type.SYSTEM
    priority_enum = Notification.Priority.MEDIUM
    
    if notification_type == 'MESSAGE':
        notification_type_enum = Notification.Type.MESSAGE
    elif notification_type == 'PROPOSAL':
        notification_type_enum = Notification.Type.PROPOSAL
    elif notification_type == 'AWARD':
        notification_type_enum = Notification.Type.AWARD
    elif notification_type == 'SESSION':
        notification_type_enum = Notification.Type.SESSION
    elif notification_type == 'REVIEW':
        notification_type_enum = Notification.Type.REVIEW
    elif notification_type == 'PAYMENT':
        notification_type_enum = Notification.Type.PAYMENT
    
    if priority == 'LOW':
        priority_enum = Notification.Priority.LOW
    elif priority == 'HIGH':
        priority_enum = Notification.Priority.HIGH
    elif priority == 'URGENT':
        priority_enum = Notification.Priority.URGENT
    
    for user in users:
        try:
            create_notification(
                recipient=user,
                title=title,
                content=content,
                notification_type=notification_type_enum,
                priority=priority_enum,
                send_email=True,
                send_push=True
            )
            notifications_created += 1
        except Exception as e:
            logger.error(f"Error creating notification for user {user.pk}: {str(e)}")
    
    logger.info(f"Created {notifications_created} bulk notifications")
    return notifications_created


@shared_task
def schedule_notification(recipient_id, title, content, notification_type='SYSTEM',
                         priority='NORMAL', scheduled_time=None,
                         send_email=False, send_push=False):
    """Schedule a notification to be sent at a specific time"""
    from django.contrib.auth import get_user_model
    from .models import Notification
    
    User = get_user_model()
    
    try:
        recipient = User.objects.get(id=recipient_id)
        
        # Convert string values to enum values
        notification_type_enum = Notification.Type.SYSTEM
        priority_enum = Notification.Priority.MEDIUM
        
        if notification_type == 'MESSAGE':
            notification_type_enum = Notification.Type.MESSAGE
        elif notification_type == 'PROPOSAL':
            notification_type_enum = Notification.Type.PROPOSAL
        elif notification_type == 'AWARD':
            notification_type_enum = Notification.Type.AWARD
        elif notification_type == 'SESSION':
            notification_type_enum = Notification.Type.SESSION
        elif notification_type == 'REVIEW':
            notification_type_enum = Notification.Type.REVIEW
        elif notification_type == 'PAYMENT':
            notification_type_enum = Notification.Type.PAYMENT
        
        if priority == 'LOW':
            priority_enum = Notification.Priority.LOW
        elif priority == 'HIGH':
            priority_enum = Notification.Priority.HIGH
        elif priority == 'URGENT':
            priority_enum = Notification.Priority.URGENT
        
        if scheduled_time and scheduled_time > timezone.now():
            # Create notification with scheduled time
            notification = create_notification(
                recipient=recipient,
                title=title,
                content=content,
                notification_type=notification_type_enum,
                priority=priority_enum,
                send_email=False,  # Don't send immediately
                send_push=False    # Don't send immediately
            )
            
            # Schedule email and push notifications for later
            if send_email:
                from .utils import queue_email_for_notification
                queue_email_for_notification(notification)
                # Update email queue with scheduled time
                from .models import EmailQueue
                EmailQueue.objects.filter(notification=notification).update(
                    scheduled_for=scheduled_time
                )
            
            if send_push:
                from .models import PushDevice, PushMessage
                from .managers import PushNotificationManager
                
                # Get the custom manager
                push_manager = PushNotificationManager()
                push_manager.model = PushMessage
                
                # Create push messages for all devices
                devices = PushDevice.objects.filter(user=recipient, is_active=True)
                for device in devices:
                    push_message = PushMessage.objects.create(
                        notification=notification,
                        device=device,
                        scheduled_for=scheduled_time
                    )
        else:
            # Send immediately
            create_notification(
                recipient=recipient,
                title=title,
                content=content,
                notification_type=notification_type_enum,
                priority=priority_enum,
                send_email=send_email,
                send_push=send_push
            )
        
        return True
    except User.DoesNotExist:
        logger.error(f"User with id {recipient_id} does not exist")
        return False


@shared_task
def schedule_notification_task(recipient_id, title, content, notification_type, priority, send_email, send_push):
    """Helper task for scheduled notifications"""
    from django.contrib.auth import get_user_model
    from .models import Notification
    
    User = get_user_model()
    
    try:
        recipient = User.objects.get(id=recipient_id)
        
        # Convert string values to enum values
        notification_type_enum = Notification.Type.SYSTEM
        priority_enum = Notification.Priority.MEDIUM
        
        if notification_type == 'MESSAGE':
            notification_type_enum = Notification.Type.MESSAGE
        elif notification_type == 'PROPOSAL':
            notification_type_enum = Notification.Type.PROPOSAL
        elif notification_type == 'AWARD':
            notification_type_enum = Notification.Type.AWARD
        elif notification_type == 'SESSION':
            notification_type_enum = Notification.Type.SESSION
        elif notification_type == 'REVIEW':
            notification_type_enum = Notification.Type.REVIEW
        elif notification_type == 'PAYMENT':
            notification_type_enum = Notification.Type.PAYMENT
        
        if priority == 'LOW':
            priority_enum = Notification.Priority.LOW
        elif priority == 'HIGH':
            priority_enum = Notification.Priority.HIGH
        elif priority == 'URGENT':
            priority_enum = Notification.Priority.URGENT
        
        create_notification(
            recipient=recipient,
            title=title,
            content=content,
            notification_type=notification_type_enum,
            priority=priority_enum,
            send_email=send_email,
            send_push=send_push
        )
        return True
    except User.DoesNotExist:
        logger.error(f"User with id {recipient_id} does not exist")
        return False


@shared_task
def cleanup_old_email_queue():
    """Clean up old sent emails from queue"""
    cutoff_date = timezone.now() - timezone.timedelta(days=30)
    
    old_emails = EmailQueue.objects.filter(
        status=EmailQueue.Status.SENT,
        sent_at__lt=cutoff_date
    )
    
    count = old_emails.count()
    if count > 0:
        old_emails.delete()
        logger.info(f"Cleaned up {count} old sent emails")
    
    return count


@shared_task
def cleanup_old_push_messages():
    """Clean up old delivered push messages"""
    cutoff_date = timezone.now() - timezone.timedelta(days=7)
    
    old_messages = PushMessage.objects.filter(
        status__in=['DELIVERED', 'FAILED'],
        created_at__lt=cutoff_date
    )
    
    count = old_messages.count()
    if count > 0:
        old_messages.delete()
        logger.info(f"Cleaned up {count} old push messages")
    
    return count


# Periodic tasks configuration
from celery.schedules import crontab

# Process email queue every 5 minutes
@shared_task
def process_email_queue_periodic():
    return process_email_queue()

# Process push notifications every 2 minutes
@shared_task
def process_push_notifications_periodic():
    return process_push_notifications()

# Create daily digests at 8 AM
@shared_task
def create_notification_digests_periodic():
    return create_notification_digests()

# Update analytics at midnight
@shared_task
def update_notification_analytics_periodic():
    return update_notification_analytics()

# Cleanup tasks at 2 AM
@shared_task
def cleanup_expired_notifications_periodic():
    return cleanup_expired_notifications()

@shared_task
def cleanup_old_read_notifications_periodic():
    return cleanup_old_read_notifications()

@shared_task
def cleanup_old_email_queue_periodic():
    return cleanup_old_email_queue()

@shared_task
def cleanup_old_push_messages_periodic():
    return cleanup_old_push_messages()