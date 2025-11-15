"""
Unit tests for messaging app models.
"""
import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from tests.factories import (
    UserFactory, TutorUserFactory, StudentUserFactory,
    ConversationFactory, MessageFactory, OnlineClassFactory,
    ClassRecordingFactory
)
from tests.utils.helpers import TestMixin, DateTimeTestMixin


class ConversationModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for Conversation model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.requirement = RequirementFactory.create()  # Will need to import
        self.tutor = TutorUserFactory.create()
        
    def test_conversation_creation(self):
        """Test conversation model creation."""
        conversation = ConversationFactory.create(
            requirement=self.requirement
        )
        self.assertTrue(isinstance(conversation, ConversationFactory._meta.model))
        self.assertEqual(conversation.requirement, self.requirement)
        
    def test_conversation_string_representation(self):
        """Test conversation string representation."""
        conversation = ConversationFactory.create(
            requirement=self.requirement
        )
        expected = f"Conversation for {self.requirement.title}"
        self.assertEqual(str(conversation), expected)
        
    def test_conversation_requirement_relationship(self):
        """Test conversation-requirement relationship."""
        conversation = ConversationFactory.create(
            requirement=self.requirement
        )
        
        # Test reverse relationship
        self.assertIn(conversation, self.requirement.conversations.all())
        
    def test_conversation_participants_relationship(self):
        """Test conversation-participants relationship."""
        conversation = ConversationFactory.create(
            requirement=self.requirement
        )
        
        # Test that participants are linked through proposals
        self.assertTrue(conversation.participants.exists())
        
    def test_conversation_updated_at_auto_update(self):
        """Test updated_at auto-updates on message changes."""
        conversation = ConversationFactory.create(
            requirement=self.requirement
        )
        original_updated = conversation.updated_at
        
        # Add a message (should update conversation.updated_at)
        MessageFactory.create(conversation=conversation)
        conversation.refresh_from_db()
        
        self.assertGreater(conversation.updated_at, original_updated)


class MessageModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for Message model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.conversation = ConversationFactory.create()
        self.sender = UserFactory.create()
        
    def test_message_creation(self):
        """Test message model creation."""
        message = MessageFactory.create(
            conversation=self.conversation,
            sender=self.sender
        )
        self.assertTrue(isinstance(message, MessageFactory._meta.model))
        self.assertEqual(message.conversation, self.conversation)
        self.assertEqual(message.sender, self.sender)
        self.assertFalse(message.is_read)
        
    def test_message_string_representation(self):
        """Test message string representation."""
        message = MessageFactory.create(
            conversation=self.conversation,
            sender=self.sender,
            content="Hello, world!"
        )
        expected = f"Message from {self.sender.username}: Hello, world!..."
        self.assertEqual(str(message), expected)
        
    def test_message_content_max_length(self):
        """Test message content max length validation."""
        message = MessageFactory.build(
            conversation=self.conversation,
            sender=self.sender
        )
        long_content = "x" * 1001  # Exceeds max length
        message.content = long_content
        
        with self.assertRaises(ValidationError):
            message.full_clean()
            
    def test_message_conversation_relationship(self):
        """Test message-conversation relationship."""
        message = MessageFactory.create(
            conversation=self.conversation
        )
        
        # Test reverse relationship
        self.assertIn(message, self.conversation.messages.all())
        
    def test_message_sender_relationship(self):
        """Test message-sender relationship."""
        message = MessageFactory.create(
            conversation=self.conversation,
            sender=self.sender
        )
        
        # Test reverse relationship
        self.assertIn(message, self.sender.sent_messages.all())
        
    def test_message_read_receipt(self):
        """Test message read receipt functionality."""
        message = MessageFactory.create(
            conversation=self.conversation,
            sender=self.sender,
            is_read=False
        )
        
        # Mark as read
        message.mark_as_read()
        message.refresh_from_db()
        
        self.assertTrue(message.is_read)
        self.assertIsNotNone(message.read_at)
        
    def test_message_ordering(self):
        """Test message ordering in conversation."""
        # Create messages with different timestamps
        msg1 = MessageFactory.create(
            conversation=self.conversation,
            created_at=self.create_past_date(hours=3)
        )
        msg2 = MessageFactory.create(
            conversation=self.conversation,
            created_at=self.create_past_date(hours=2)
        )
        msg3 = MessageFactory.create(
            conversation=self.conversation,
            created_at=self.create_past_date(hours=1)
        )
        
        # Messages should be ordered by created_at (ascending)
        messages = self.conversation.messages.all()
        self.assertEqual(messages[0], msg1)
        self.assertEqual(messages[1], msg2)
        self.assertEqual(messages[2], msg3)


class OnlineClassModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for OnlineClass model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.host = TutorUserFactory.create()
        
    def test_online_class_creation(self):
        """Test online class model creation."""
        online_class = OnlineClassFactory.create(host=self.host)
        self.assertTrue(isinstance(online_class, OnlineClassFactory._meta.model))
        self.assertEqual(online_class.host, self.host)
        self.assertEqual(online_class.status, 'SCHEDULED')
        
    def test_online_class_string_representation(self):
        """Test online class string representation."""
        online_class = OnlineClassFactory.create(
            host=self.host,
            title="Math Tutoring Session"
        )
        expected = f"Math Tutoring Session by {self.host.username}"
        self.assertEqual(str(online_class), expected)
        
    def test_online_class_title_max_length(self):
        """Test title max length validation."""
        online_class = OnlineClassFactory.build(host=self.host)
        long_title = "x" * 201  # Exceeds max length
        online_class.title = long_title
        
        with self.assertRaises(ValidationError):
            online_class.full_clean()
            
    def test_online_class_description_max_length(self):
        """Test description max length validation."""
        online_class = OnlineClassFactory.build(host=self.host)
        long_description = "x" * 1001  # Exceeds max length
        online_class.description = long_description
        
        with self.assertRaises(ValidationError):
            online_class.full_clean()
            
    def test_online_class_platform_choices(self):
        """Test platform field choices."""
        online_class = OnlineClassFactory.build(host=self.host)
        
        valid_platforms = ['ZOOM', 'TEAMS', 'MEET', 'SKYPE']
        for platform in valid_platforms:
            online_class.platform = platform
            online_class.full_clean()  # Should not raise
            
        # Test invalid platform
        online_class.platform = 'INVALID'
        with self.assertRaises(ValidationError):
            online_class.full_clean()
            
    def test_online_class_scheduling_validation(self):
        """Test scheduling validation."""
        online_class = OnlineClassFactory.build(host=self.host)
        
        # Test end before start
        online_class.scheduled_start = self.create_future_date(hours=2)
        online_class.scheduled_end = self.create_future_date(hours=1)
        with self.assertRaises(ValidationError):
            online_class.full_clean()
            
        # Test start in past
        online_class.scheduled_start = self.create_past_date(hours=1)
        with self.assertRaises(ValidationError):
            online_class.full_clean()
            
    def test_online_class_max_participants_validation(self):
        """Test max participants validation."""
        online_class = OnlineClassFactory.build(host=self.host)
        
        # Test negative participants
        online_class.max_participants = -1
        with self.assertRaises(ValidationError):
            online_class.full_clean()
            
        # Test zero participants
        online_class.max_participants = 0
        with self.assertRaises(ValidationError):
            online_class.full_clean()
            
    def test_online_class_status_choices(self):
        """Test status field choices."""
        online_class = OnlineClassFactory.build(host=self.host)
        
        valid_statuses = ['SCHEDULED', 'LIVE', 'COMPLETED', 'CANCELLED']
        for status in valid_statuses:
            online_class.status = status
            online_class.full_clean()  # Should not raise
            
        # Test invalid status
        online_class.status = 'INVALID'
        with self.assertRaises(ValidationError):
            online_class.full_clean()
            
    def test_online_class_host_relationship(self):
        """Test online class-host relationship."""
        online_class = OnlineClassFactory.create(host=self.host)
        
        # Test reverse relationship
        self.assertIn(online_class, self.host.hosted_classes.all())


class ClassRecordingModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for ClassRecording model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.online_class = OnlineClassFactory.create()
        
    def test_class_recording_creation(self):
        """Test class recording model creation."""
        recording = ClassRecordingFactory.create(
            online_class=self.online_class
        )
        self.assertTrue(isinstance(recording, ClassRecordingFactory._meta.model))
        self.assertEqual(recording.online_class, self.online_class)
        self.assertFalse(recording.is_public)
        
    def test_class_recording_string_representation(self):
        """Test class recording string representation."""
        recording = ClassRecordingFactory.create(
            online_class=self.online_class,
            title="Math Session Recording"
        )
        expected = f"Math Session Recording - {recording.duration_minutes}min"
        self.assertEqual(str(recording), expected)
        
    def test_class_recording_title_max_length(self):
        """Test title max length validation."""
        recording = ClassRecordingFactory.build(
            online_class=self.online_class
        )
        long_title = "x" * 201  # Exceeds max length
        recording.title = long_title
        
        with self.assertRaises(ValidationError):
            recording.full_clean()
            
    def test_class_recording_description_max_length(self):
        """Test description max length validation."""
        recording = ClassRecordingFactory.build(
            online_class=self.online_class
        )
        long_description = "x" * 301  # Exceeds max length
        recording.description = long_description
        
        with self.assertRaises(ValidationError):
            recording.full_clean()
            
    def test_class_recording_duration_validation(self):
        """Test duration validation."""
        recording = ClassRecordingFactory.build(
            online_class=self.online_class
        )
        
        # Test negative duration
        recording.duration_minutes = -1
        with self.assertRaises(ValidationError):
            recording.full_clean()
            
        # Test zero duration
        recording.duration_minutes = 0
        with self.assertRaises(ValidationError):
            recording.full_clean()
            
        # Test excessive duration
        recording.duration_minutes = 481  # More than 8 hours
        with self.assertRaises(ValidationError):
            recording.full_clean()
            
    def test_class_recording_file_size_validation(self):
        """Test file size validation."""
        recording = ClassRecordingFactory.build(
            online_class=self.online_class
        )
        
        # Test negative file size
        recording.file_size = -1
        with self.assertRaises(ValidationError):
            recording.full_clean()
            
    def test_class_recording_view_count_default(self):
        """Test view_count defaults to 0."""
        recording = ClassRecordingFactory.build(
            online_class=self.online_class
        )
        self.assertEqual(recording.view_count, 0)
        
    def test_class_recording_online_class_relationship(self):
        """Test recording-online class relationship."""
        recording = ClassRecordingFactory.create(
            online_class=self.online_class
        )
        
        # Test reverse relationship
        self.assertIn(recording, self.online_class.recordings.all())


class ConversationQuerySetTest(TestCase, TestMixin):
    """Test cases for Conversation model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.requirement = RequirementFactory.create()
        
    def test_by_requirement_queryset(self):
        """Test by_requirement queryset method."""
        # Create conversations for different requirements
        conv1 = ConversationFactory.create(requirement=self.requirement)
        req2 = RequirementFactory.create()
        conv2 = ConversationFactory.create(requirement=req2)
        
        # Test filtering by requirement
        requirement_conversations = Conversation.objects.by_requirement(self.requirement.id)
        self.assertEqual(requirement_conversations.count(), 1)
        self.assertIn(conv1, requirement_conversations)
        self.assertNotIn(conv2, requirement_conversations)
        
    def test_with_unread_messages_queryset(self):
        """Test with_unread_messages queryset method."""
        # Create conversations with and without unread messages
        conv_with_unread = ConversationFactory.create()
        MessageFactory.create(
            conversation=conv_with_unread,
            is_read=False
        )
        
        conv_all_read = ConversationFactory.create()
        MessageFactory.create(
            conversation=conv_all_read,
            is_read=True
        )
        
        # Test filtering
        conversations_with_unread = Conversation.objects.with_unread_messages()
        self.assertEqual(conversations_with_unread.count(), 1)
        self.assertIn(conv_with_unread, conversations_with_unread)
        self.assertNotIn(conv_all_read, conversations_with_unread)


class MessageQuerySetTest(TestCase, TestMixin):
    """Test cases for Message model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.conversation = ConversationFactory.create()
        self.sender = UserFactory.create()
        
    def test_unread_queryset(self):
        """Test unread queryset method."""
        # Create messages with different read status
        unread = MessageFactory.create(
            conversation=self.conversation,
            sender=self.sender,
            is_read=False
        )
        read = MessageFactory.create(
            conversation=self.conversation,
            sender=self.sender,
            is_read=True
        )
        
        # Test filtering
        unread_messages = Message.objects.unread()
        self.assertEqual(unread_messages.count(), 1)
        self.assertIn(unread, unread_messages)
        self.assertNotIn(read, unread_messages)
        
    def test_by_conversation_queryset(self):
        """Test by_conversation queryset method."""
        # Create messages for different conversations
        msg1 = MessageFactory.create(conversation=self.conversation)
        conv2 = ConversationFactory.create()
        msg2 = MessageFactory.create(conversation=conv2)
        
        # Test filtering by conversation
        conversation_messages = Message.objects.by_conversation(self.conversation.id)
        self.assertEqual(conversation_messages.count(), 1)
        self.assertIn(msg1, conversation_messages)
        self.assertNotIn(msg2, conversation_messages)
        
    def test_by_sender_queryset(self):
        """Test by_sender queryset method."""
        # Create messages from different senders
        sender1 = UserFactory.create()
        sender2 = UserFactory.create()
        
        msg1 = MessageFactory.create(
            conversation=self.conversation,
            sender=sender1
        )
        msg2 = MessageFactory.create(
            conversation=self.conversation,
            sender=sender2
        )
        
        # Test filtering by sender1
        sender1_messages = Message.objects.by_sender(sender1.id)
        self.assertEqual(sender1_messages.count(), 1)
        self.assertIn(msg1, sender1_messages)
        self.assertNotIn(msg2, sender1_messages)


class OnlineClassQuerySetTest(TestCase, TestMixin):
    """Test cases for OnlineClass model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.host = TutorUserFactory.create()
        
    def test_upcoming_queryset(self):
        """Test upcoming queryset method."""
        # Create classes with different schedules
        upcoming = OnlineClassFactory.create(
            host=self.host,
            scheduled_start=self.create_future_date(hours=2)
        )
        past = OnlineClassFactory.create(
            host=self.host,
            scheduled_start=self.create_past_date(hours=2)
        )
        
        # Test filtering
        upcoming_classes = OnlineClass.objects.upcoming()
        self.assertEqual(upcoming_classes.count(), 1)
        self.assertIn(upcoming, upcoming_classes)
        self.assertNotIn(past, upcoming_classes)
        
    def test_by_host_queryset(self):
        """Test by_host queryset method."""
        # Create classes for different hosts
        host1 = TutorUserFactory.create()
        host2 = TutorUserFactory.create()
        
        class1 = OnlineClassFactory.create(host=host1)
        class2 = OnlineClassFactory.create(host=host2)
        
        # Test filtering by host1
        host1_classes = OnlineClass.objects.by_host(host1.id)
        self.assertEqual(host1_classes.count(), 1)
        self.assertIn(class1, host1_classes)
        self.assertNotIn(class2, host1_classes)
        
    def test_live_queryset(self):
        """Test live queryset method."""
        # Create classes with different statuses
        live = OnlineClassFactory.create(
            host=self.host,
            status='LIVE'
        )
        scheduled = OnlineClassFactory.create(
            host=self.host,
            status='SCHEDULED'
        )
        
        # Test filtering
        live_classes = OnlineClass.objects.live()
        self.assertEqual(live_classes.count(), 1)
        self.assertIn(live, live_classes)
        self.assertNotIn(scheduled, live_classes)


class MessagingSignalTest(TestCase, TestMixin):
    """Test cases for messaging app signals."""
    
    def test_message_created_signal(self):
        """Test message creation signal."""
        # This would test that message creation triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_message_read_signal(self):
        """Test message read signal."""
        # This would test that marking messages as read triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_class_started_signal(self):
        """Test class started signal."""
        # This would test that class status changes to LIVE trigger
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_class_ended_signal(self):
        """Test class ended signal."""
        # This would test that class status changes to COMPLETED trigger
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic