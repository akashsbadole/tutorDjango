"""
Unit tests for accounts app views and business logic.
"""
import pytest
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from unittest.mock import patch, MagicMock

from accounts.views import (
    RegisterView, LoginView, LogoutView, ProfileView, ProfileUpdateView,
    TutorProfileView, TutorProfileUpdateView, StudentProfileView, StudentProfileUpdateView
)
from tests.factories import UserFactory, TutorProfileFactory, StudentProfileFactory
from tests.utils.helpers import TestMixin, ViewTestMixin

User = get_user_model()


class RegisterViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for RegisterView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.view = RegisterView()
        
    def test_register_view_get(self):
        """Test RegisterView GET request."""
        request = self.factory.get(reverse('accounts:register'))
        response = RegisterView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')
        
    def test_register_view_post_valid_data(self):
        """Test RegisterView POST request with valid data."""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'STUDENT'
        }
        
        request = self.factory.post(reverse('accounts:register'), data=data)
        
        with patch('accounts.views.messages.success') as mock_success:
            response = RegisterView.as_view()(request)
            
            # Check that user was created
            self.assertTrue(User.objects.filter(username='testuser').exists())
            
            # Check that success message was called
            mock_success.assert_called_once()
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            
    def test_register_view_post_invalid_data(self):
        """Test RegisterView POST request with invalid data."""
        data = {
            'username': 'testuser',
            'email': 'invalid-email',  # Invalid email
            'password1': 'testpass123',
            'password2': 'differentpass',  # Passwords don't match
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'STUDENT'
        }
        
        request = self.factory.post(reverse('accounts:register'), data=data)
        response = RegisterView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'email', 'Enter a valid email address.')
        self.assertFormError(response, 'form', 'password2', 'The two password fields didn\'t match.')
        
    def test_register_view_creates_student_profile(self):
        """Test RegisterView creates StudentProfile for student user."""
        data = {
            'username': 'teststudent',
            'email': 'student@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Student',
            'user_type': 'STUDENT'
        }
        
        request = self.factory.post(reverse('accounts:register'), data=data)
        RegisterView.as_view()(request)
        
        user = User.objects.get(username='teststudent')
        self.assertTrue(hasattr(user, 'student_profile'))
        
    def test_register_view_creates_tutor_profile(self):
        """Test RegisterView creates TutorProfile for tutor user."""
        data = {
            'username': 'testtutor',
            'email': 'tutor@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Tutor',
            'user_type': 'TUTOR'
        }
        
        request = self.factory.post(reverse('accounts:register'), data=data)
        RegisterView.as_view()(request)
        
        user = User.objects.get(username='testtutor')
        self.assertTrue(hasattr(user, 'tutor_profile'))


class LoginViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for LoginView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.user = UserFactory.create()
        self.user.set_password('testpass123')
        self.user.save()
        
    def test_login_view_get(self):
        """Test LoginView GET request."""
        request = self.factory.get(reverse('accounts:login'))
        response = LoginView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        
    def test_login_view_post_valid_credentials(self):
        """Test LoginView POST request with valid credentials."""
        data = {
            'username': self.user.username,
            'password': 'testpass123'
        }
        
        request = self.factory.post(reverse('accounts:login'), data=data)
        
        with patch('accounts.views.login') as mock_login:
            with patch('accounts.views.messages.success') as mock_success:
                response = LoginView.as_view()(request)
                
                # Check that login was called
                mock_login.assert_called_once()
                
                # Check that success message was called
                mock_success.assert_called_once()
                
                # Check redirect
                self.assertEqual(response.status_code, 302)
                
    def test_login_view_post_invalid_credentials(self):
        """Test LoginView POST request with invalid credentials."""
        data = {
            'username': self.user.username,
            'password': 'wrongpassword'
        }
        
        request = self.factory.post(reverse('accounts:login'), data=data)
        
        with patch('accounts.views.messages.error') as mock_error:
            response = LoginView.as_view()(request)
            
            # Check that error message was called
            mock_error.assert_called_once()
            
            # Check that form has error
            self.assertFormError(response, 'form', None, 'Invalid username or password.')
            
    def test_login_view_redirects_authenticated_user(self):
        """Test LoginView redirects authenticated user."""
        # Create authenticated request
        request = self.factory.get(reverse('accounts:login'))
        request.user = self.user
        
        response = LoginView.as_view()(request)
        
        # Check redirect to profile
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:profile'), response.url)


class LogoutViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for LogoutView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.user = UserFactory.create()
        
    def test_logout_view(self):
        """Test LogoutView."""
        # Create authenticated request
        request = self.factory.post(reverse('accounts:logout'))
        request.user = self.user
        
        with patch('accounts.views.logout') as mock_logout:
            with patch('accounts.views.messages.success') as mock_success:
                response = LogoutView.as_view()(request)
                
                # Check that logout was called
                mock_logout.assert_called_once()
                
                # Check that success message was called
                mock_success.assert_called_once()
                
                # Check redirect
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse('accounts:login'), response.url)


class ProfileViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for ProfileView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.user = UserFactory.create()
        
    def test_profile_view_authenticated(self):
        """Test ProfileView with authenticated user."""
        # Create authenticated request
        request = self.factory.get(reverse('accounts:profile'))
        request.user = self.user
        
        response = ProfileView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')
        self.assertEqual(response.context['user'], self.user)
        
    def test_profile_view_unauthenticated(self):
        """Test ProfileView with unauthenticated user."""
        # Create unauthenticated request
        request = self.factory.get(reverse('accounts:profile'))
        request.user = self.anonymous_user
        
        response = ProfileView.as_view()(request)
        
        # Check redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)


class ProfileUpdateViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for ProfileUpdateView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.user = UserFactory.create()
        
    def test_profile_update_view_get(self):
        """Test ProfileUpdateView GET request."""
        # Create authenticated request
        request = self.factory.get(reverse('accounts:profile_update'))
        request.user = self.user
        
        response = ProfileUpdateView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile_update.html')
        self.assertEqual(response.context['form'].instance, self.user)
        
    def test_profile_update_view_post_valid_data(self):
        """Test ProfileUpdateView POST request with valid data."""
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@example.com',
            'bio': 'Updated bio'
        }
        
        # Create authenticated request
        request = self.factory.post(reverse('accounts:profile_update'), data=data)
        request.user = self.user
        
        with patch('accounts.views.messages.success') as mock_success:
            response = ProfileUpdateView.as_view()(request)
            
            # Check that user was updated
            self.user.refresh_from_db()
            self.assertEqual(self.user.first_name, 'Updated')
            self.assertEqual(self.user.last_name, 'Name')
            self.assertEqual(self.user.email, 'updated@example.com')
            self.assertEqual(self.user.bio, 'Updated bio')
            
            # Check that success message was called
            mock_success.assert_called_once()
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('accounts:profile'), response.url)
            
    def test_profile_update_view_post_invalid_data(self):
        """Test ProfileUpdateView POST request with invalid data."""
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'invalid-email',  # Invalid email
            'bio': 'Updated bio'
        }
        
        # Create authenticated request
        request = self.factory.post(reverse('accounts:profile_update'), data=data)
        request.user = self.user
        
        response = ProfileUpdateView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'email', 'Enter a valid email address.')


class TutorProfileViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for TutorProfileView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.user = UserFactory.create(user_type='TUTOR')
        self.tutor_profile = TutorProfileFactory.create(user=self.user)
        
    def test_tutor_profile_view_authenticated(self):
        """Test TutorProfileView with authenticated user."""
        # Create authenticated request
        request = self.factory.get(reverse('accounts:tutor_profile'))
        request.user = self.user
        
        response = TutorProfileView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/tutor_profile.html')
        self.assertEqual(response.context['tutor_profile'], self.tutor_profile)
        
    def test_tutor_profile_view_unauthenticated(self):
        """Test TutorProfileView with unauthenticated user."""
        # Create unauthenticated request
        request = self.factory.get(reverse('accounts:tutor_profile'))
        request.user = self.anonymous_user
        
        response = TutorProfileView.as_view()(request)
        
        # Check redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)
        
    def test_tutor_profile_view_non_tutor(self):
        """Test TutorProfileView with non-tutor user."""
        # Create student user
        student_user = UserFactory.create(user_type='STUDENT')
        
        # Create authenticated request
        request = self.factory.get(reverse('accounts:tutor_profile'))
        request.user = student_user
        
        response = TutorProfileView.as_view()(request)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)


class TutorProfileUpdateViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for TutorProfileUpdateView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.user = UserFactory.create(user_type='TUTOR')
        self.tutor_profile = TutorProfileFactory.create(user=self.user)
        
    def test_tutor_profile_update_view_get(self):
        """Test TutorProfileUpdateView GET request."""
        # Create authenticated request
        request = self.factory.get(reverse('accounts:tutor_profile_update'))
        request.user = self.user
        
        response = TutorProfileUpdateView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/tutor_profile_update.html')
        self.assertEqual(response.context['form'].instance, self.tutor_profile)
        
    def test_tutor_profile_update_view_post_valid_data(self):
        """Test TutorProfileUpdateView POST request with valid data."""
        data = {
            'hourly_rate': 50.00,
            'experience_years': 5,
            'education': 'Updated education',
            'subjects': 'Updated subjects',
            'availability': 'Updated availability',
            'bio': 'Updated bio'
        }
        
        # Create authenticated request
        request = self.factory.post(reverse('accounts:tutor_profile_update'), data=data)
        request.user = self.user
        
        with patch('accounts.views.messages.success') as mock_success:
            response = TutorProfileUpdateView.as_view()(request)
            
            # Check that tutor profile was updated
            self.tutor_profile.refresh_from_db()
            self.assertEqual(self.tutor_profile.hourly_rate, 50.00)
            self.assertEqual(self.tutor_profile.experience_years, 5)
            self.assertEqual(self.tutor_profile.education, 'Updated education')
            self.assertEqual(self.tutor_profile.subjects, 'Updated subjects')
            self.assertEqual(self.tutor_profile.availability, 'Updated availability')
            self.assertEqual(self.tutor_profile.bio, 'Updated bio')
            
            # Check that success message was called
            mock_success.assert_called_once()
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('accounts:tutor_profile'), response.url)


class StudentProfileViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for StudentProfileView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.user = UserFactory.create(user_type='STUDENT')
        self.student_profile = StudentProfileFactory.create(user=self.user)
        
    def test_student_profile_view_authenticated(self):
        """Test StudentProfileView with authenticated user."""
        # Create authenticated request
        request = self.factory.get(reverse('accounts:student_profile'))
        request.user = self.user
        
        response = StudentProfileView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/student_profile.html')
        self.assertEqual(response.context['student_profile'], self.student_profile)
        
    def test_student_profile_view_unauthenticated(self):
        """Test StudentProfileView with unauthenticated user."""
        # Create unauthenticated request
        request = self.factory.get(reverse('accounts:student_profile'))
        request.user = self.anonymous_user
        
        response = StudentProfileView.as_view()(request)
        
        # Check redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)
        
    def test_student_profile_view_non_student(self):
        """Test StudentProfileView with non-student user."""
        # Create tutor user
        tutor_user = UserFactory.create(user_type='TUTOR')
        
        # Create authenticated request
        request = self.factory.get(reverse('accounts:student_profile'))
        request.user = tutor_user
        
        response = StudentProfileView.as_view()(request)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)


class StudentProfileUpdateViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for StudentProfileUpdateView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.user = UserFactory.create(user_type='STUDENT')
        self.student_profile = StudentProfileFactory.create(user=self.user)
        
    def test_student_profile_update_view_get(self):
        """Test StudentProfileUpdateView GET request."""
        # Create authenticated request
        request = self.factory.get(reverse('accounts:student_profile_update'))
        request.user = self.user
        
        response = StudentProfileUpdateView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/student_profile_update.html')
        self.assertEqual(response.context['form'].instance, self.student_profile)
        
    def test_student_profile_update_view_post_valid_data(self):
        """Test StudentProfileUpdateView POST request with valid data."""
        data = {
            'education_level': 'GRADUATE',
            'subjects_of_interest': 'Updated subjects',
            'learning_goals': 'Updated learning goals',
            'bio': 'Updated bio'
        }
        
        # Create authenticated request
        request = self.factory.post(reverse('accounts:student_profile_update'), data=data)
        request.user = self.user
        
        with patch('accounts.views.messages.success') as mock_success:
            response = StudentProfileUpdateView.as_view()(request)
            
            # Check that student profile was updated
            self.student_profile.refresh_from_db()
            self.assertEqual(self.student_profile.education_level, 'GRADUATE')
            self.assertEqual(self.student_profile.subjects_of_interest, 'Updated subjects')
            self.assertEqual(self.student_profile.learning_goals, 'Updated learning goals')
            self.assertEqual(self.student_profile.bio, 'Updated bio')
            
            # Check that success message was called
            mock_success.assert_called_once()
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('accounts:student_profile'), response.url)


class AccountsBusinessLogicTest(TestCase, TestMixin):
    """Test cases for accounts app business logic."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_user_type_property(self):
        """Test user_type property."""
        # Test student user
        student = UserFactory.create(user_type='STUDENT')
        self.assertEqual(student.user_type, 'STUDENT')
        self.assertTrue(student.is_student)
        self.assertFalse(student.is_tutor)
        
        # Test tutor user
        tutor = UserFactory.create(user_type='TUTOR')
        self.assertEqual(tutor.user_type, 'TUTOR')
        self.assertTrue(tutor.is_tutor)
        self.assertFalse(tutor.is_student)
        
    def test_user_profile_property(self):
        """Test profile property."""
        # Test student user
        student = UserFactory.create(user_type='STUDENT')
        student_profile = StudentProfileFactory.create(user=student)
        self.assertEqual(student.profile, student_profile)
        
        # Test tutor user
        tutor = UserFactory.create(user_type='TUTOR')
        tutor_profile = TutorProfileFactory.create(user=tutor)
        self.assertEqual(tutor.profile, tutor_profile)
        
    def test_user_full_name_property(self):
        """Test full_name property."""
        user = UserFactory.create(first_name='John', last_name='Doe')
        self.assertEqual(user.full_name, 'John Doe')
        
        # Test with only first name
        user_first_only = UserFactory.create(first_name='John', last_name='')
        self.assertEqual(user_first_only.full_name, 'John')
        
        # Test with only last name
        user_last_only = UserFactory.create(first_name='', last_name='Doe')
        self.assertEqual(user_last_only.full_name, 'Doe')
        
        # Test with no names
        user_no_names = UserFactory.create(first_name='', last_name='')
        self.assertEqual(user_no_names.full_name, user_no_names.username)
        
    def test_user_avatar_url_property(self):
        """Test avatar_url property."""
        # Test with avatar
        user_with_avatar = UserFactory.create(avatar='avatars/test.jpg')
        self.assertIn('avatars/test.jpg', user_with_avatar.avatar_url)
        
        # Test without avatar
        user_without_avatar = UserFactory.create(avatar='')
        self.assertIn('default-avatar', user_without_avatar.avatar_url)
        
    def test_tutor_profile_rating_property(self):
        """Test TutorProfile rating property."""
        tutor_profile = TutorProfileFactory.create()
        
        # Test with no ratings
        self.assertEqual(tutor_profile.rating, 0)
        
        # Test with ratings (implementation depends on actual rating calculation)
        # This would require creating rating objects
        pass
        
    def test_tutor_profile_is_available_property(self):
        """Test TutorProfile is_available property."""
        tutor_profile = TutorProfileFactory.create()
        
        # Test with availability
        tutor_profile.availability = "Monday, Wednesday, Friday"
        self.assertTrue(tutor_profile.is_available)
        
        # Test without availability
        tutor_profile.availability = ""
        self.assertFalse(tutor_profile.is_available)
        
    def test_student_profile_level_property(self):
        """Test StudentProfile level property."""
        student_profile = StudentProfileFactory.create()
        
        # Test with education level
        student_profile.education_level = 'UNDERGRADUATE'
        self.assertEqual(student_profile.level, 'Undergraduate')
        
        # Test without education level
        student_profile.education_level = ''
        self.assertEqual(student_profile.level, 'Not specified')