"""
Unit tests for utility functions across all apps.
"""
import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from unittest.mock import patch, MagicMock

from accounts.utils import (
    get_user_profile, is_tutor, is_student, generate_username,
    send_welcome_email, mask_email
)
from requirements.utils import (
    calculate_proposal_score, get_matching_tutors, filter_requirements,
    get_requirement_stats
)
from messaging.utils import (
    create_conversation, send_message, get_unread_count,
    get_conversation_participants, mask_message_content
)
from paymentsdetails.utils import (
    calculate_commission, process_payment, refund_payment,
    get_payment_stats, validate_payment_method
)
from notifications.utils import (
    create_notification, send_push_notification,
    batch_notifications, get_notification_stats
)
from search.utils import (
    index_requirement, search_requirements, get_search_suggestions,
    get_popular_searches
)

from tests.factories import (
    UserFactory, TutorProfileFactory, StudentProfileFactory, CategoryFactory,
    SubjectFactory, RequirementFactory, ProposalFactory, PaymentFactory
)
from tests.utils.helpers import TestMixin


class AccountsUtilsTest(TestCase, TestMixin):
    """Test cases for accounts utility functions."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.student_user = UserFactory.create(user_type='STUDENT')
        
    def test_get_user_profile_tutor(self):
        """Test get_user_profile for tutor."""
        tutor_profile = TutorProfileFactory.create(user=self.tutor_user)
        profile = get_user_profile(self.tutor_user)
        self.assertEqual(profile, tutor_profile)
        
    def test_get_user_profile_student(self):
        """Test get_user_profile for student."""
        student_profile = StudentProfileFactory.create(user=self.student_user)
        profile = get_user_profile(self.student_user)
        self.assertEqual(profile, student_profile)
        
    def test_get_user_profile_no_profile(self):
        """Test get_user_profile for user without profile."""
        profile = get_user_profile(self.user)
        self.assertIsNone(profile)
        
    def test_is_tutor_true(self):
        """Test is_tutor returns True for tutor."""
        self.assertTrue(is_tutor(self.tutor_user))
        
    def test_is_tutor_false(self):
        """Test is_tutor returns False for non-tutor."""
        self.assertFalse(is_tutor(self.student_user))
        self.assertFalse(is_tutor(self.user))
        
    def test_is_student_true(self):
        """Test is_student returns True for student."""
        self.assertTrue(is_student(self.student_user))
        
    def test_is_student_false(self):
        """Test is_student returns False for non-student."""
        self.assertFalse(is_student(self.tutor_user))
        self.assertFalse(is_student(self.user))
        
    def test_generate_username_from_email(self):
        """Test generate_username from email."""
        username = generate_username('john.doe@example.com')
        self.assertEqual(username, 'john.doe')
        
    def test_generate_username_from_names(self):
        """Test generate_username from names."""
        username = generate_username(first_name='John', last_name='Doe')
        self.assertEqual(username, 'john.doe')
        
    def test_generate_username_with_existing(self):
        """Test generate_username with existing username."""
        # Create user with username 'john.doe'
        UserFactory.create(username='john.doe')
        
        # Generate username for new user with same name
        username = generate_username(first_name='John', last_name='Doe')
        
        # Should append number to make it unique
        self.assertNotEqual(username, 'john.doe')
        self.assertTrue(username.startswith('john.doe'))
        
    @patch('accounts.utils.send_mail')
    def test_send_welcome_email(self, mock_send_mail):
        """Test send_welcome_email function."""
        send_welcome_email(self.user)
        
        # Check that send_mail was called
        mock_send_mail.assert_called_once()
        
        # Check call arguments
        args, kwargs = mock_send_mail.call_args
        self.assertIn('Welcome', args[0])  # Subject contains 'Welcome'
        self.assertEqual(args[1], self.user.email)  # To email
        
    def test_mask_email(self):
        """Test mask_email function."""
        email = 'john.doe@example.com'
        masked = mask_email(email)
        self.assertEqual(masked, 'j***@example.com')
        
    def test_mask_email_short(self):
        """Test mask_email function with short username."""
        email = 'jd@example.com'
        masked = mask_email(email)
        self.assertEqual(masked, 'j***@example.com')
        
    def test_mask_email_invalid(self):
        """Test mask_email function with invalid email."""
        email = 'invalid-email'
        masked = mask_email(email)
        self.assertEqual(masked, email)  # Should return as is


class RequirementsUtilsTest(TestCase, TestMixin):
    """Test cases for requirements utility functions."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_profile = TutorProfileFactory.create(user=self.tutor_user)
        self.category = CategoryFactory.create()
        self.subject = SubjectFactory.create(category=self.category)
        self.requirement = RequirementFactory.create(
            subject=self.subject,
            created_by=self.student_user
        )
        
    def test_calculate_proposal_score_perfect_match(self):
        """Test calculate_proposal_score with perfect match."""
        proposal = ProposalFactory.create(
            requirement=self.requirement,
            hourly_rate=self.requirement.budget / self.requirement.hours_per_week,
            created_by=self.tutor_user
        )
        
        score = calculate_proposal_score(proposal)
        self.assertGreater(score, 80)  # Should be high score for perfect match
        
    def test_calculate_proposal_score_price_mismatch(self):
        """Test calculate_proposal_score with price mismatch."""
        proposal = ProposalFactory.create(
            requirement=self.requirement,
            hourly_rate=self.requirement.budget * 2,  # Double the budget
            created_by=self.tutor_user
        )
        
        score = calculate_proposal_score(proposal)
        self.assertLess(score, 50)  # Should be low score for price mismatch
        
    def test_get_matching_tutors_by_subject(self):
        """Test get_matching_tutors by subject."""
        # Create tutor with matching subject
        matching_tutor = UserFactory.create(user_type='TUTOR')
        matching_profile = TutorProfileFactory.create(
            user=matching_tutor,
            subjects=self.subject.name
        )
        
        # Create tutor with different subject
        other_tutor = UserFactory.create(user_type='TUTOR')
        other_subject = SubjectFactory.create()
        other_profile = TutorProfileFactory.create(
            user=other_tutor,
            subjects=other_subject.name
        )
        
        matching_tutors = get_matching_tutors(self.requirement)
        self.assertIn(matching_tutor, matching_tutors)
        self.assertNotIn(other_tutor, matching_tutors)
        
    def test_get_matching_tutors_by_budget(self):
        """Test get_matching_tutors by budget."""
        # Create tutor with matching hourly rate
        matching_tutor = UserFactory.create(user_type='TUTOR')
        matching_profile = TutorProfileFactory.create(
            user=matching_tutor,
            hourly_rate=self.requirement.budget / self.requirement.hours_per_week
        )
        
        # Create tutor with higher hourly rate
        expensive_tutor = UserFactory.create(user_type='TUTOR')
        expensive_profile = TutorProfileFactory.create(
            user=expensive_tutor,
            hourly_rate=self.requirement.budget * 2
        )
        
        matching_tutors = get_matching_tutors(self.requirement)
        self.assertIn(matching_tutor, matching_tutors)
        self.assertNotIn(expensive_tutor, matching_tutors)
        
    def test_filter_requirements_by_category(self):
        """Test filter_requirements by category."""
        # Create requirements in different categories
        req1 = RequirementFactory.create(subject=self.subject)
        other_category = CategoryFactory.create()
        other_subject = SubjectFactory.create(category=other_category)
        req2 = RequirementFactory.create(subject=other_subject)
        
        filtered = filter_requirements(category=self.category.id)
        self.assertIn(req1, filtered)
        self.assertNotIn(req2, filtered)
        
    def test_filter_requirements_by_budget_range(self):
        """Test filter_requirements by budget range."""
        # Create requirements with different budgets
        req1 = RequirementFactory.create(budget=50)
        req2 = RequirementFactory.create(budget=100)
        req3 = RequirementFactory.create(budget=150)
        
        filtered = filter_requirements(min_budget=75, max_budget=125)
        self.assertIn(req2, filtered)
        self.assertNotIn(req1, filtered)
        self.assertNotIn(req3, filtered)
        
    def test_get_requirement_stats(self):
        """Test get_requirement_stats function."""
        # Create requirements with different statuses
        open_req = RequirementFactory.create(is_closed=False)
        closed_req = RequirementFactory.create(is_closed=True)
        
        # Create proposals
        ProposalFactory.create_batch(3, requirement=open_req)
        ProposalFactory.create_batch(2, requirement=closed_req)
        
        stats = get_requirement_stats()
        
        self.assertEqual(stats['total_requirements'], 2)
        self.assertEqual(stats['open_requirements'], 1)
        self.assertEqual(stats['closed_requirements'], 1)
        self.assertEqual(stats['total_proposals'], 5)


class MessagingUtilsTest(TestCase, TestMixin):
    """Test cases for messaging utility functions."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user1 = UserFactory.create()
        self.user2 = UserFactory.create()
        
    def test_create_conversation(self):
        """Test create_conversation function."""
        conversation = create_conversation(
            participants=[self.user1, self.user2],
            subject='Test Conversation'
        )
        
        self.assertEqual(conversation.subject, 'Test Conversation')
        self.assertEqual(conversation.participants.count(), 2)
        self.assertIn(self.user1, conversation.participants.all())
        self.assertIn(self.user2, conversation.participants.all())
        
    def test_send_message(self):
        """Test send_message function."""
        conversation = create_conversation(
            participants=[self.user1, self.user2],
            subject='Test Conversation'
        )
        
        message = send_message(
            conversation=conversation,
            sender=self.user1,
            content='Hello, this is a test message'
        )
        
        self.assertEqual(message.conversation, conversation)
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.content, 'Hello, this is a test message')
        
    def test_get_unread_count(self):
        """Test get_unread_count function."""
        conversation = create_conversation(
            participants=[self.user1, self.user2],
            subject='Test Conversation'
        )
        
        # Send messages
        send_message(conversation, self.user1, 'Message 1')
        send_message(conversation, self.user1, 'Message 2')
        send_message(conversation, self.user1, 'Message 3')
        
        # Get unread count for user2
        unread_count = get_unread_count(self.user2, conversation)
        self.assertEqual(unread_count, 3)
        
        # Mark one as read
        messages = conversation.messages.all()
        messages[0].mark_as_read()
        
        # Get updated unread count
        unread_count = get_unread_count(self.user2, conversation)
        self.assertEqual(unread_count, 2)
        
    def test_get_conversation_participants(self):
        """Test get_conversation_participants function."""
        conversation = create_conversation(
            participants=[self.user1, self.user2],
            subject='Test Conversation'
        )
        
        participants = get_conversation_participants(conversation)
        self.assertEqual(len(participants), 2)
        self.assertIn(self.user1, participants)
        self.assertIn(self.user2, participants)
        
    def test_mask_message_content(self):
        """Test mask_message_content function."""
        content = 'This is a long message that should be truncated for preview purposes'
        masked = mask_message_content(content, length=30)
        self.assertEqual(masked, 'This is a long message that sh...')
        
    def test_mask_message_content_short(self):
        """Test mask_message_content function with short content."""
        content = 'Short message'
        masked = mask_message_content(content, length=30)
        self.assertEqual(masked, content)


class PaymentsdetailsUtilsTest(TestCase, TestMixin):
    """Test cases for paymentsdetails utility functions."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_calculate_commission(self):
        """Test calculate_commission function."""
        amount = 100.00
        commission_rate = 0.10  # 10%
        
        commission = calculate_commission(amount, commission_rate)
        self.assertEqual(commission, 10.00)
        
    def test_calculate_commission_with_minimum(self):
        """Test calculate_commission function with minimum fee."""
        amount = 5.00
        commission_rate = 0.10  # 10%
        minimum_fee = 1.00
        
        commission = calculate_commission(amount, commission_rate, minimum_fee)
        self.assertEqual(commission, 1.00)  # Should use minimum fee
        
    def test_calculate_commission_with_maximum(self):
        """Test calculate_commission function with maximum fee."""
        amount = 1000.00
        commission_rate = 0.10  # 10%
        maximum_fee = 50.00
        
        commission = calculate_commission(amount, commission_rate, maximum=maximum_fee)
        self.assertEqual(commission, 50.00)  # Should use maximum fee
        
    @patch('paymentsdetails.utils.PaymentProcessor.process')
    def test_process_payment(self, mock_process):
        """Test process_payment function."""
        payment = PaymentFactory.create(amount=100.00)
        
        # Mock successful payment
        mock_process.return_value = {'status': 'success', 'transaction_id': '12345'}
        
        result = process_payment(payment)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['transaction_id'], '12345')
        
        # Check that payment status was updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'COMPLETED')
        
    @patch('paymentsdetails.utils.PaymentProcessor.process')
    def test_process_payment_failure(self, mock_process):
        """Test process_payment function with failure."""
        payment = PaymentFactory.create(amount=100.00)
        
        # Mock failed payment
        mock_process.return_value = {'status': 'failed', 'error': 'Insufficient funds'}
        
        result = process_payment(payment)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Insufficient funds')
        
        # Check that payment status was updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'FAILED')
        
    @patch('paymentsdetails.utils.PaymentProcessor.refund')
    def test_refund_payment(self, mock_refund):
        """Test refund_payment function."""
        payment = PaymentFactory.create(
            amount=100.00,
            status='COMPLETED',
            transaction_id='12345'
        )
        
        # Mock successful refund
        mock_refund.return_value = {
            'status': 'success',
            'refund_id': '67890'
        }
        
        result = refund_payment(payment)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['refund_id'], '67890')
        
        # Check that payment status was updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'REFUNDED')
        
    def test_get_payment_stats(self):
        """Test get_payment_stats function."""
        # Create payments with different statuses
        completed_payment = PaymentFactory.create(status='COMPLETED', amount=100.00)
        pending_payment = PaymentFactory.create(status='PENDING', amount=50.00)
        failed_payment = PaymentFactory.create(status='FAILED', amount=25.00)
        refunded_payment = PaymentFactory.create(status='REFUNDED', amount=75.00)
        
        stats = get_payment_stats()
        
        self.assertEqual(stats['total_payments'], 4)
        self.assertEqual(stats['completed_payments'], 1)
        self.assertEqual(stats['pending_payments'], 1)
        self.assertEqual(stats['failed_payments'], 1)
        self.assertEqual(stats['refunded_payments'], 1)
        self.assertEqual(stats['total_amount'], 250.00)
        self.assertEqual(stats['completed_amount'], 100.00)
        
    def test_validate_payment_method_valid(self):
        """Test validate_payment_method function with valid method."""
        method_data = {
            'type': 'PAYPAL',
            'email': 'user@example.com'
        }
        
        result = validate_payment_method(method_data)
        self.assertTrue(result['valid'])
        
    def test_validate_payment_method_invalid(self):
        """Test validate_payment_method function with invalid method."""
        method_data = {
            'type': 'PAYPAL',
            'email': 'invalid-email'
        }
        
        result = validate_payment_method(method_data)
        self.assertFalse(result['valid'])
        self.assertIn('email', result['errors'])


class NotificationsUtilsTest(TestCase, TestMixin):
    """Test cases for notifications utility functions."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_create_notification(self):
        """Test create_notification function."""
        notification = create_notification(
            recipient=self.user,
            title='Test Notification',
            message='This is a test notification',
            notification_type='INFO'
        )
        
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.title, 'Test Notification')
        self.assertEqual(notification.message, 'This is a test notification')
        self.assertEqual(notification.notification_type, 'INFO')
        
    @patch('notifications.utils.PushService.send')
    def test_send_push_notification(self, mock_send):
        """Test send_push_notification function."""
        # Create user with push token
        self.user.push_token = 'test-push-token'
        self.user.save()
        
        notification = create_notification(
            recipient=self.user,
            title='Test Notification',
            message='This is a test notification',
            notification_type='INFO'
        )
        
        # Mock successful push
        mock_send.return_value = {'status': 'success'}
        
        result = send_push_notification(notification)
        
        self.assertTrue(result['success'])
        mock_send.assert_called_once()
        
    def test_batch_notifications(self):
        """Test batch_notifications function."""
        users = UserFactory.create_batch(3)
        
        notifications = batch_notifications(
            recipients=users,
            title='Batch Notification',
            message='This is a batch notification',
            notification_type='INFO'
        )
        
        self.assertEqual(len(notifications), 3)
        
        for i, user in enumerate(users):
            self.assertEqual(notifications[i].recipient, user)
            self.assertEqual(notifications[i].title, 'Batch Notification')
            self.assertEqual(notifications[i].message, 'This is a batch notification')
            self.assertEqual(notifications[i].notification_type, 'INFO')
            
    def test_get_notification_stats(self):
        """Test get_notification_stats function."""
        # Create notifications with different types
        info_notification = create_notification(
            recipient=self.user,
            title='Info Notification',
            message='Info message',
            notification_type='INFO'
        )
        
        alert_notification = create_notification(
            recipient=self.user,
            title='Alert Notification',
            message='Alert message',
            notification_type='ALERT'
        )
        
        # Mark one as read
        info_notification.mark_as_read()
        
        stats = get_notification_stats(self.user)
        
        self.assertEqual(stats['total_notifications'], 2)
        self.assertEqual(stats['unread_notifications'], 1)
        self.assertEqual(stats['read_notifications'], 1)
        self.assertEqual(stats['info_notifications'], 1)
        self.assertEqual(stats['alert_notifications'], 1)


class SearchUtilsTest(TestCase, TestMixin):
    """Test cases for search utility functions."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.category = CategoryFactory.create()
        self.subject = SubjectFactory.create(category=self.category)
        self.requirement = RequirementFactory.create(
            title='Python Programming Tutor',
            subject=self.subject
        )
        
    def test_index_requirement(self):
        """Test index_requirement function."""
        result = index_requirement(self.requirement)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['indexed_id'], self.requirement.id)
        
    def test_search_requirements_by_title(self):
        """Test search_requirements by title."""
        # Create requirements
        python_req = RequirementFactory.create(title='Python Programming Tutor')
        math_req = RequirementFactory.create(title='Mathematics Tutor')
        
        # Search for 'Python'
        results = search_requirements('Python')
        
        self.assertIn(python_req, results)
        self.assertNotIn(math_req, results)
        
    def test_search_requirements_by_description(self):
        """Test search_requirements by description."""
        # Create requirements
        python_req = RequirementFactory.create(
            title='Programming Tutor',
            description='Need help with Python programming'
        )
        math_req = RequirementFactory.create(
            title='Mathematics Tutor',
            description='Need help with calculus'
        )
        
        # Search for 'Python'
        results = search_requirements('Python')
        
        self.assertIn(python_req, results)
        self.assertNotIn(math_req, results)
        
    def test_get_search_suggestions(self):
        """Test get_search_suggestions function."""
        # Create requirements
        RequirementFactory.create(title='Python Programming Tutor')
        RequirementFactory.create(title='Python Web Development')
        RequirementFactory.create(title='Mathematics Tutor')
        
        # Get suggestions for 'Python'
        suggestions = get_search_suggestions('Python')
        
        self.assertIn('Python Programming Tutor', suggestions)
        self.assertIn('Python Web Development', suggestions)
        self.assertNotIn('Mathematics Tutor', suggestions)
        
    def test_get_popular_searches(self):
        """Test get_popular_searches function."""
        # This would typically query a search history table
        # For testing, we'll mock the data
        
        with patch('search.utils.SearchQuery.objects.popular') as mock_popular:
            mock_popular.return_value = [
                {'query': 'Python programming', 'count': 10},
                {'query': 'Mathematics tutor', 'count': 8},
                {'query': 'Web development', 'count': 5}
            ]
            
            popular = get_popular_searches()
            
            self.assertEqual(len(popular), 3)
            self.assertEqual(popular[0]['query'], 'Python programming')
            self.assertEqual(popular[0]['count'], 10)