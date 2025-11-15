"""
Unit tests for notifications app models.
"""
import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from tests.factories import (
    UserFactory, NotificationFactory, NotificationPreferenceFactory
)
from tests.utils.helpers import TestMixin, DateTimeTestMixin


class NotificationModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for Notification model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.recipient = UserFactory.create()
        
    def test_notification_creation(self):
        """Test notification model creation."""
        notification = NotificationFactory.create(recipient=self.recipient)
        self.assertTrue(isinstance(notification, NotificationFactory._meta.model))
        self.assertEqual(notification.recipient, self.recipient)
        self.assertFalse(notification.is_read)
        
    def test_notification_string_representation(self):
        """Test notification string representation."""
        notification = NotificationFactory.create(
            recipient=self.recipient,
            title="New Message",
            message="You have a new message"
        )
        expected = f"New Message for {self.recipient.username}"
        self.assertEqual(str(notification), expected)
        
    def test_notification_title_max_length(self):
        """Test title max length validation."""
        notification = NotificationFactory.build(recipient=self.recipient)
        long_title = "x" * 201  # Exceeds max length
        notification.title = long_title
        
        with self.assertRaises(ValidationError):
            notification.full_clean()
            
    def test_notification_message_max_length(self):
        """Test message max length validation."""
        notification = NotificationFactory.build(recipient=self.recipient)
        long_message = "x" * 1001  # Exceeds max length
        notification.message = long_message
        
        with self.assertRaises(ValidationError):
            notification.full_clean()
            
    def test_notification_type_choices(self):
        """Test notification type field choices."""
        notification = NotificationFactory.build(recipient=self.recipient)
        
        valid_types = ['INFO', 'SUCCESS', 'WARNING', 'ERROR', 'PROPOSAL', 'MESSAGE', 'PAYMENT']
        for notif_type in valid_types:
            notification.notification_type = notif_type
            notification.full_clean()  # Should not raise
            
        # Test invalid type
        notification.notification_type = 'INVALID'
        with self.assertRaises(ValidationError):
            notification.full_clean()
            
    def test_notification_recipient_relationship(self):
        """Test notification-recipient relationship."""
        notification = NotificationFactory.create(recipient=self.recipient)
        
        # Test reverse relationship
        self.assertIn(notification, self.recipient.notifications.all())
        
    def test_notification_mark_as_read(self):
        """Test mark_as_read method."""
        notification = NotificationFactory.create(
            recipient=self.recipient,
            is_read=False
        )
        
        # Mark as read
        notification.mark_as_read()
        notification.refresh_from_db()
        
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
        
    def test_notification_ordering(self):
        """Test notification ordering for recipient."""
        # Create notifications with different timestamps
        notif1 = NotificationFactory.create(
            recipient=self.recipient,
            created_at=self.create_past_date(hours=3)
        )
        notif2 = NotificationFactory.create(
            recipient=self.recipient,
            created_at=self.create_past_date(hours=2)
        )
        notif3 = NotificationFactory.create(
            recipient=self.recipient,
            created_at=self.create_past_date(hours=1)
        )
        
        # Notifications should be ordered by created_at (descending)
        notifications = self.recipient.notifications.all()
        self.assertEqual(notifications[0], notif3)  # Most recent
        self.assertEqual(notifications[1], notif2)
        self.assertEqual(notifications[2], notif1)  # Oldest


class NotificationPreferenceModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for NotificationPreference model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_notification_preference_creation(self):
        """Test notification preference model creation."""
        preference = NotificationPreferenceFactory.create(user=self.user)
        self.assertTrue(isinstance(preference, NotificationPreferenceFactory._meta.model))
        self.assertEqual(preference.user, self.user)
        self.assertTrue(preference.email_notifications)
        
    def test_notification_preference_string_representation(self):
        """Test notification preference string representation."""
        preference = NotificationPreferenceFactory.create(user=self.user)
        expected = f"Preferences for {self.user.username}"
        self.assertEqual(str(preference), expected)
        
    def test_notification_preference_email_frequency_choices(self):
        """Test email frequency field choices."""
        preference = NotificationPreferenceFactory.build(user=self.user)
        
        valid_frequencies = ['IMMEDIATE', 'DAILY', 'WEEKLY']
        for frequency in valid_frequencies:
            preference.email_frequency = frequency
            preference.full_clean()  # Should not raise
            
        # Test invalid frequency
        preference.email_frequency = 'INVALID'
        with self.assertRaises(ValidationError):
            preference.full_clean()
            
    def test_notification_preference_notification_types_choices(self):
        """Test notification types field choices."""
        preference = NotificationPreferenceFactory.build(user=self.user)
        
        valid_types = ['ALL', 'IMPORTANT', 'NONE']
        for notif_types in valid_types:
            preference.notification_types = notif_types
            preference.full_clean()  # Should not raise
            
        # Test invalid types
        preference.notification_types = 'INVALID'
        with self.assertRaises(ValidationError):
            preference.full_clean()
            
    def test_notification_preference_user_relationship(self):
        """Test notification preference-user relationship."""
        preference = NotificationPreferenceFactory.create(user=self.user)
        
        # Test reverse relationship
        self.assertIn(preference, self.user.notification_preferences.all())
        
    def test_notification_preference_defaults(self):
        """Test default values for notification preference."""
        preference = NotificationPreferenceFactory.build(user=self.user)
        
        # Test defaults
        self.assertTrue(preference.email_notifications)
        self.assertFalse(preference.sms_notifications)
        self.assertEqual(preference.email_frequency, 'IMMEDIATE')
        self.assertEqual(preference.notification_types, 'ALL')


class NotificationQuerySetTest(TestCase, TestMixin):
    """Test cases for Notification model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_unread_queryset(self):
        """Test unread queryset method."""
        # Create notifications with different read status
        unread = NotificationFactory.create(
            recipient=self.user,
            is_read=False
        )
        read = NotificationFactory.create(
            recipient=self.user,
            is_read=True
        )
        
        # Test filtering
        unread_notifications = Notification.objects.unread()
        self.assertEqual(unread_notifications.count(), 1)
        self.assertIn(unread, unread_notifications)
        self.assertNotIn(read, unread_notifications)
        
    def test_read_queryset(self):
        """Test read queryset method."""
        # Create notifications with different read status
        unread = NotificationFactory.create(
            recipient=self.user,
            is_read=False
        )
        read = NotificationFactory.create(
            recipient=self.user,
            is_read=True
        )
        
        # Test filtering
        read_notifications = Notification.objects.read()
        self.assertEqual(read_notifications.count(), 1)
        self.assertIn(read, read_notifications)
        self.assertNotIn(unread, read_notifications)
        
    def test_by_type_queryset(self):
        """Test by_type queryset method."""
        # Create notifications with different types
        message_notif = NotificationFactory.create(
            recipient=self.user,
            notification_type='MESSAGE'
        )
        payment_notif = NotificationFactory.create(
            recipient=self.user,
            notification_type='PAYMENT'
        )
        
        # Test filtering by MESSAGE type
        message_notifications = Notification.objects.by_type('MESSAGE')
        self.assertEqual(message_notifications.count(), 1)
        self.assertIn(message_notif, message_notifications)
        self.assertNotIn(payment_notif, message_notifications)
        
    def test_by_recipient_queryset(self):
        """Test by_recipient queryset method."""
        # Create notifications for different users
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        
        notif1 = NotificationFactory.create(recipient=user1)
        notif2 = NotificationFactory.create(recipient=user2)
        
        # Test filtering by user1
        user1_notifications = Notification.objects.by_recipient(user1.id)
        self.assertEqual(user1_notifications.count(), 1)
        self.assertIn(notif1, user1_notifications)
        self.assertNotIn(notif2, user1_notifications)
        
    def test_recent_queryset(self):
        """Test recent queryset method."""
        # Create notifications with different timestamps
        old_notif = NotificationFactory.create(
            recipient=self.user,
            created_at=self.create_past_date(days=10)
        )
        recent_notif = NotificationFactory.create(
            recipient=self.user,
            created_at=self.create_past_date(days=2)
        )
        
        # Test filtering (last 7 days)
        recent_notifications = Notification.objects.recent(days=7)
        self.assertEqual(recent_notifications.count(), 1)
        self.assertIn(recent_notif, recent_notifications)
        self.assertNotIn(old_notif, recent_notifications)


class NotificationPreferenceQuerySetTest(TestCase, TestMixin):
    """Test cases for NotificationPreference model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_for_user_queryset(self):
        """Test for_user queryset method."""
        # Create preferences for different users
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        
        pref1 = NotificationPreferenceFactory.create(user=user1)
        pref2 = NotificationPreferenceFactory.create(user=user2)
        
        # Test filtering by user1
        user1_preferences = NotificationPreference.objects.for_user(user1.id)
        self.assertEqual(user1_preferences.count(), 1)
        self.assertIn(pref1, user1_preferences)
        self.assertNotIn(pref2, user1_preferences)
        
    def test_email_enabled_queryset(self):
        """Test email_enabled queryset method."""
        # Create preferences with different email settings
        email_enabled = NotificationPreferenceFactory.create(
            user=self.user,
            email_notifications=True
        )
        email_disabled = NotificationPreferenceFactory.create(
            user=self.user,
            email_notifications=False
        )
        
        # Test filtering
        email_enabled_preferences = NotificationPreference.objects.email_enabled()
        self.assertEqual(email_enabled_preferences.count(), 1)
        self.assertIn(email_enabled, email_enabled_preferences)
        self.assertNotIn(email_disabled, email_enabled_preferences)
        
    def test_push_enabled_queryset(self):
        """Test push_enabled queryset method."""
        # Create preferences with different push settings
        push_enabled = NotificationPreferenceFactory.create(
            user=self.user,
            push_notifications=True
        )
        push_disabled = NotificationPreferenceFactory.create(
            user=self.user,
            push_notifications=False
        )
        
        # Test filtering
        push_enabled_preferences = NotificationPreference.objects.push_enabled()
        self.assertEqual(push_enabled_preferences.count(), 1)
        self.assertIn(push_enabled, push_enabled_preferences)
        self.assertNotIn(push_disabled, push_enabled_preferences)


class NotificationSignalTest(TestCase, TestMixin):
    """Test cases for Notification model signals."""
    
    def test_notification_created_signal(self):
        """Test notification creation signal."""
        # This would test that notification creation triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_notification_read_signal(self):
        """Test notification read signal."""
        # This would test that marking notifications as read triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_notification_sent_signal(self):
        """Test notification sent signal."""
        # This would test that sending notifications triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic


class NotificationPreferenceSignalTest(TestCase, TestMixin):
    """Test cases for NotificationPreference model signals."""
    
    def test_preference_created_signal(self):
        """Test preference creation signal."""
        # This would test that preference creation triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_preference_updated_signal(self):
        """Test preference update signal."""
        # This would test that preference updates trigger
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic