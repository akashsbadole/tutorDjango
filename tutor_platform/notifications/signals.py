from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import NotificationPreference, Notification
from .utils import (
    create_notification, create_message_notification, create_proposal_notification,
    create_award_notification, create_session_notification,
    create_review_notification, create_payment_notification
)

User = get_user_model()


@receiver(post_save, sender=User)
def create_notification_preferences(sender, instance, created, **kwargs):
    """
    Create notification preferences for new users
    """
    if created:
        NotificationPreference.objects.create(user=instance)


# Requirement signals
@receiver(post_save, sender='requirements.Requirement')
def requirement_created(sender, instance, created, **kwargs):
    """
    Create notification when a new requirement is posted
    """
    if created:
        # Notify tutors who might be interested
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get tutors who might be interested based on subject
        interested_tutors = User.objects.filter(
            user_type='TUTOR',
            subjects__in=instance.subjects.all()
        ).distinct()
        
        for tutor in interested_tutors:
            create_notification(
                recipient=tutor,
                title=f"New requirement: {instance.title}",
                content=instance.description[:200],
                notification_type=Notification.Type.SYSTEM,
                priority=Notification.Priority.HIGH,
                related_object=instance,
                action_url=reverse('requirements:detail', kwargs={'pk': instance.pk}),
                action_text="View Requirement",
                send_email=True,
                send_push=True
            )


# Proposal signals
@receiver(post_save, sender='requirements.Proposal')
def proposal_submitted(sender, instance, created, **kwargs):
    """
    Create notification when a proposal is submitted
    """
    if created:
        # Notify the requirement owner
        create_proposal_notification(
            recipient=instance.requirement.student,
            proposal=instance,
            action_url=reverse('requirements:proposal_detail', kwargs={'pk': instance.pk}),
            send_email=True
        )


# Award signals
@receiver(post_save, sender='requirements.Award')
def award_created(sender, instance, created, **kwargs):
    """
    Create notification when an award is created
    """
    if created:
        # Notify the tutor whose proposal was awarded
        create_award_notification(
            recipient=instance.proposal.tutor,
            award=instance,
            action_url=reverse('requirements:award_detail', kwargs={'pk': instance.pk}),
            send_email=True
        )


# Session signals
@receiver(post_save, sender='requirements.Session')
def session_created(sender, instance, created, **kwargs):
    """
    Create notification when a session is scheduled
    """
    if created:
        # Notify both tutor and student
        create_session_notification(
            recipient=instance.tutor,
            session=instance,
            action_url=reverse('requirements:session_detail', kwargs={'pk': instance.pk}),
            send_email=True
        )
        
        create_session_notification(
            recipient=instance.student,
            session=instance,
            action_url=reverse('requirements:session_detail', kwargs={'pk': instance.pk}),
            send_email=True
        )


# Review signals
@receiver(post_save, sender='requirements.Review')
def review_created(sender, instance, created, **kwargs):
    """
    Create notification when a review is posted
    """
    if created:
        # Notify the user being reviewed
        if instance.tutor:
            recipient = instance.tutor
        else:
            recipient = instance.student
        
        create_review_notification(
            recipient=recipient,
            review=instance,
            action_url=reverse('requirements:review_detail', kwargs={'pk': instance.pk}),
            send_email=True
        )


# Payment signals
@receiver(post_save, sender='paymentsdetails.Payment')
def payment_created(sender, instance, created, **kwargs):
    """
    Create notification when a payment is made
    """
    if created:
        # Notify the recipient of the payment
        if instance.recipient_type == 'TUTOR':
            recipient = instance.tutor
        else:
            recipient = instance.student
        
        create_payment_notification(
            recipient=recipient,
            payment_amount=instance.amount,
            payment_type=instance.payment_type,
            action_url=reverse('paymentsdetails:payment_detail', kwargs={'pk': instance.pk}),
            send_email=True
        )


# Message signals
@receiver(post_save, sender='messaging.Message')
def message_created(sender, instance, created, **kwargs):
    """
    Create notification when a message is sent
    """
    if created:
        # Notify the recipient (not the sender)
        if instance.sender != instance.conversation.student:
            create_message_notification(
                recipient=instance.conversation.student,
                sender=instance.sender,
                message=instance.content,
                action_url=reverse('messaging:conversation', kwargs={'pk': instance.conversation.pk}),
                send_email=True
            )
        elif instance.sender != instance.conversation.tutor:
            create_message_notification(
                recipient=instance.conversation.tutor,
                sender=instance.sender,
                message=instance.content,
                action_url=reverse('messaging:conversation', kwargs={'pk': instance.conversation.pk}),
                send_email=True
            )


# System notification signals
@receiver(post_save, sender='notifications.SystemNotification')
def system_notification_created(sender, instance, created, **kwargs):
    """
    Create notifications when a system notification is created
    """
    if created and instance.is_active:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get target audience
        if instance.target_audience == 'ALL':
            users = User.objects.all()
        elif instance.target_audience == 'STUDENTS':
            users = User.objects.filter(user_type='STUDENT')
        elif instance.target_audience == 'TUTORS':
            users = User.objects.filter(user_type='TUTOR')
        elif instance.target_audience == 'ADMINS':
            users = User.objects.filter(is_staff=True)
        else:
            users = User.objects.none()
        
        # Create notifications for all target users
        for user in users:
            # Check if user has already dismissed this notification
            from .models import SystemNotificationDismissal
            if not SystemNotificationDismissal.objects.filter(
                system_notification=instance,
                user=user
            ).exists():
                create_notification(
                    recipient=user,
                    title=instance.title,
                    content=instance.message,
                    notification_type=Notification.Type.SYSTEM,
                    priority=instance.priority,
                    action_url=instance.action_url,
                    action_text=instance.action_text,
                    send_email=False,  # System notifications are in-app only
                    send_push=True
                )