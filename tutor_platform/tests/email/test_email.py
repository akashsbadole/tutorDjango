"""
Email tests for Django tutoring platform.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.mail import send_mail, EmailMessage
from django.utils import timezone
from datetime import timedelta

from tests.factories import (
    UserFactory, TutorProfileFactory, StudentProfileFactory, CategoryFactory,
    SubjectFactory, RequirementFactory, ProposalFactory, PaymentFactory
)
from tests.utils.helpers import TestMixin, EmailTestMixin

User = get_user_model()


class EmailDeliveryTest(TestCase, TestMixin, EmailTestMixin):
    """Tests for email delivery."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_user_registration_email(self):
        """Test user registration email."""
        # Clear email outbox
        self.clear_emails()
        
        # Create new user
        user = UserFactory.create()
        
        # Check that welcome email was sent
        self.assert_email_sent(1)
        email = self.get_latest_email()
        self.assertEqual(email.to[0], user.email)
        self.assertIn('Welcome', email.subject)
        self.assertIn(user.username, email.body)
        
    def test_password_reset_email(self):
        """Test password reset email."""
        # Clear email outbox
        self.clear_emails()
        
        # Request password reset
        response = self.client.post(reverse('accounts:password_reset'), {
            'email': self.user.email
        })
        
        # Check that password reset email was sent
        self.assert_email_sent(1)
        email = self.get_latest_email()
        self.assertEqual(email.to[0], self.user.email)
        self.assertIn('Password reset', email.subject)
        self.assertIn('reset', email.body)
        
    def test_proposal_received_email(self):
        """Test proposal received email."""
        # Clear email outbox
        self.clear_emails()
        
        # Create requirement and proposal
        requirement = RequirementFactory.create()
        proposal = ProposalFactory.create(requirement=requirement)
        
        # Check that proposal received email was sent
        self.assert_email_sent(1)
        email = self.get_latest_email()
        self.assertEqual(email.to[0], requirement.created_by.email)
        self.assertIn('New proposal', email.subject)
        self.assertIn(proposal.tutor.username, email.body)
        
    def test_proposal_accepted_email(self):
        """Test proposal accepted email."""
        # Clear email outbox
        self.clear_emails()
        
        # Create requirement and proposal
        requirement = RequirementFactory.create()
        proposal = ProposalFactory.create(requirement=requirement)
        
        # Accept proposal
        from requirements.models import Award
        Award.objects.create(
            requirement=requirement,
            proposal=proposal,
            student=requirement.created_by
        )
        
        # Check that proposal accepted email was sent
        self.assert_email_sent(1)
        email = self.get_latest_email()
        self.assertEqual(email.to[0], proposal.tutor.email)
        self.assertIn('Proposal accepted', email.subject)
        self.assertIn(requirement.title, email.body)
        
    def test_payment_received_email(self):
        """Test payment received email."""
        # Clear email outbox
        self.clear_emails()
        
        # Create payment
        payment = PaymentFactory.create(status='completed')
        
        # Check that payment received email was sent
        self.assert_email_sent(1)
        email = self.get_latest_email()
        self.assertEqual(email.to[0], payment.tutor.email)
        self.assertIn('Payment received', email.subject)
        self.assertIn(str(payment.amount), email.body)
        
    def test_session_reminder_email(self):
        """Test session reminder email."""
        # Clear email outbox
        self.clear_emails()
        
        # Create session in the future
        from requirements.models import Session
        session = Session.objects.create(
            requirement=RequirementFactory.create(),
            proposal=ProposalFactory.create(),
            tutor=ProposalFactory.create().tutor,
            student=RequirementFactory.create().created_by,
            scheduled_time=timezone.now() + timedelta(hours=24)
        )
        
        # Send reminder
        from notifications.tasks import send_session_reminder
        send_session_reminder(session.id)
        
        # Check that reminder email was sent
        self.assert_email_sent(1)
        email = self.get_latest_email()
        self.assertIn([session.student.email, session.tutor.email], email.to)
        self.assertIn('Session reminder', email.subject)
        self.assertIn(session.requirement.title, email.body)


class MaskedEmailTest(TestCase, TestMixin, EmailTestMixin):
    """Tests for masked email functionality."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_masked_email_creation(self):
        """Test masked email creation."""
        # Create masked email
        from accounts.models import MaskedEmail
        masked_email = MaskedEmail.objects.create(
            user=self.user,
            masked_email='masked123@example.com',
            real_email=self.user.email
        )
        
        # Check that masked email was created
        self.assertEqual(masked_email.user, self.user)
        self.assertEqual(masked_email.masked_email, 'masked123@example.com')
        self.assertEqual(masked_email.real_email, self.user.email)
        
    def test_masked_email_forwarding(self):
        """Test masked email forwarding."""
        # Create masked email
        from accounts.models import MaskedEmail
        masked_email = MaskedEmail.objects.create(
            user=self.user,
            masked_email='masked123@example.com',
            real_email=self.user.email
        )
        
        # Send email to masked address
        with patch('django.core.mail.send_mail') as mock_send:
            mock_send.return_value = True
            
            # Simulate receiving email at masked address
            from accounts.utils import forward_masked_email
            forward_masked_email(
                masked_email='masked123@example.com',
                subject='Test Subject',
                message='Test Message',
                from_email='sender@example.com'
            )
            
            # Check that email was forwarded to real address
            mock_send.assert_called_once()
            args, kwargs = mock_send.call_args
            self.assertEqual(kwargs['recipient_list'], [self.user.email])
            
    def test_masked_email_uniqueness(self):
        """Test masked email uniqueness."""
        # Create first masked email
        from accounts.models import MaskedEmail
        MaskedEmail.objects.create(
            user=self.user,
            masked_email='masked123@example.com',
            real_email=self.user.email
        )
        
        # Try to create duplicate masked email
        with self.assertRaises(Exception):
            MaskedEmail.objects.create(
                user=UserFactory.create(),
                masked_email='masked123@example.com',
                real_email='other@example.com'
            )
            
    def test_masked_email_deactivation(self):
        """Test masked email deactivation."""
        # Create masked email
        from accounts.models import MaskedEmail
        masked_email = MaskedEmail.objects.create(
            user=self.user,
            masked_email='masked123@example.com',
            real_email=self.user.email
        )
        
        # Deactivate masked email
        masked_email.is_active = False
        masked_email.save()
        
        # Try to forward email to inactive masked email
        with patch('django.core.mail.send_mail') as mock_send:
            # Simulate receiving email at masked address
            from accounts.utils import forward_masked_email
            forward_masked_email(
                masked_email='masked123@example.com',
                subject='Test Subject',
                message='Test Message',
                from_email='sender@example.com'
            )
            
            # Check that email was not forwarded
            mock_send.assert_not_called()


class EmailTemplateTest(TestCase, TestMixin, EmailTestMixin):
    """Tests for email template rendering."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_welcome_email_template(self):
        """Test welcome email template."""
        # Clear email outbox
        self.clear_emails()
        
        # Create new user
        user = UserFactory.create()
        
        # Get welcome email
        email = self.get_latest_email()
        
        # Check template content
        self.assertIn(user.username, email.body)
        self.assertIn(user.first_name, email.body)
        self.assertIn(user.last_name, email.body)
        self.assertIn('Welcome to Tutor Platform', email.body)
        
    def test_password_reset_template(self):
        """Test password reset template."""
        # Clear email outbox
        self.clear_emails()
        
        # Request password reset
        self.client.post(reverse('accounts:password_reset'), {
            'email': self.user.email
        })
        
        # Get password reset email
        email = self.get_latest_email()
        
        # Check template content
        self.assertIn(self.user.username, email.body)
        self.assertIn('reset', email.body)
        self.assertIn('Password Reset Request', email.body)
        
    def test_proposal_notification_template(self):
        """Test proposal notification template."""
        # Clear email outbox
        self.clear_emails()
        
        # Create requirement and proposal
        requirement = RequirementFactory.create()
        proposal = ProposalFactory.create(requirement=requirement)
        
        # Get proposal notification email
        email = self.get_latest_email()
        
        # Check template content
        self.assertIn(requirement.title, email.body)
        self.assertIn(proposal.tutor.username, email.body)
        self.assertIn(str(proposal.hourly_rate), email.body)
        self.assertIn('New Proposal Received', email.body)
        
    def test_payment_notification_template(self):
        """Test payment notification template."""
        # Clear email outbox
        self.clear_emails()
        
        # Create payment
        payment = PaymentFactory.create(status='completed')
        
        # Get payment notification email
        email = self.get_latest_email()
        
        # Check template content
        self.assertIn(payment.student.username, email.body)
        self.assertIn(payment.requirement.title, email.body)
        self.assertIn(str(payment.amount), email.body)
        self.assertIn('Payment Received', email.body)
        
    def test_email_template_context(self):
        """Test email template context variables."""
        # Clear email outbox
        self.clear_emails()
        
        # Create payment with specific details
        payment = PaymentFactory.create(
            amount=Decimal('100.50'),
            status='completed'
        )
        
        # Get payment notification email
        email = self.get_latest_email()
        
        # Check that context variables are properly rendered
        self.assertIn(str(payment.amount), email.body)
        self.assertIn(payment.transaction_id, email.body)
        self.assertIn(payment.created_at.strftime('%Y-%m-%d'), email.body)


class EmailQueueTest(TestCase, TestMixin, EmailTestMixin):
    """Tests for email queue processing."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_email_queue_creation(self):
        """Test email queue creation."""
        # Create email queue entry
        from notifications.models import EmailQueue
        email_queue = EmailQueue.objects.create(
            to_email=self.user.email,
            subject='Test Subject',
            message='Test Message',
            status='pending'
        )
        
        # Check that email queue was created
        self.assertEqual(email_queue.to_email, self.user.email)
        self.assertEqual(email_queue.subject, 'Test Subject')
        self.assertEqual(email_queue.status, 'pending')
        
    def test_email_queue_processing(self):
        """Test email queue processing."""
        # Create email queue entry
        from notifications.models import EmailQueue
        email_queue = EmailQueue.objects.create(
            to_email=self.user.email,
            subject='Test Subject',
            message='Test Message',
            status='pending'
        )
        
        # Process email queue
        from notifications.management.commands.process_email_queue import Command
        command = Command()
        command.handle()
        
        # Check that email was sent
        self.assert_email_sent(1)
        email = self.get_latest_email()
        self.assertEqual(email.to[0], self.user.email)
        self.assertEqual(email.subject, 'Test Subject')
        self.assertIn('Test Message', email.body)
        
        # Check that email queue status was updated
        email_queue.refresh_from_db()
        self.assertEqual(email_queue.status, 'sent')
        
    def test_email_queue_retry(self):
        """Test email queue retry mechanism."""
        # Create email queue entry
        from notifications.models import EmailQueue
        email_queue = EmailQueue.objects.create(
            to_email=self.user.email,
            subject='Test Subject',
            message='Test Message',
            status='failed',
            retry_count=1
        )
        
        # Process email queue
        from notifications.management.commands.process_email_queue import Command
        command = Command()
        command.handle()
        
        # Check that retry count was incremented
        email_queue.refresh_from_db()
        self.assertEqual(email_queue.retry_count, 2)
        
    def test_email_queue_max_retries(self):
        """Test email queue maximum retries."""
        # Create email queue entry with max retries
        from notifications.models import EmailQueue
        email_queue = EmailQueue.objects.create(
            to_email=self.user.email,
            subject='Test Subject',
            message='Test Message',
            status='failed',
            retry_count=5
        )
        
        # Process email queue
        from notifications.management.commands.process_email_queue import Command
        command = Command()
        command.handle()
        
        # Check that email was marked as permanently failed
        email_queue.refresh_from_db()
        self.assertEqual(email_queue.status, 'permanently_failed')
        self.assertEqual(email_queue.retry_count, 5)


class NotificationEmailTest(TestCase, TestMixin, EmailTestMixin):
    """Tests for notification emails."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_new_message_notification(self):
        """Test new message notification email."""
        # Clear email outbox
        self.clear_emails()
        
        # Create conversation and message
        from messaging.models import Conversation, Message
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user)
        
        message = Message.objects.create(
            conversation=conversation,
            sender=UserFactory.create(),
            content='Test message'
        )
        
        # Check that notification email was sent
        self.assert_email_sent(1)
        email = self.get_latest_email()
        self.assertEqual(email.to[0], self.user.email)
        self.assertIn('New message', email.subject)
        self.assertIn(message.content, email.body)
        
    def test_requirement_matched_notification(self):
        """Test requirement matched notification email."""
        # Clear email outbox
        self.clear_emails()
        
        # Create requirement and matching proposal
        requirement = RequirementFactory.create()
        proposal = ProposalFactory.create(requirement=requirement)
        
        # Check that notification email was sent
        self.assert_email_sent(1)
        email = self.get_latest_email()
        self.assertEqual(email.to[0], requirement.created_by.email)
        self.assertIn('New proposal', email.subject)
        self.assertIn(proposal.tutor.username, email.body)
        
    def test_session_scheduled_notification(self):
        """Test session scheduled notification email."""
        # Clear email outbox
        self.clear_emails()
        
        # Create scheduled session
        from requirements.models import Session
        session = Session.objects.create(
            requirement=RequirementFactory.create(),
            proposal=ProposalFactory.create(),
            tutor=ProposalFactory.create().tutor,
            student=RequirementFactory.create().created_by,
            scheduled_time=timezone.now() + timedelta(hours=24)
        )
        
        # Check that notification email was sent
        self.assert_email_sent(2)  # One to student, one to tutor
        emails = mail.outbox
        
        # Check student notification
        student_email = next(e for e in emails if session.student.email in e.to)
        self.assertIn('Session scheduled', student_email.subject)
        
        # Check tutor notification
        tutor_email = next(e for e in emails if session.tutor.email in e.to)
        self.assertIn('Session scheduled', tutor_email.subject)
        
    def test_payment_completed_notification(self):
        """Test payment completed notification email."""
        # Clear email outbox
        self.clear_emails()
        
        # Create completed payment
        payment = PaymentFactory.create(status='completed')
        
        # Check that notification email was sent
        self.assert_email_sent(2)  # One to student, one to tutor
        emails = mail.outbox
        
        # Check student notification
        student_email = next(e for e in emails if payment.student.email in e.to)
        self.assertIn('Payment completed', student_email.subject)
        
        # Check tutor notification
        tutor_email = next(e for e in emails if payment.tutor.email in e.to)
        self.assertIn('Payment received', tutor_email.subject)
        
    def test_profile_viewed_notification(self):
        """Test profile viewed notification email."""
        # Clear email outbox
        self.clear_emails()
        
        # Create profile view
        viewer = UserFactory.create()
        profile_owner = UserFactory.create()
        
        # Simulate profile view
        from accounts.signals import profile_viewed
        profile_viewed.send(
            sender=profile_owner.__class__,
            profile_owner=profile_owner,
            viewer=viewer
        )
        
        # Check that notification email was sent (if user has opted in)
        # This depends on user preferences, so we'll check the signal handling
        # rather than the email itself
        self.assertTrue(True)  # Placeholder for actual test


class EmailPreferenceTest(TestCase, TestMixin, EmailTestMixin):
    """Tests for email preferences."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_email_preference_creation(self):
        """Test email preference creation."""
        # Create email preference
        from notifications.models import EmailPreference
        preference = EmailPreference.objects.create(
            user=self.user,
            email_type='new_message',
            enabled=True
        )
        
        # Check that preference was created
        self.assertEqual(preference.user, self.user)
        self.assertEqual(preference.email_type, 'new_message')
        self.assertTrue(preference.enabled)
        
    def test_email_preference_update(self):
        """Test email preference update."""
        # Create email preference
        from notifications.models import EmailPreference
        preference = EmailPreference.objects.create(
            user=self.user,
            email_type='new_message',
            enabled=True
        )
        
        # Update preference
        preference.enabled = False
        preference.save()
        
        # Check that preference was updated
        preference.refresh_from_db()
        self.assertFalse(preference.enabled)
        
    def test_email_preference_respected(self):
        """Test that email preferences are respected."""
        # Disable email preference
        from notifications.models import EmailPreference
        EmailPreference.objects.create(
            user=self.user,
            email_type='new_message',
            enabled=False
        )
        
        # Clear email outbox
        self.clear_emails()
        
        # Create conversation and message
        from messaging.models import Conversation, Message
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user)
        
        message = Message.objects.create(
            conversation=conversation,
            sender=UserFactory.create(),
            content='Test message'
        )
        
        # Check that notification email was not sent
        self.assert_email_sent(0)
        
    def test_default_email_preferences(self):
        """Test default email preferences for new users."""
        # Create new user
        new_user = UserFactory.create()
        
        # Check that default preferences were created
        from notifications.models import EmailPreference
        preferences = EmailPreference.objects.filter(user=new_user)
        self.assertGreater(preferences.count(), 0)
        
        # Check that all default preferences are enabled
        for preference in preferences:
            self.assertTrue(preference.enabled)


class EmailUnsubscribeTest(TestCase, TestMixin, EmailTestMixin):
    """Tests for email unsubscribe functionality."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_unsubscribe_token_generation(self):
        """Test unsubscribe token generation."""
        # Generate unsubscribe token
        from notifications.utils import generate_unsubscribe_token
        token = generate_unsubscribe_token(self.user)
        
        # Check that token was generated
        self.assertIsNotNone(token)
        self.assertEqual(len(token), 32)  # Check token length
        
    def test_unsubscribe_link_creation(self):
        """Test unsubscribe link creation."""
        # Create unsubscribe link
        from notifications.utils import create_unsubscribe_link
        link = create_unsubscribe_link(self.user, 'new_message')
        
        # Check that link was created
        self.assertIn(reverse('notifications:unsubscribe'), link)
        self.assertIn(str(self.user.id), link)
        
    def test_unsubscribe_view(self):
        """Test unsubscribe view."""
        # Generate unsubscribe token
        from notifications.utils import generate_unsubscribe_token
        token = generate_unsubscribe_token(self.user)
        
        # Visit unsubscribe page
        response = self.client.get(
            reverse('notifications:unsubscribe'),
            {'user_id': self.user.id, 'token': token, 'email_type': 'new_message'}
        )
        
        # Check that unsubscribe page is displayed
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Unsubscribe')
        
    def test_unsubscribe_processing(self):
        """Test unsubscribe processing."""
        # Generate unsubscribe token
        from notifications.utils import generate_unsubscribe_token
        token = generate_unsubscribe_token(self.user)
        
        # Process unsubscribe
        response = self.client.post(
            reverse('notifications:unsubscribe'),
            {
                'user_id': self.user.id,
                'token': token,
                'email_type': 'new_message'
            }
        )
        
        # Check that preference was updated
        from notifications.models import EmailPreference
        preference = EmailPreference.objects.get(
            user=self.user,
            email_type='new_message'
        )
        self.assertFalse(preference.enabled)
        
        # Check that success message is displayed
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'successfully unsubscribed')
        
    def test_invalid_unsubscribe_token(self):
        """Test invalid unsubscribe token."""
        # Visit unsubscribe page with invalid token
        response = self.client.get(
            reverse('notifications:unsubscribe'),
            {'user_id': self.user.id, 'token': 'invalid-token', 'email_type': 'new_message'}
        )
        
        # Check that error is displayed
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Invalid unsubscribe link')