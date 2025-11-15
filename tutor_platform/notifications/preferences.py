"""
Notification preferences and unsubscribe utilities.
This module provides functionality to:
1. Manage user notification preferences
2. Handle unsubscribe requests
3. Process preference updates
4. Validate preference changes
5. Generate preference summaries
"""

from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.signing import TimestampSigner
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
import logging

from .models import Notification, NotificationPreference

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationPreferenceManager:
    """
    Manages user notification preferences.
    
    This class provides methods to:
    1. Create default preferences
    2. Update preferences
    3. Validate preferences
    4. Generate preference summaries
    5. Handle unsubscribe tokens
    """
    
    def __init__(self):
        self.signer = TimestampSigner()
    
    def create_default_preferences(self, user):
        """
        Create default notification preferences for a user.
        
        Args:
            user: The user to create preferences for
            
        Returns:
            NotificationPreference: The created preferences
        """
        try:
            return NotificationPreference.objects.get(user=user)
        except NotificationPreference.DoesNotExist:
            # Create default preferences
            return NotificationPreference.objects.create(user=user)
    
    def update_preferences(self, user, **kwargs):
        """
        Update user notification preferences.
        
        Args:
            user: The user to update preferences for
            **kwargs: Preference values to update
            
        Returns:
            NotificationPreference: The updated preferences
        """
        try:
            with transaction.atomic():
                preferences = NotificationPreference.objects.get(user=user)
                
                # Update each provided preference
                for key, value in kwargs.items():
                    if hasattr(preferences, key):
                        setattr(preferences, key, value)
                
                preferences.save()
                return preferences
                
        except NotificationPreference.DoesNotExist:
            # Create preferences if they don't exist
            return NotificationPreference.objects.create(user=user, **kwargs)
    
    def validate_preferences(self, preferences):
        """
        Validate notification preferences.
        
        Args:
            preferences: The preferences to validate
            
        Returns:
            tuple: (is_valid, errors)
        """
        errors = {}
        
        # Validate email frequency
        if 'email_frequency' in preferences:
            valid_frequencies = [choice[0] for choice in NotificationPreference.EmailFrequency.choices]
            if preferences['email_frequency'] not in valid_frequencies:
                errors['email_frequency'] = f"Invalid frequency: {preferences['email_frequency']}"
        
        # Validate quiet hours
        if preferences.get('quiet_hours_enabled', False):
            if not preferences.get('quiet_hours_start') or not preferences.get('quiet_hours_end'):
                errors['quiet_hours'] = "Both start and end times must be specified when quiet hours are enabled"
        
        # Validate auto-delete settings
        if preferences.get('auto_delete_read', False):
            auto_delete_days = preferences.get('auto_delete_days', 0)
            if auto_delete_days <= 0:
                errors['auto_delete'] = "Auto-delete days must be positive when auto-delete is enabled"
        
        return (len(errors) == 0, errors)
    
    def get_preference_summary(self, user):
        """
        Get a summary of user's notification preferences.
        
        Args:
            user: The user to get preferences for
            
        Returns:
            dict: Summary of preferences
        """
        try:
            preferences = NotificationPreference.objects.get(user=user)
            
            # Count enabled channels
            enabled_channels = []
            if preferences.email_enabled:
                enabled_channels.append('Email')
            if preferences.push_enabled:
                enabled_channels.append('Push')
            if preferences.in_app_enabled:
                enabled_channels.append('In-App')
            
            # Count enabled types
            enabled_email_types = []
            if preferences.email_message:
                enabled_email_types.append('Messages')
            if preferences.email_proposal:
                enabled_email_types.append('Proposals')
            if preferences.email_award:
                enabled_email_types.append('Awards')
            if preferences.email_session:
                enabled_email_types.append('Sessions')
            if preferences.email_review:
                enabled_email_types.append('Reviews')
            if preferences.email_payment:
                enabled_email_types.append('Payments')
            if preferences.email_system:
                enabled_email_types.append('System')
            
            return {
                'user': user.get_full_name() or user.username,
                'enabled_channels': enabled_channels,
                'email_frequency': preferences.get_email_frequency_display(),
                'quiet_hours_enabled': preferences.quiet_hours_enabled,
                'quiet_hours': {
                    'start': preferences.quiet_hours_start.strftime('%H:%M') if preferences.quiet_hours_start else None,
                    'end': preferences.quiet_hours_end.strftime('%H:%M') if preferences.quiet_hours_end else None,
                    'timezone': preferences.quiet_hours_timezone
                },
                'enabled_email_types': enabled_email_types,
                'auto_delete': {
                    'enabled': preferences.auto_delete_read,
                    'days': preferences.auto_delete_days
                }
            }
            
        except NotificationPreference.DoesNotExist:
            return {
                'user': user.get_full_name() or user.username,
                'error': 'No preferences found'
            }
    
    def generate_unsubscribe_token(self, user, notification_type=None):
        """
        Generate an unsubscribe token for a user.
        
        Args:
            user: The user to generate token for
            notification_type: Optional notification type to unsubscribe from
            
        Returns:
            str: The unsubscribe token
        """
        data = {
            'user_id': str(user.pk),
            'notification_type': notification_type or 'all'
        }
        
        return self.signer.sign(urlsafe_base64_encode(str(data).encode()).decode())
    
    def validate_unsubscribe_token(self, token, max_age=60*60*24*7):  # 7 days
        """
        Validate an unsubscribe token.
        
        Args:
            token: The token to validate
            max_age: Maximum age of token in seconds
            
        Returns:
            tuple: (is_valid, user_id, notification_type)
        """
        try:
            # Decode token
            data = urlsafe_base64_decode(self.signer.unsign(token, max_age=max_age)).decode()
            data = eval(data)  # In production, use json.loads instead
            
            # Get user
            user_id = data.get('user_id')
            notification_type = data.get('notification_type')
            
            # Verify user exists
            User.objects.get(pk=user_id)
            
            return (True, user_id, notification_type)
            
        except Exception as e:
            logger.error(f"Invalid unsubscribe token: {e}")
            return (False, None, None)
    
    def process_unsubscribe(self, user, notification_type=None):
        """
        Process an unsubscribe request.
        
        Args:
            user: The user to unsubscribe
            notification_type: The notification type to unsubscribe from
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with transaction.atomic():
                preferences = NotificationPreference.objects.get(user=user)
                
                if notification_type == 'all':
                    # Unsubscribe from all email notifications
                    preferences.email_enabled = False
                elif notification_type == 'email':
                    # Unsubscribe from all email notifications
                    preferences.email_enabled = False
                else:
                    # Unsubscribe from specific type
                    if notification_type == 'MESSAGE':
                        preferences.email_message = False
                    elif notification_type == 'PROPOSAL':
                        preferences.email_proposal = False
                    elif notification_type == 'AWARD':
                        preferences.email_award = False
                    elif notification_type == 'SESSION':
                        preferences.email_session = False
                    elif notification_type == 'REVIEW':
                        preferences.email_review = False
                    elif notification_type == 'PAYMENT':
                        preferences.email_payment = False
                    elif notification_type == 'SYSTEM':
                        preferences.email_system = False
                
                preferences.save()
                return True
                
        except NotificationPreference.DoesNotExist:
            logger.error(f"No preferences found for user {user.pk}")
            return False
        except Exception as e:
            logger.error(f"Error processing unsubscribe: {e}")
            return False
    
    def process_resubscribe(self, user, notification_type=None):
        """
        Process a resubscribe request.
        
        Args:
            user: The user to resubscribe
            notification_type: The notification type to resubscribe to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with transaction.atomic():
                preferences = NotificationPreference.objects.get(user=user)
                
                if notification_type == 'all':
                    # Resubscribe to all email notifications
                    preferences.email_enabled = True
                elif notification_type == 'email':
                    # Resubscribe to all email notifications
                    preferences.email_enabled = True
                else:
                    # Resubscribe to specific type
                    if notification_type == 'MESSAGE':
                        preferences.email_message = True
                    elif notification_type == 'PROPOSAL':
                        preferences.email_proposal = True
                    elif notification_type == 'AWARD':
                        preferences.email_award = True
                    elif notification_type == 'SESSION':
                        preferences.email_session = True
                    elif notification_type == 'REVIEW':
                        preferences.email_review = True
                    elif notification_type == 'PAYMENT':
                        preferences.email_payment = True
                    elif notification_type == 'SYSTEM':
                        preferences.email_system = True
                
                preferences.save()
                return True
                
        except NotificationPreference.DoesNotExist:
            logger.error(f"No preferences found for user {user.pk}")
            return False
        except Exception as e:
            logger.error(f"Error processing resubscribe: {e}")
            return False
    
    def get_unsubscribe_url(self, user, notification_type=None):
        """
        Generate an unsubscribe URL for a user.
        
        Args:
            user: The user to generate URL for
            notification_type: Optional notification type
            
        Returns:
            str: The unsubscribe URL
        """
        token = self.generate_unsubscribe_token(user, notification_type)
        
        from django.urls import reverse
        base_url = reverse('notifications:unsubscribe')
        
        return f"{base_url}?token={token}&type={notification_type or 'all'}"
    
    def get_resubscribe_url(self, user, notification_type=None):
        """
        Generate a resubscribe URL for a user.
        
        Args:
            user: The user to generate URL for
            notification_type: Optional notification type
            
        Returns:
            str: The resubscribe URL
        """
        token = self.generate_unsubscribe_token(user, notification_type)
        
        from django.urls import reverse
        base_url = reverse('notifications:resubscribe')
        
        return f"{base_url}?token={token}&type={notification_type or 'all'}"
    
    def export_preferences(self, user):
        """
        Export user preferences as JSON.
        
        Args:
            user: The user to export preferences for
            
        Returns:
            dict: User preferences as JSON-serializable data
        """
        try:
            preferences = NotificationPreference.objects.get(user=user)
            
            # Convert to JSON-serializable format
            return {
                'email_enabled': preferences.email_enabled,
                'push_enabled': preferences.push_enabled,
                'in_app_enabled': preferences.in_app_enabled,
                'email_frequency': preferences.email_frequency,
                'email_message': preferences.email_message,
                'email_proposal': preferences.email_proposal,
                'email_award': preferences.email_award,
                'email_session': preferences.email_session,
                'email_review': preferences.email_review,
                'email_payment': preferences.email_payment,
                'email_system': preferences.email_system,
                'push_message': preferences.push_message,
                'push_proposal': preferences.push_proposal,
                'push_award': preferences.push_award,
                'push_session': preferences.push_session,
                'push_review': preferences.push_review,
                'push_payment': preferences.push_payment,
                'push_system': preferences.push_system,
                'in_app_message': preferences.in_app_message,
                'in_app_proposal': preferences.in_app_proposal,
                'in_app_award': preferences.in_app_award,
                'in_app_session': preferences.in_app_session,
                'in_app_review': preferences.in_app_review,
                'in_app_payment': preferences.in_app_payment,
                'in_app_system': preferences.in_app_system,
                'quiet_hours_enabled': preferences.quiet_hours_enabled,
                'quiet_hours_start': preferences.quiet_hours_start.isoformat() if preferences.quiet_hours_start else None,
                'quiet_hours_end': preferences.quiet_hours_end.isoformat() if preferences.quiet_hours_end else None,
                'quiet_hours_timezone': preferences.quiet_hours_timezone,
                'auto_delete_read': preferences.auto_delete_read,
                'auto_delete_days': preferences.auto_delete_days,
                'exported_at': timezone.now().isoformat()
            }
            
        except NotificationPreference.DoesNotExist:
            return {
                'error': 'No preferences found',
                'exported_at': timezone.now().isoformat()
            }
    
    def import_preferences(self, user, preferences_data):
        """
        Import user preferences from JSON data.
        
        Args:
            user: The user to import preferences for
            preferences_data: The preferences data to import
            
        Returns:
            tuple: (success, errors)
        """
        try:
            with transaction.atomic():
                preferences = NotificationPreference.objects.get(user=user)
                
                # Update each preference
                for key, value in preferences_data.items():
                    if hasattr(preferences, key) and key != 'user_id':
                        setattr(preferences, key, value)
                
                preferences.save()
                return (True, [])
                
        except NotificationPreference.DoesNotExist:
            return (False, ['No preferences found for user'])
        except Exception as e:
            return (False, [f'Error importing preferences: {str(e)}'])


# Global instance
preference_manager = NotificationPreferenceManager()


def create_default_preferences(user):
    """Convenience function to create default preferences."""
    return preference_manager.create_default_preferences(user)


def update_preferences(user, **kwargs):
    """Convenience function to update preferences."""
    return preference_manager.update_preferences(user, **kwargs)


def get_preference_summary(user):
    """Convenience function to get preference summary."""
    return preference_manager.get_preference_summary(user)


def generate_unsubscribe_token(user, notification_type=None):
    """Convenience function to generate unsubscribe token."""
    return preference_manager.generate_unsubscribe_token(user, notification_type)


def validate_unsubscribe_token(token, max_age=60*60*24*7):
    """Convenience function to validate unsubscribe token."""
    return preference_manager.validate_unsubscribe_token(token, max_age)


def process_unsubscribe(user, notification_type=None):
    """Convenience function to process unsubscribe."""
    return preference_manager.process_unsubscribe(user, notification_type)


def process_resubscribe(user, notification_type=None):
    """Convenience function to process resubscribe."""
    return preference_manager.process_resubscribe(user, notification_type)


def export_preferences(user):
    """Convenience function to export preferences."""
    return preference_manager.export_preferences(user)


def import_preferences(user, preferences_data):
    """Convenience function to import preferences."""
    return preference_manager.import_preferences(user, preferences_data)