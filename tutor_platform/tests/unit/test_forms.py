"""
Unit tests for forms across all apps.
"""
import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from accounts.forms import (
    UserRegistrationForm, UserLoginForm, UserProfileForm, TutorProfileForm, StudentProfileForm
)
from requirements.forms import (
    RequirementForm, ProposalForm, AwardForm, SessionForm
)
from messaging.forms import (
    ConversationForm, MessageForm, OnlineClassForm
)
from paymentsdetails.forms import (
    PaymentMethodForm, PayoutRequestForm
)
from search.forms import SearchForm

from tests.factories import (
    UserFactory, TutorProfileFactory, StudentProfileFactory, CategoryFactory,
    SubjectFactory, RequirementFactory, ProposalFactory
)
from tests.utils.helpers import TestMixin

User = get_user_model()


class UserRegistrationFormTest(TestCase, TestMixin):
    """Test cases for UserRegistrationForm."""
    
    def test_valid_registration_data(self):
        """Test form with valid data."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'STUDENT'
        }
        
        form = UserRegistrationForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_password_mismatch(self):
        """Test form with mismatched passwords."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'differentpass',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'STUDENT'
        }
        
        form = UserRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
        
    def test_invalid_email(self):
        """Test form with invalid email."""
        data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'STUDENT'
        }
        
        form = UserRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        
    def test_duplicate_username(self):
        """Test form with duplicate username."""
        # Create user with same username
        UserFactory.create(username='testuser')
        
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'STUDENT'
        }
        
        form = UserRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        
    def test_missing_required_fields(self):
        """Test form with missing required fields."""
        data = {
            'username': '',
            'email': '',
            'password1': '',
            'password2': '',
            'first_name': '',
            'last_name': '',
            'user_type': ''
        }
        
        form = UserRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        
        # Check that all required fields have errors
        self.assertIn('username', form.errors)
        self.assertIn('email', form.errors)
        self.assertIn('password1', form.errors)
        self.assertIn('password2', form.errors)
        self.assertIn('first_name', form.errors)
        self.assertIn('last_name', form.errors)
        self.assertIn('user_type', form.errors)
        
    def test_weak_password(self):
        """Test form with weak password."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': '123',  # Too short
            'password2': '123',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'STUDENT'
        }
        
        form = UserRegistrationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)


class UserLoginFormTest(TestCase, TestMixin):
    """Test cases for UserLoginForm."""
    
    def test_valid_login_data(self):
        """Test form with valid data."""
        # Create user
        user = UserFactory.create()
        user.set_password('testpass123')
        user.save()
        
        data = {
            'username': user.username,
            'password': 'testpass123'
        }
        
        form = UserLoginForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_invalid_credentials(self):
        """Test form with invalid credentials."""
        data = {
            'username': 'nonexistentuser',
            'password': 'wrongpassword'
        }
        
        form = UserLoginForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)  # Non-field error
        
    def test_missing_fields(self):
        """Test form with missing fields."""
        data = {
            'username': '',
            'password': ''
        }
        
        form = UserLoginForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('password', form.errors)


class UserProfileFormTest(TestCase, TestMixin):
    """Test cases for UserProfileForm."""
    
    def test_valid_profile_data(self):
        """Test form with valid data."""
        user = UserFactory.create()
        
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'bio': 'Updated bio'
        }
        
        form = UserProfileForm(data=data, instance=user)
        self.assertTrue(form.is_valid())
        
    def test_invalid_email(self):
        """Test form with invalid email."""
        user = UserFactory.create()
        
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'invalid-email',
            'bio': 'Updated bio'
        }
        
        form = UserProfileForm(data=data, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        
    def test_duplicate_email(self):
        """Test form with duplicate email."""
        # Create users
        user1 = UserFactory.create(email='user1@example.com')
        user2 = UserFactory.create(email='user2@example.com')
        
        # Try to update user2 with user1's email
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'user1@example.com',
            'bio': 'Updated bio'
        }
        
        form = UserProfileForm(data=data, instance=user2)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)


class TutorProfileFormTest(TestCase, TestMixin):
    """Test cases for TutorProfileForm."""
    
    def test_valid_tutor_profile_data(self):
        """Test form with valid data."""
        user = UserFactory.create()
        
        data = {
            'hourly_rate': 50.00,
            'experience_years': 5,
            'education': 'Bachelor\'s in Computer Science',
            'subjects': 'Python, Django, JavaScript',
            'availability': 'Monday, Wednesday, Friday',
            'bio': 'Experienced tutor'
        }
        
        form = TutorProfileForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_negative_hourly_rate(self):
        """Test form with negative hourly rate."""
        data = {
            'hourly_rate': -10.00,
            'experience_years': 5,
            'education': 'Bachelor\'s in Computer Science',
            'subjects': 'Python, Django, JavaScript',
            'availability': 'Monday, Wednesday, Friday',
            'bio': 'Experienced tutor'
        }
        
        form = TutorProfileForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('hourly_rate', form.errors)
        
    def test_negative_experience_years(self):
        """Test form with negative experience years."""
        data = {
            'hourly_rate': 50.00,
            'experience_years': -1,
            'education': 'Bachelor\'s in Computer Science',
            'subjects': 'Python, Django, JavaScript',
            'availability': 'Monday, Wednesday, Friday',
            'bio': 'Experienced tutor'
        }
        
        form = TutorProfileForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('experience_years', form.errors)


class StudentProfileFormTest(TestCase, TestMixin):
    """Test cases for StudentProfileForm."""
    
    def test_valid_student_profile_data(self):
        """Test form with valid data."""
        data = {
            'education_level': 'UNDERGRADUATE',
            'subjects_of_interest': 'Python, Mathematics, Physics',
            'learning_goals': 'Learn Python programming',
            'bio': 'Motivated student'
        }
        
        form = StudentProfileForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_invalid_education_level(self):
        """Test form with invalid education level."""
        data = {
            'education_level': 'INVALID',
            'subjects_of_interest': 'Python, Mathematics, Physics',
            'learning_goals': 'Learn Python programming',
            'bio': 'Motivated student'
        }
        
        form = StudentProfileForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('education_level', form.errors)


class RequirementFormTest(TestCase, TestMixin):
    """Test cases for RequirementForm."""
    
    def test_valid_requirement_data(self):
        """Test form with valid data."""
        category = CategoryFactory.create()
        subject = SubjectFactory.create(category=category)
        
        data = {
            'title': 'Python Programming Tutor',
            'description': 'Need help with Python programming',
            'category': category.id,
            'subject': subject.id,
            'budget': 50.00,
            'duration_weeks': 4,
            'hours_per_week': 2,
            'location': 'Online',
            'requirements': 'Basic Python knowledge'
        }
        
        form = RequirementForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_missing_required_fields(self):
        """Test form with missing required fields."""
        data = {
            'title': '',
            'description': '',
            'category': '',
            'subject': '',
            'budget': '',
            'duration_weeks': '',
            'hours_per_week': '',
            'location': '',
            'requirements': ''
        }
        
        form = RequirementForm(data=data)
        self.assertFalse(form.is_valid())
        
        # Check that all required fields have errors
        self.assertIn('title', form.errors)
        self.assertIn('description', form.errors)
        self.assertIn('category', form.errors)
        self.assertIn('subject', form.errors)
        self.assertIn('budget', form.errors)
        self.assertIn('duration_weeks', form.errors)
        self.assertIn('hours_per_week', form.errors)
        self.assertIn('location', form.errors)
        
    def test_negative_budget(self):
        """Test form with negative budget."""
        category = CategoryFactory.create()
        subject = SubjectFactory.create(category=category)
        
        data = {
            'title': 'Python Programming Tutor',
            'description': 'Need help with Python programming',
            'category': category.id,
            'subject': subject.id,
            'budget': -50.00,
            'duration_weeks': 4,
            'hours_per_week': 2,
            'location': 'Online',
            'requirements': 'Basic Python knowledge'
        }
        
        form = RequirementForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('budget', form.errors)
        
    def test_negative_duration(self):
        """Test form with negative duration."""
        category = CategoryFactory.create()
        subject = SubjectFactory.create(category=category)
        
        data = {
            'title': 'Python Programming Tutor',
            'description': 'Need help with Python programming',
            'category': category.id,
            'subject': subject.id,
            'budget': 50.00,
            'duration_weeks': -4,
            'hours_per_week': 2,
            'location': 'Online',
            'requirements': 'Basic Python knowledge'
        }
        
        form = RequirementForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('duration_weeks', form.errors)


class ProposalFormTest(TestCase, TestMixin):
    """Test cases for ProposalForm."""
    
    def test_valid_proposal_data(self):
        """Test form with valid data."""
        data = {
            'title': 'Python Programming Proposal',
            'description': 'I can help you with Python programming',
            'hourly_rate': 25.00,
            'total_hours': 8,
            'timeline': '2 weeks',
            'approach': 'Hands-on coding exercises',
            'qualifications': '5 years Python experience'
        }
        
        form = ProposalForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_missing_required_fields(self):
        """Test form with missing required fields."""
        data = {
            'title': '',
            'description': '',
            'hourly_rate': '',
            'total_hours': '',
            'timeline': '',
            'approach': '',
            'qualifications': ''
        }
        
        form = ProposalForm(data=data)
        self.assertFalse(form.is_valid())
        
        # Check that all required fields have errors
        self.assertIn('title', form.errors)
        self.assertIn('description', form.errors)
        self.assertIn('hourly_rate', form.errors)
        self.assertIn('total_hours', form.errors)
        self.assertIn('timeline', form.errors)
        self.assertIn('approach', form.errors)
        self.assertIn('qualifications', form.errors)
        
    def test_negative_hourly_rate(self):
        """Test form with negative hourly rate."""
        data = {
            'title': 'Python Programming Proposal',
            'description': 'I can help you with Python programming',
            'hourly_rate': -25.00,
            'total_hours': 8,
            'timeline': '2 weeks',
            'approach': 'Hands-on coding exercises',
            'qualifications': '5 years Python experience'
        }
        
        form = ProposalForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('hourly_rate', form.errors)
        
    def test_negative_total_hours(self):
        """Test form with negative total hours."""
        data = {
            'title': 'Python Programming Proposal',
            'description': 'I can help you with Python programming',
            'hourly_rate': 25.00,
            'total_hours': -8,
            'timeline': '2 weeks',
            'approach': 'Hands-on coding exercises',
            'qualifications': '5 years Python experience'
        }
        
        form = ProposalForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('total_hours', form.errors)


class AwardFormTest(TestCase, TestMixin):
    """Test cases for AwardForm."""
    
    def test_valid_award_data(self):
        """Test form with valid data."""
        data = {
            'price': 200.00,
            'terms': 'Payment will be made upon completion'
        }
        
        form = AwardForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_missing_required_fields(self):
        """Test form with missing required fields."""
        data = {
            'price': '',
            'terms': ''
        }
        
        form = AwardForm(data=data)
        self.assertFalse(form.is_valid())
        
        # Check that all required fields have errors
        self.assertIn('price', form.errors)
        self.assertIn('terms', form.errors)
        
    def test_negative_price(self):
        """Test form with negative price."""
        data = {
            'price': -200.00,
            'terms': 'Payment will be made upon completion'
        }
        
        form = AwardForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)


class SessionFormTest(TestCase, TestMixin):
    """Test cases for SessionForm."""
    
    def test_valid_session_data(self):
        """Test form with valid data."""
        data = {
            'title': 'Python Programming Session 1',
            'description': 'Introduction to Python basics',
            'scheduled_at': '2023-12-01T10:00:00Z',
            'duration_minutes': 60,
            'location': 'Online'
        }
        
        form = SessionForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_missing_required_fields(self):
        """Test form with missing required fields."""
        data = {
            'title': '',
            'description': '',
            'scheduled_at': '',
            'duration_minutes': '',
            'location': ''
        }
        
        form = SessionForm(data=data)
        self.assertFalse(form.is_valid())
        
        # Check that all required fields have errors
        self.assertIn('title', form.errors)
        self.assertIn('description', form.errors)
        self.assertIn('scheduled_at', form.errors)
        self.assertIn('duration_minutes', form.errors)
        self.assertIn('location', form.errors)
        
    def test_negative_duration(self):
        """Test form with negative duration."""
        data = {
            'title': 'Python Programming Session 1',
            'description': 'Introduction to Python basics',
            'scheduled_at': '2023-12-01T10:00:00Z',
            'duration_minutes': -60,
            'location': 'Online'
        }
        
        form = SessionForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('duration_minutes', form.errors)


class ConversationFormTest(TestCase, TestMixin):
    """Test cases for ConversationForm."""
    
    def test_valid_conversation_data(self):
        """Test form with valid data."""
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        
        data = {
            'participants': [user2.id],
            'subject': 'Python Programming Discussion'
        }
        
        form = ConversationForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_missing_required_fields(self):
        """Test form with missing required fields."""
        data = {
            'participants': [],
            'subject': ''
        }
        
        form = ConversationForm(data=data)
        self.assertFalse(form.is_valid())
        
        # Check that all required fields have errors
        self.assertIn('participants', form.errors)
        self.assertIn('subject', form.errors)


class MessageFormTest(TestCase, TestMixin):
    """Test cases for MessageForm."""
    
    def test_valid_message_data(self):
        """Test form with valid data."""
        data = {
            'content': 'Hello, I need help with Python programming'
        }
        
        form = MessageForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_missing_content(self):
        """Test form with missing content."""
        data = {
            'content': ''
        }
        
        form = MessageForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)


class OnlineClassFormTest(TestCase, TestMixin):
    """Test cases for OnlineClassForm."""
    
    def test_valid_class_data(self):
        """Test form with valid data."""
        data = {
            'title': 'Python Programming Class',
            'description': 'Introduction to Python programming',
            'scheduled_at': '2023-12-01T10:00:00Z',
            'duration_minutes': 60,
            'platform': 'Zoom',
            'meeting_url': 'https://zoom.us/j/123456789',
            'max_participants': 10
        }
        
        form = OnlineClassForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_missing_required_fields(self):
        """Test form with missing required fields."""
        data = {
            'title': '',
            'description': '',
            'scheduled_at': '',
            'duration_minutes': '',
            'platform': '',
            'meeting_url': '',
            'max_participants': ''
        }
        
        form = OnlineClassForm(data=data)
        self.assertFalse(form.is_valid())
        
        # Check that all required fields have errors
        self.assertIn('title', form.errors)
        self.assertIn('description', form.errors)
        self.assertIn('scheduled_at', form.errors)
        self.assertIn('duration_minutes', form.errors)
        self.assertIn('platform', form.errors)
        self.assertIn('meeting_url', form.errors)
        self.assertIn('max_participants', form.errors)
        
    def test_invalid_meeting_url(self):
        """Test form with invalid meeting URL."""
        data = {
            'title': 'Python Programming Class',
            'description': 'Introduction to Python programming',
            'scheduled_at': '2023-12-01T10:00:00Z',
            'duration_minutes': 60,
            'platform': 'Zoom',
            'meeting_url': 'invalid-url',
            'max_participants': 10
        }
        
        form = OnlineClassForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('meeting_url', form.errors)
        
    def test_negative_max_participants(self):
        """Test form with negative max participants."""
        data = {
            'title': 'Python Programming Class',
            'description': 'Introduction to Python programming',
            'scheduled_at': '2023-12-01T10:00:00Z',
            'duration_minutes': 60,
            'platform': 'Zoom',
            'meeting_url': 'https://zoom.us/j/123456789',
            'max_participants': -10
        }
        
        form = OnlineClassForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('max_participants', form.errors)


class PaymentMethodFormTest(TestCase, TestMixin):
    """Test cases for PaymentMethodForm."""
    
    def test_valid_payment_method_data(self):
        """Test form with valid data."""
        data = {
            'method_type': 'PAYPAL',
            'paypal_email': 'user@example.com',
            'is_default': True
        }
        
        form = PaymentMethodForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_missing_required_fields(self):
        """Test form with missing required fields."""
        data = {
            'method_type': '',
            'paypal_email': '',
            'is_default': False
        }
        
        form = PaymentMethodForm(data=data)
        self.assertFalse(form.is_valid())
        
        # Check that all required fields have errors
        self.assertIn('method_type', form.errors)
        self.assertIn('paypal_email', form.errors)
        
    def test_invalid_email(self):
        """Test form with invalid email."""
        data = {
            'method_type': 'PAYPAL',
            'paypal_email': 'invalid-email',
            'is_default': True
        }
        
        form = PaymentMethodForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('paypal_email', form.errors)


class PayoutRequestFormTest(TestCase, TestMixin):
    """Test cases for PayoutRequestForm."""
    
    def test_valid_payout_data(self):
        """Test form with valid data."""
        data = {
            'amount': 100.00,
            'payment_method': 'PAYPAL',
            'notes': 'Monthly payout'
        }
        
        form = PayoutRequestForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_missing_required_fields(self):
        """Test form with missing required fields."""
        data = {
            'amount': '',
            'payment_method': '',
            'notes': ''
        }
        
        form = PayoutRequestForm(data=data)
        self.assertFalse(form.is_valid())
        
        # Check that all required fields have errors
        self.assertIn('amount', form.errors)
        self.assertIn('payment_method', form.errors)
        
    def test_negative_amount(self):
        """Test form with negative amount."""
        data = {
            'amount': -100.00,
            'payment_method': 'PAYPAL',
            'notes': 'Monthly payout'
        }
        
        form = PayoutRequestForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)


class SearchFormTest(TestCase, TestMixin):
    """Test cases for SearchForm."""
    
    def test_valid_search_data(self):
        """Test form with valid data."""
        data = {
            'q': 'Python programming',
            'category': '',
            'subject': '',
            'location': '',
            'min_budget': '',
            'max_budget': ''
        }
        
        form = SearchForm(data=data)
        self.assertTrue(form.is_valid())
        
    def test_empty_search(self):
        """Test form with empty search query."""
        data = {
            'q': '',
            'category': '',
            'subject': '',
            'location': '',
            'min_budget': '',
            'max_budget': ''
        }
        
        form = SearchForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('q', form.errors)
        
    def test_negative_budgets(self):
        """Test form with negative budgets."""
        data = {
            'q': 'Python programming',
            'category': '',
            'subject': '',
            'location': '',
            'min_budget': -50.00,
            'max_budget': -100.00
        }
        
        form = SearchForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('min_budget', form.errors)
        self.assertIn('max_budget', form.errors)
        
    def test_min_greater_than_max_budget(self):
        """Test form with min budget greater than max budget."""
        data = {
            'q': 'Python programming',
            'category': '',
            'subject': '',
            'location': '',
            'min_budget': 100.00,
            'max_budget': 50.00
        }
        
        form = SearchForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)  # Non-field error