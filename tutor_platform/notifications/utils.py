from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.urls import reverse
from .models import Notification, NotificationPreference, NotificationTemplate, EmailQueue


def create_notification(
    recipient,
    title,
    content,
    notification_type=Notification.Type.SYSTEM,
    priority=Notification.Priority.MEDIUM,
    sender=None,
    related_object=None,
    action_url=None,
    action_text=None,
    send_email=False,
    send_push=False,
    expires_at=None
):
    """
    Create a notification and optionally send email/push notifications
    
    Args:
        recipient: User who will receive the notification
        title: Notification title
        content: Notification content
        notification_type: Type of notification (Notification.Type)
        priority: Priority level (Notification.Priority)
        sender: User who sent the notification (optional)
        related_object: Related object (Requirement, Proposal, etc.)
        action_url: URL for action button
        action_text: Text for action button
        send_email: Whether to send email notification
        send_push: Whether to send push notification
        expires_at: When notification expires
    
    Returns:
        Notification object
    """
    # Create notification
    notification = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        title=title,
        content=content,
        notification_type=notification_type,
        priority=priority,
        action_url=action_url,
        action_text=action_text,
        expires_at=expires_at
    )
    
    # Set related object if provided
    if related_object:
        notification.content_type = ContentType.objects.get_for_model(related_object)
        notification.object_id = related_object.id
        notification.save(update_fields=['content_type', 'object_id'])
    
    # Send email if requested
    if send_email:
        notification.send_email_notification()
    
    # Send push if requested
    if send_push:
        notification.send_push_notification()
    
    return notification


def create_system_notification(
    recipient,
    title,
    content,
    priority=Notification.Priority.MEDIUM,
    action_url=None,
    action_text=None,
    send_email=True
):
    """Create a system notification"""
    return create_notification(
        recipient=recipient,
        title=title,
        content=content,
        notification_type=Notification.Type.SYSTEM,
        priority=priority,
        sender=None,
        action_url=action_url,
        action_text=action_text,
        send_email=send_email,
        send_push=False
    )


def create_message_notification(
    recipient,
    sender,
    message,
    action_url=None,
    send_email=False
):
    """Create a message notification"""
    title = f"New message from {sender.get_full_name()}"
    content = message[:100] + "..." if len(message) > 100 else message
    
    return create_notification(
        recipient=recipient,
        title=title,
        content=content,
        notification_type=Notification.Type.MESSAGE,
        priority=Notification.Priority.MEDIUM,
        sender=sender,
        related_object=message,
        action_url=action_url,
        action_text="View Message",
        send_email=send_email,
        send_push=True
    )


def create_proposal_notification(
    recipient,
    proposal,
    action_url=None,
    send_email=True
):
    """Create a proposal notification"""
    title = f"New proposal for {proposal.requirement.title}"
    content = f"{proposal.tutor.get_full_name()} submitted a proposal: {proposal.cover_letter[:100]}..."
    
    return create_notification(
        recipient=recipient,
        title=title,
        content=content,
        notification_type=Notification.Type.PROPOSAL,
        priority=Notification.Priority.HIGH,
        sender=proposal.tutor,
        related_object=proposal,
        action_url=action_url,
        action_text="View Proposal",
        send_email=send_email,
        send_push=True
    )


def create_award_notification(
    recipient,
    award,
    action_url=None,
    send_email=True
):
    """Create an award notification"""
    title = f"Proposal awarded for {award.requirement.title}"
    content = f"Your proposal has been awarded to {award.student.get_full_name()}"
    
    return create_notification(
        recipient=recipient,
        title=title,
        content=content,
        notification_type=Notification.Type.AWARD,
        priority=Notification.Priority.HIGH,
        related_object=award,
        action_url=action_url,
        action_text="View Award",
        send_email=send_email,
        send_push=True
    )


def create_session_notification(
    recipient,
    session,
    action_url=None,
    send_email=True
):
    """Create a session notification"""
    title = f"Session scheduled: {session.title}"
    content = f"Session scheduled for {session.scheduled_start.strftime('%Y-%m-%d %H:%M')}"
    
    return create_notification(
        recipient=recipient,
        title=title,
        content=content,
        notification_type=Notification.Type.SESSION,
        priority=Notification.Priority.HIGH,
        related_object=session,
        action_url=action_url,
        action_text="View Session",
        send_email=send_email,
        send_push=True
    )


def create_review_notification(
    recipient,
    review,
    action_url=None,
    send_email=True
):
    """Create a review notification"""
    title = f"New review from {review.reviewer.get_full_name()}"
    content = f"You received a {review.rating}/5 star rating"
    
    return create_notification(
        recipient=recipient,
        title=title,
        content=content,
        notification_type=Notification.Type.REVIEW,
        priority=Notification.Priority.MEDIUM,
        sender=review.reviewer,
        related_object=review,
        action_url=action_url,
        action_text="View Review",
        send_email=send_email,
        send_push=False
    )


def create_payment_notification(
    recipient,
    payment_amount,
    payment_type,
    action_url=None,
    send_email=True
):
    """Create a payment notification"""
    title = f"Payment of ${payment_amount} received"
    content = f"You received a {payment_type} payment of ${payment_amount}"
    
    return create_notification(
        recipient=recipient,
        title=title,
        content=content,
        notification_type=Notification.Type.PAYMENT,
        priority=Notification.Priority.HIGH,
        action_url=action_url,
        action_text="View Payment",
        send_email=send_email,
        send_push=False
    )


def get_unread_count(user):
    """Get unread notification count for user"""
    return Notification.objects.filter(
        recipient=user,
        is_read=False
    ).count()


def get_recent_notifications(user, limit=5):
    """Get recent notifications for user"""
    return Notification.objects.filter(
        recipient=user
    ).select_related('sender').order_by('-created_at')[:limit]


def mark_all_as_read(user):
    """Mark all notifications as read for user"""
    Notification.objects.filter(
        recipient=user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )


def cleanup_expired_notifications():
    """Delete expired notifications"""
    return Notification.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()


def cleanup_old_read_notifications(days=30):
    """Delete old read notifications based on user preferences"""
    deleted_count = 0
    
    for preference in NotificationPreference.objects.filter(auto_delete_read=True):
        cutoff_date = timezone.now() - timezone.timedelta(days=preference.auto_delete_days)
        
        count, _ = Notification.objects.filter(
            recipient=preference.user,
            is_read=True,
            read_at__lt=cutoff_date
        ).delete()
        
        deleted_count += count
    
    return deleted_count


def queue_email_for_notification(notification):
    """Queue email for a notification"""
    try:
        # Get email template or use default
        try:
            template = NotificationTemplate.objects.get(
                notification_type=notification.notification_type,
                is_default=True,
                is_active=True
            )
            subject = template.render_subject(notification)
            body = template.render_body(notification)
            html_body = template.render_html(notification)
        except NotificationTemplate.DoesNotExist:
            subject = notification.title
            body = notification.content
            html_body = None
        
        # Create email queue entry
        EmailQueue.objects.create(
            notification=notification,
            recipient=notification.recipient,
            subject=subject,
            body=body,
            html_body=html_body
        )
        
        return True
        
    except Exception as e:
        # Log error
        print(f"Error queuing email for notification {notification.id}: {str(e)}")
        return False


def get_notification_url(notification):
    """Get appropriate URL for notification based on type"""
    if notification.action_url:
        return notification.action_url
    
    # Generate URL based on notification type and related object
    if notification.related_object:
        model_name = notification.content_type.model
        
        if model_name == 'message':
            return reverse('messaging:conversation', kwargs={'pk': notification.related_object.conversation.id})
        elif model_name == 'proposal':
            return reverse('requirements:proposal_detail', kwargs={'pk': notification.related_object.id})
        elif model_name == 'award':
            return reverse('requirements:award_detail', kwargs={'pk': notification.related_object.id})
        elif model_name == 'session':
            return reverse('requirements:session_detail', kwargs={'pk': notification.related_object.id})
        elif model_name == 'review':
            return reverse('requirements:review_detail', kwargs={'pk': notification.related_object.id})
    
    # Default to notification detail
    return reverse('notifications:detail', kwargs={'pk': notification.id})