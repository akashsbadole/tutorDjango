"""
API tests for all endpoints.
"""
import pytest
import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from tests.factories import (
    UserFactory, TutorProfileFactory, StudentProfileFactory, CategoryFactory,
    SubjectFactory, RequirementFactory, ProposalFactory, PaymentFactory
)
from tests.utils.helpers import TestMixin, APITestMixin

User = get_user_model()


class AuthenticationAPITest(TestCase, APITestMixin):
    """API tests for authentication endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = APIClient()
        self.user = UserFactory.create()
        self.user.set_password('testpass123')
        self.user.save()
        
    def test_api_login_valid_credentials(self):
        """Test API login with valid credentials."""
        url = reverse('api:login')
        data = {
            'username': self.user.username,
            'password': 'testpass123'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        
    def test_api_login_invalid_credentials(self):
        """Test API login with invalid credentials."""
        url = reverse('api:login')
        data = {
            'username': self.user.username,
            'password': 'wrongpassword'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('token', response.data)
        
    def test_api_logout(self):
        """Test API logout."""
        # Login and get token
        token = Token.objects.get_or_create(user=self.user)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        url = reverse('api:logout')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check token was deleted
        self.assertFalse(Token.objects.filter(key=token.key).exists())
        
    def test_api_registration(self):
        """Test API registration."""
        url = reverse('api:register')
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'testpass123',
            'first_name': 'New',
            'last_name': 'User',
            'user_type': 'STUDENT'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        
        # Check user was created
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertEqual(user.user_type, 'STUDENT')


class UserAPITest(TestCase, APITestMixin):
    """API tests for user endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = APIClient()
        self.user = UserFactory.create()
        self.token = Token.objects.get_or_create(user=self.user)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
    def test_get_user_profile(self):
        """Test getting user profile."""
        url = reverse('api:user-profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user.username)
        self.assertEqual(response.data['email'], self.user.email)
        
    def test_update_user_profile(self):
        """Test updating user profile."""
        url = reverse('api:user-profile')
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'bio': 'Updated bio'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')
        self.assertEqual(response.data['last_name'], 'Name')
        self.assertEqual(response.data['email'], 'updated@example.com')
        self.assertEqual(response.data['bio'], 'Updated bio')
        
    def test_get_user_profile_unauthorized(self):
        """Test getting user profile without authentication."""
        self.client.credentials()  # Remove authentication
        
        url = reverse('api:user-profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RequirementAPITest(TestCase, APITestMixin):
    """API tests for requirement endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = APIClient()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.category = CategoryFactory.create()
        self.subject = SubjectFactory.create(category=self.category)
        self.requirement = RequirementFactory.create(
            subject=self.subject,
            created_by=self.student_user
        )
        self.token = Token.objects.get_or_create(user=self.student_user)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
    def test_get_requirements_list(self):
        """Test getting requirements list."""
        url = reverse('api:requirement-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.requirement.id)
        
    def test_get_requirement_detail(self):
        """Test getting requirement detail."""
        url = reverse('api:requirement-detail', kwargs={'pk': self.requirement.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.requirement.id)
        self.assertEqual(response.data['title'], self.requirement.title)
        
    def test_create_requirement(self):
        """Test creating a requirement."""
        url = reverse('api:requirement-list')
        data = {
            'title': 'Python Programming Tutor',
            'description': 'Need help with Python programming',
            'category': self.category.id,
            'subject': self.subject.id,
            'budget': 50.00,
            'duration_weeks': 4,
            'hours_per_week': 2,
            'location': 'Online',
            'requirements': 'Basic Python knowledge'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Python Programming Tutor')
        self.assertEqual(response.data['created_by']['id'], self.student_user.id)
        
    def test_create_requirement_unauthorized(self):
        """Test creating a requirement without authentication."""
        self.client.credentials()  # Remove authentication
        
        url = reverse('api:requirement-list')
        data = {
            'title': 'Python Programming Tutor',
            'description': 'Need help with Python programming',
            'category': self.category.id,
            'subject': self.subject.id,
            'budget': 50.00,
            'duration_weeks': 4,
            'hours_per_week': 2,
            'location': 'Online',
            'requirements': 'Basic Python knowledge'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_update_requirement(self):
        """Test updating a requirement."""
        url = reverse('api:requirement-detail', kwargs={'pk': self.requirement.pk})
        data = {
            'title': 'Updated Python Programming Tutor',
            'budget': 75.00
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Python Programming Tutor')
        self.assertEqual(response.data['budget'], 75.00)
        
    def test_delete_requirement(self):
        """Test deleting a requirement."""
        url = reverse('api:requirement-detail', kwargs={'pk': self.requirement.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Check requirement was deleted
        self.assertFalse(Requirement.objects.filter(pk=self.requirement.pk).exists())
        
    def test_filter_requirements_by_subject(self):
        """Test filtering requirements by subject."""
        url = reverse('api:requirement-list')
        response = self.client.get(url, {'subject': self.subject.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.requirement.id)
        
    def test_search_requirements(self):
        """Test searching requirements."""
        url = reverse('api:requirement-list')
        response = self.client.get(url, {'search': 'Python'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.requirement.id)


class ProposalAPITest(TestCase, APITestMixin):
    """API tests for proposal endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = APIClient()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.tutor_profile = TutorProfileFactory.create(user=self.tutor_user)
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        self.proposal = ProposalFactory.create(
            requirement=self.requirement,
            created_by=self.tutor_user
        )
        self.token = Token.objects.get_or_create(user=self.tutor_user)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
    def test_get_proposals_list(self):
        """Test getting proposals list."""
        url = reverse('api:proposal-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.proposal.id)
        
    def test_get_proposal_detail(self):
        """Test getting proposal detail."""
        url = reverse('api:proposal-detail', kwargs={'pk': self.proposal.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.proposal.id)
        self.assertEqual(response.data['title'], self.proposal.title)
        
    def test_create_proposal(self):
        """Test creating a proposal."""
        new_requirement = RequirementFactory.create(created_by=self.student_user)
        
        url = reverse('api:proposal-list')
        data = {
            'requirement': new_requirement.id,
            'title': 'Python Programming Proposal',
            'description': 'I can help you with Python programming',
            'hourly_rate': 25.00,
            'total_hours': 8,
            'timeline': '2 weeks',
            'approach': 'Hands-on coding exercises',
            'qualifications': '5 years Python experience'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Python Programming Proposal')
        self.assertEqual(response.data['created_by']['id'], self.tutor_user.id)
        
    def test_create_proposal_student_forbidden(self):
        """Test creating a proposal as student (should be forbidden)."""
        # Login as student
        student_token = Token.objects.get_or_create(user=self.student_user)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {student_token.key}')
        
        url = reverse('api:proposal-list')
        data = {
            'requirement': self.requirement.id,
            'title': 'Python Programming Proposal',
            'description': 'I can help you with Python programming',
            'hourly_rate': 25.00,
            'total_hours': 8,
            'timeline': '2 weeks',
            'approach': 'Hands-on coding exercises',
            'qualifications': '5 years Python experience'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_update_proposal(self):
        """Test updating a proposal."""
        url = reverse('api:proposal-detail', kwargs={'pk': self.proposal.pk})
        data = {
            'title': 'Updated Python Programming Proposal',
            'hourly_rate': 30.00
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Python Programming Proposal')
        self.assertEqual(response.data['hourly_rate'], 30.00)
        
    def test_delete_proposal(self):
        """Test deleting a proposal."""
        url = reverse('api:proposal-detail', kwargs={'pk': self.proposal.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Check proposal was deleted
        self.assertFalse(Proposal.objects.filter(pk=self.proposal.pk).exists())


class PaymentAPITest(TestCase, APITestMixin):
    """API tests for payment endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = APIClient()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.tutor_profile = TutorProfileFactory.create(user=self.tutor_user)
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        self.proposal = ProposalFactory.create(
            requirement=self.requirement,
            created_by=self.tutor_user
        )
        
        # Create award
        from requirements.models import Award  # Import here to avoid circular imports
        self.award = AwardFactory.create(
            proposal=self.proposal,
            price=200.00
        )
        
        self.payment = PaymentFactory.create(
            award=self.award,
            amount=200.00,
            status='PENDING'
        )
        
        self.token = Token.objects.get_or_create(user=self.student_user)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
    def test_get_payments_list(self):
        """Test getting payments list."""
        url = reverse('api:payment-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.payment.id)
        
    def test_get_payment_detail(self):
        """Test getting payment detail."""
        url = reverse('api:payment-detail', kwargs={'pk': self.payment.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.payment.id)
        self.assertEqual(response.data['amount'], 200.00)
        
    def test_create_payment(self):
        """Test creating a payment."""
        # Create new award
        from requirements.models import Award  # Import here to avoid circular imports
        new_award = AwardFactory.create(price=150.00)
        
        url = reverse('api:payment-list')
        data = {
            'award': new_award.id,
            'payment_method': 'PAYPAL'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['amount'], 150.00)
        self.assertEqual(response.data['payment_method'], 'PAYPAL')
        
    def test_process_payment(self):
        """Test processing a payment."""
        url = reverse('api:payment-process', kwargs={'pk': self.payment.pk})
        data = {
            'payment_method': 'PAYPAL'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('payment_url', response.data)
        
    def test_refund_payment(self):
        """Test refunding a payment."""
        # Mark payment as completed
        self.payment.status = 'COMPLETED'
        self.payment.save()
        
        url = reverse('api:payment-refund', kwargs={'pk': self.payment.pk})
        data = {
            'reason': 'Tutor did not complete the work'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('refund_id', response.data)


class MessagingAPITest(TestCase, APITestMixin):
    """API tests for messaging endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = APIClient()
        self.user1 = UserFactory.create()
        self.user2 = UserFactory.create()
        
        # Create conversation
        from messaging.models import Conversation  # Import here to avoid circular imports
        self.conversation = ConversationFactory.create()
        self.conversation.participants.add(self.user1, self.user2)
        
        # Create message
        from messaging.models import Message  # Import here to avoid circular imports
        self.message = MessageFactory.create(
            conversation=self.conversation,
            sender=self.user1
        )
        
        self.token = Token.objects.get_or_create(user=self.user1)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
    def test_get_conversations_list(self):
        """Test getting conversations list."""
        url = reverse('api:conversation-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.conversation.id)
        
    def test_get_conversation_detail(self):
        """Test getting conversation detail."""
        url = reverse('api:conversation-detail', kwargs={'pk': self.conversation.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.conversation.id)
        self.assertEqual(response.data['subject'], self.conversation.subject)
        
    def test_create_conversation(self):
        """Test creating a conversation."""
        url = reverse('api:conversation-list')
        data = {
            'participants': [self.user2.id],
            'subject': 'Test Conversation'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['subject'], 'Test Conversation')
        self.assertEqual(len(response.data['participants']), 2)
        
    def test_get_messages_list(self):
        """Test getting messages list."""
        url = reverse('api:message-list', kwargs={'conversation_pk': self.conversation.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.message.id)
        
    def test_send_message(self):
        """Test sending a message."""
        url = reverse('api:message-list', kwargs={'conversation_pk': self.conversation.pk})
        data = {
            'content': 'Hello, this is a test message'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Hello, this is a test message')
        self.assertEqual(response.data['sender']['id'], self.user1.id)
        
    def test_mark_message_as_read(self):
        """Test marking a message as read."""
        # Login as user2
        user2_token = Token.objects.get_or_create(user=self.user2)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {user2_token.key}')
        
        url = reverse('api:message-read', kwargs={'pk': self.message.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check message was marked as read
        self.message.refresh_from_db()
        self.assertTrue(self.message.is_read)


class NotificationAPITest(TestCase, APITestMixin):
    """API tests for notification endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = APIClient()
        self.user = UserFactory.create()
        
        # Create notification
        from notifications.models import Notification  # Import here to avoid circular imports
        self.notification = NotificationFactory.create(
            recipient=self.user,
            title='Test Notification',
            message='This is a test notification'
        )
        
        self.token = Token.objects.get_or_create(user=self.user)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
    def test_get_notifications_list(self):
        """Test getting notifications list."""
        url = reverse('api:notification-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.notification.id)
        
    def test_get_notification_detail(self):
        """Test getting notification detail."""
        url = reverse('api:notification-detail', kwargs={'pk': self.notification.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.notification.id)
        self.assertEqual(response.data['title'], 'Test Notification')
        
    def test_mark_notification_as_read(self):
        """Test marking a notification as read."""
        url = reverse('api:notification-read', kwargs={'pk': self.notification.pk})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check notification was marked as read
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        
    def test_mark_all_notifications_as_read(self):
        """Test marking all notifications as read."""
        # Create more notifications
        from notifications.models import Notification  # Import here to avoid circular imports
        NotificationFactory.create_batch(3, recipient=self.user)
        
        url = reverse('api:notification-read-all')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check all notifications were marked as read
        unread_count = Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).count()
        self.assertEqual(unread_count, 0)
        
    def test_get_unread_count(self):
        """Test getting unread notifications count."""
        url = reverse('api:notification-unread-count')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 1)


class SearchAPITest(TestCase, APITestMixin):
    """API tests for search endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = APIClient()
        self.category = CategoryFactory.create()
        self.subject = SubjectFactory.create(category=self.category)
        
        # Create requirements
        self.python_req = RequirementFactory.create(
            title='Python Programming Tutor',
            subject=self.subject
        )
        self.math_req = RequirementFactory.create(
            title='Mathematics Tutor',
            subject=self.subject
        )
        
    def test_search_requirements(self):
        """Test searching requirements."""
        url = reverse('api:search')
        response = self.client.get(url, {'q': 'Python'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.python_req.id)
        
    def test_search_tutors(self):
        """Test searching tutors."""
        # Create tutors
        python_tutor = UserFactory.create(user_type='TUTOR')
        python_profile = TutorProfileFactory.create(
            user=python_tutor,
            subjects='Python'
        )
        
        math_tutor = UserFactory.create(user_type='TUTOR')
        math_profile = TutorProfileFactory.create(
            user=math_tutor,
            subjects='Mathematics'
        )
        
        url = reverse('api:search-tutors')
        response = self.client.get(url, {'q': 'Python'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], python_tutor.id)
        
    def test_get_search_suggestions(self):
        """Test getting search suggestions."""
        url = reverse('api:search-suggestions')
        response = self.client.get(url, {'q': 'Pyt'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Python Programming Tutor', response.data['suggestions'])
        
    def test_get_popular_searches(self):
        """Test getting popular searches."""
        url = reverse('api:search-popular')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data['popular_searches'], list)


class PaginationAPITest(TestCase, APITestMixin):
    """API tests for pagination."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = APIClient()
        self.user = UserFactory.create()
        self.token = Token.objects.get_or_create(user=self.user)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Create many requirements
        RequirementFactory.create_batch(25)
        
    def test_pagination_first_page(self):
        """Test pagination first page."""
        url = reverse('api:requirement-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 20)  # Default page size
        self.assertEqual(response.data['count'], 25)
        self.assertIsNone(response.data['previous'])
        self.assertIsNotNone(response.data['next'])
        
    def test_pagination_second_page(self):
        """Test pagination second page."""
        url = reverse('api:requirement-list')
        response = self.client.get(url, {'page': 2})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)
        self.assertEqual(response.data['count'], 25)
        self.assertIsNotNone(response.data['previous'])
        self.assertIsNone(response.data['next'])
        
    def test_pagination_page_size(self):
        """Test pagination with custom page size."""
        url = reverse('api:requirement-list')
        response = self.client.get(url, {'page_size': 10})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
        self.assertEqual(response.data['count'], 25)
        self.assertIsNone(response.data['previous'])
        self.assertIsNotNone(response.data['next'])


class ErrorHandlingAPITest(TestCase, APITestMixin):
    """API tests for error handling."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = APIClient()
        self.user = UserFactory.create()
        self.token = Token.objects.get_or_create(user=self.user)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
    def test_not_found_error(self):
        """Test 404 Not Found error."""
        url = reverse('api:requirement-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_permission_denied_error(self):
        """Test 403 Permission Denied error."""
        # Create requirement by another user
        other_user = UserFactory.create()
        requirement = RequirementFactory.create(created_by=other_user)
        
        url = reverse('api:requirement-detail', kwargs={'pk': requirement.pk})
        data = {'title': 'Updated Title'}
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
    def test_validation_error(self):
        """Test validation error."""
        url = reverse('api:requirement-list')
        data = {
            'title': '',  # Empty title should cause validation error
            'description': 'Test description',
            'budget': 50.00
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)
        
    def test_authentication_required_error(self):
        """Test authentication required error."""
        self.client.credentials()  # Remove authentication
        
        url = reverse('api:requirement-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_rate_limiting_error(self):
        """Test rate limiting error."""
        # This would depend on the actual rate limiting implementation
        # For testing, we'll simulate multiple rapid requests
        url = reverse('api:requirement-list')
        
        # Make many requests
        for _ in range(100):
            response = self.client.get(url)
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break
                
        # Check if rate limiting was triggered
        # This would depend on the actual rate limiting implementation
        pass


class APIResponseFormatTest(TestCase, APITestMixin):
    """API tests for response format."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = APIClient()
        self.user = UserFactory.create()
        self.token = Token.objects.get_or_create(user=self.user)[0]
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # Create requirement
        self.requirement = RequirementFactory.create(created_by=self.user)
        
    def test_list_response_format(self):
        """Test list response format."""
        url = reverse('api:requirement-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check response structure
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
        
    def test_detail_response_format(self):
        """Test detail response format."""
        url = reverse('api:requirement-detail', kwargs={'pk': self.requirement.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check response structure
        self.assertIn('id', response.data)
        self.assertIn('title', response.data)
        self.assertIn('description', response.data)
        self.assertIn('created_at', response.data)
        self.assertIn('updated_at', response.data)
        
    def test_error_response_format(self):
        """Test error response format."""
        url = reverse('api:requirement-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Check error response structure
        self.assertIn('detail', response.data)
        
    def test_validation_error_response_format(self):
        """Test validation error response format."""
        url = reverse('api:requirement-list')
        data = {
            'title': '',  # Empty title should cause validation error
            'description': 'Test description',
            'budget': 50.00
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Check validation error response structure
        self.assertIsInstance(response.data, dict)