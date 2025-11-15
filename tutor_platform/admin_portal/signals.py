"""
Django Tutor Platform Admin Portal Signals

This module contains signal handlers for the admin portal.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from .models import AdminProfile, AdminActivityLog
from .utils import log_admin_activity

User = get_user_model()


@receiver(post_save, sender=User)
def create_admin_profile(sender, instance, created, **kwargs):
    """
    Create AdminProfile when a new user is created with admin privileges
    """
    if created and (instance.is_superuser or instance.is_staff):
        AdminProfile.objects.get_or_create(
            user=instance,
            defaults={
                'is_super_admin': instance.is_superuser,
            }
        )
        
        # Log admin creation
        log_admin_activity(
            admin=instance,
            action_type='CREATE',
            action_description=f"Admin account created for {instance.username}",
            ip_address=None,
            user_agent=None
        )


@receiver(post_save, sender=AdminProfile)
def log_profile_changes(sender, instance, created, **kwargs):
    """
    Log changes to admin profiles
    """
    if not created:
        log_admin_activity(
            admin=instance.user,
            action_type='UPDATE',
            action_description=f"Admin profile updated for {instance.user.username}",
            content_type=None,
            object_id=instance.id
        )


@receiver(post_delete, sender=AdminProfile)
def log_profile_deletion(sender, instance, **kwargs):
    """
    Log deletion of admin profiles
    """
    log_admin_activity(
        admin=None,  # Admin is being deleted, so we can't reference them
        action_type='DELETE',
        action_description=f"Admin profile deleted for {instance.user.username}",
        content_type=None,
        object_id=instance.id,
        additional_data={'deleted_admin': instance.user.username}
    )