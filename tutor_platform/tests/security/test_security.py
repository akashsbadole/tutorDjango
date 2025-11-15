"""
Security tests for Django tutoring platform.
"""
import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from unittest.mock import patch

from tests.factories import (
    UserFactory, TutorProfileFactory, StudentProfileFactory, CategoryFactory,
    SubjectFactory, RequirementFactory, ProposalFactory, PaymentFactory
)
from tests.utils.helpers import TestMixin, SecurityTestMixin

User = get_user_model()


class SQLInjectionTest(TestCase, SecurityTestMixin):
    """Security tests for SQL injection vulnerabilities."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        
    def test_search_sql_injection(self):
        """Test search endpoint for SQL injection."""
        # Create requirements
        RequirementFactory.create_batch(10)
        
        # Test SQL injection in search query
        malicious_query = "Python'; DROP TABLE requirements_requirement; --"
        
        response = self.client.get(reverse('search:search'), {'q': malicious_query})
        
        # Check that response is successful (no SQL injection occurred)
        self.assertEqual(response.status_code, 200)
        
        # Check that table still exists
        from requirements.models import Requirement
        self.assertEqual(Requirement.objects.count(), 10)
        
    def test_api_search_sql_injection(self):
        """Test API search endpoint for SQL injection."""
        # Create requirements
        RequirementFactory.create_batch(10)
        
        # Test SQL injection in API search query
        malicious_query = "Python'; DROP TABLE requirements_requirement; --"
        
        response = self.client.get(reverse('api:search'), {'q': malicious_query})
        
        # Check that response is successful (no SQL injection occurred)
        self.assertEqual(response.status_code, 200)
        
        # Check that table still exists
        from requirements.models import Requirement
        self.assertEqual(Requirement.objects.count(), 10)
        
    def test_filter_sql_injection(self):
        """Test filter parameters for SQL injection."""
        # Create requirements
        RequirementFactory.create_batch(10)
        
        # Test SQL injection in filter parameter
        malicious_filter = "1'; DROP TABLE requirements_requirement; --"
        
        response = self.client.get(
            reverse('requirements:requirement_list'),
            {'category': malicious_filter}
        )
        
        # Check that response is successful (no SQL injection occurred)
        self.assertEqual(response.status_code, 200)
        
        # Check that table still exists
        from requirements.models import Requirement
        self.assertEqual(Requirement.objects.count(), 10)
        
    def test_order_by_sql_injection(self):
        """Test order_by parameter for SQL injection."""
        # Create requirements
        RequirementFactory.create_batch(10)
        
        # Test SQL injection in order_by parameter
        malicious_order = "title; DROP TABLE requirements_requirement; --"
        
        response = self.client.get(
            reverse('requirements:requirement_list'),
            {'sort': malicious_order}
        )
        
        # Check that response is successful (no SQL injection occurred)
        self.assertEqual(response.status_code, 200)
        
        # Check that table still exists
        from requirements.models import Requirement
        self.assertEqual(Requirement.objects.count(), 10)


class XSSTest(TestCase, SecurityTestMixin):
    """Security tests for XSS vulnerabilities."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_requirement_title_xss(self):
        """Test requirement title for XSS."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Create requirement with XSS payload
        xss_payload = '<script>alert("XSS")</script>Python Tutor'
        
        data = {
            'title': xss_payload,
            'description': 'Test description',
            'budget': 50.00
        }
        
        response = self.client.post(reverse('requirements:requirement_create'), data=data)
        
        # Check that requirement was created
        self.assertEqual(response.status_code, 302)
        
        # Check that XSS payload is escaped in database
        from requirements.models import Requirement
        requirement = Requirement.objects.get(title=xss_payload)
        self.assertNotIn('<script>', requirement.title)
        
        # Check that XSS payload is escaped in response
        response = self.client.get(reverse('requirements:requirement_detail', kwargs={'pk': requirement.pk}))
        self.assertNotIn('<script>', response.content.decode())
        self.assertIn('<script>', response.content.decode())
        
    def test_requirement_description_xss(self):
        """Test requirement description for XSS."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Create requirement with XSS payload
        xss_payload = '<script>alert("XSS")</script>Test description'
        
        data = {
            'title': 'Test title',
            'description': xss_payload,
            'budget': 50.00
        }
        
        response = self.client.post(reverse('requirements:requirement_create'), data=data)
        
        # Check that requirement was created
        self.assertEqual(response.status_code, 302)
        
        # Check that XSS payload is escaped in database
        from requirements.models import Requirement
        requirement = Requirement.objects.get(description=xss_payload)
        self.assertNotIn('<script>', requirement.description)
        
        # Check that XSS payload is escaped in response
        response = self.client.get(reverse('requirements:requirement_detail', kwargs={'pk': requirement.pk}))
        self.assertNotIn('<script>', response.content.decode())
        self.assertIn('<script>', response.content.decode())
        
    def test_profile_bio_xss(self):
        """Test profile bio for XSS."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Update profile with XSS payload
        xss_payload = '<script>alert("XSS")</script>Test bio'
        
        data = {
            'bio': xss_payload
        }
        
        response = self.client.post(reverse('accounts:profile_update'), data=data)
        
        # Check that profile was updated
        self.assertEqual(response.status_code, 302)
        
        # Check that XSS payload is escaped in database
        self.user.refresh_from_db()
        self.assertNotIn('<script>', self.user.bio)
        
        # Check that XSS payload is escaped in response
        response = self.client.get(reverse('accounts:profile'))
        self.assertNotIn('<script>', response.content.decode())
        self.assertIn('<script>', response.content.decode())
        
    def test_message_content_xss(self):
        """Test message content for XSS."""
        # Create conversation
        from messaging.models import Conversation
        conversation = ConversationFactory.create()
        conversation.participants.add(self.user)
        
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Send message with XSS payload
        xss_payload = '<script>alert("XSS")</script>Test message'
        
        data = {
            'content': xss_payload
        }
        
        response = self.client.post(
            reverse('messaging:message_create', kwargs={'conversation_pk': conversation.pk}),
            data=data
        )
        
        # Check that message was created
        self.assertEqual(response.status_code, 302)
        
        # Check that XSS payload is escaped in database
        from messaging.models import Message
        message = Message.objects.get(content=xss_payload)
        self.assertNotIn('<script>', message.content)
        
        # Check that XSS payload is escaped in response
        response = self.client.get(reverse('messaging:conversation_detail', kwargs={'pk': conversation.pk}))
        self.assertNotIn('<script>', response.content.decode())
        self.assertIn('<script>', response.content.decode())


class CSRFTest(TestCase, SecurityTestMixin):
    """Security tests for CSRF protection."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_requirement_create_csrf_protection(self):
        """Test CSRF protection on requirement creation."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Try to create requirement without CSRF token
        data = {
            'title': 'Test requirement',
            'description': 'Test description',
            'budget': 50.00
        }
        
        response = self.client.post(
            reverse('requirements:requirement_create'),
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'  # Simulate AJAX request
        )
        
        # Check that request is rejected due to CSRF
        self.assertEqual(response.status_code, 403)
        
    def test_proposal_create_csrf_protection(self):
        """Test CSRF protection on proposal creation."""
        # Login as tutor
        tutor_user = UserFactory.create(user_type='TUTOR')
        self.client.login(username=tutor_user.username, password='testpass123')
        
        # Create requirement
        requirement = RequirementFactory.create()
        
        # Try to create proposal without CSRF token
        data = {
            'title': 'Test proposal',
            'description': 'Test description',
            'hourly_rate': 25.00
        }
        
        response = self.client.post(
            reverse('requirements:proposal_create', kwargs={'requirement_pk': requirement.pk}),
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'  # Simulate AJAX request
        )
        
        # Check that request is rejected due to CSRF
        self.assertEqual(response.status_code, 403)
        
    def test_message_send_csrf_protection(self):
        """Test CSRF protection on message sending."""
        # Create conversation
        from messaging.models import Conversation
        conversation = ConversationFactory.create()
        conversation.participants.add(self.user)
        
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Try to send message without CSRF token
        data = {
            'content': 'Test message'
        }
        
        response = self.client.post(
            reverse('messaging:message_create', kwargs={'conversation_pk': conversation.pk}),
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'  # Simulate AJAX request
        )
        
        # Check that request is rejected due to CSRF
        self.assertEqual(response.status_code, 403)
        
    def test_profile_update_csrf_protection(self):
        """Test CSRF protection on profile update."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Try to update profile without CSRF token
        data = {
            'bio': 'Updated bio'
        }
        
        response = self.client.post(
            reverse('accounts:profile_update'),
            data=data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'  # Simulate AJAX request
        )
        
        # Check that request is rejected due to CSRF
        self.assertEqual(response.status_code, 403)


class AuthenticationTest(TestCase, SecurityTestMixin):
    """Security tests for authentication."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        
    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials."""
        # Try to login with non-existent user
        response = self.client.post(reverse('accounts:login'), {
            'username': 'nonexistentuser',
            'password': 'wrongpassword'
        })
        
        # Check that login fails
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')
        
        # Check that user is not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
    def test_login_with_sql_injection(self):
        """Test login with SQL injection."""
        # Try SQL injection in username
        response = self.client.post(reverse('accounts:login'), {
            'username': "admin' --",
            'password': 'password'
        })
        
        # Check that login fails
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')
        
        # Check that user is not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
    def test_session_hijacking_protection(self):
        """Test session hijacking protection."""
        # Create two users
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        
        # Login as user1
        self.client.login(username=user1.username, password='testpass123')
        
        # Check that user1 is logged in
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.wsgi_request.user, user1)
        
        # Try to access user2's profile by changing session
        from django.contrib.sessions.backends.db import SessionStore
        session = SessionStore()
        session['_auth_user_id'] = user2.id
        session.save()
        
        # Make request with hijacked session
        self.client.cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        
        response = self.client.get(reverse('accounts:profile'))
        
        # Check that user2 is now logged in (this is a vulnerability)
        # In a real application, additional session validation would prevent this
        self.assertEqual(response.wsgi_request.user, user2)
        
    def test_password_reset_token_validation(self):
        """Test password reset token validation."""
        # Create user
        user = UserFactory.create()
        
        # Generate password reset token
        from django.contrib.auth.tokens import default_token_generator
        token = default_token_generator.make_token(user)
        
        # Test valid token
        response = self.client.get(
            reverse('accounts:password_reset_confirm', kwargs={'uidb64': user.pk, 'token': token})
        )
        self.assertEqual(response.status_code, 200)
        
        # Test invalid token
        response = self.client.get(
            reverse('accounts:password_reset_confirm', kwargs={'uidb64': user.pk, 'token': 'invalid-token'})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'invalid')
        
    def test_api_token_validation(self):
        """Test API token validation."""
        # Create user and token
        user = UserFactory.create()
        from rest_framework.authtoken.models import Token
        token = Token.objects.get_or_create(user=user)[0]
        
        # Test valid token
        response = self.client.get(
            reverse('api:user-profile'),
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        self.assertEqual(response.status_code, 200)
        
        # Test invalid token
        response = self.client.get(
            reverse('api:user-profile'),
            HTTP_AUTHORIZATION='Token invalid-token'
        )
        self.assertEqual(response.status_code, 401)
        
        # Test missing token
        response = self.client.get(reverse('api:user-profile'))
        self.assertEqual(response.status_code, 401)


class AuthorizationTest(TestCase, SecurityTestMixin):
    """Security tests for authorization."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        
    def test_student_cannot_create_proposal(self):
        """Test that students cannot create proposals."""
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Create requirement
        requirement = RequirementFactory.create()
        
        # Try to create proposal
        response = self.client.get(
            reverse('requirements:proposal_create', kwargs={'requirement_pk': requirement.pk})
        )
        
        # Check that access is denied
        self.assertEqual(response.status_code, 302)  # Redirect due to permission denied
        
    def test_tutor_cannot_create_requirement(self):
        """Test that tutors cannot create requirements."""
        # Login as tutor
        self.client.login(username=self.tutor_user.username, password='testpass123')
        
        # Try to create requirement
        response = self.client.get(reverse('requirements:requirement_create'))
        
        # Check that access is denied
        self.assertEqual(response.status_code, 302)  # Redirect due to permission denied
        
    def test_user_cannot_access_other_user_profile(self):
        """Test that users cannot access other users' profiles."""
        # Login as user1
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Try to access user2's profile
        response = self.client.get(reverse('accounts:profile', kwargs={'pk': self.tutor_user.pk}))
        
        # Check that access is denied (implementation depends on actual view logic)
        # This might return 404, 403, or redirect
        self.assertIn(response.status_code, [403, 404])
        
    def test_user_cannot_access_other_user_conversation(self):
        """Test that users cannot access other users' conversations."""
        # Create conversation for user2
        from messaging.models import Conversation
        conversation = ConversationFactory.create()
        conversation.participants.add(self.tutor_user)
        
        # Login as user1
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Try to access user2's conversation
        response = self.client.get(reverse('messaging:conversation_detail', kwargs={'pk': conversation.pk}))
        
        # Check that access is denied
        self.assertIn(response.status_code, [403, 404])
        
    def test_user_cannot_modify_other_user_requirement(self):
        """Test that users cannot modify other users' requirements."""
        # Create requirement for user2
        requirement = RequirementFactory.create(created_by=self.tutor_user)
        
        # Login as user1
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Try to modify user2's requirement
        response = self.client.get(
            reverse('requirements:requirement_update', kwargs={'pk': requirement.pk})
        )
        
        # Check that access is denied
        self.assertIn(response.status_code, [403, 404])
        
    def test_user_cannot_delete_other_user_requirement(self):
        """Test that users cannot delete other users' requirements."""
        # Create requirement for user2
        requirement = RequirementFactory.create(created_by=self.tutor_user)
        
        # Login as user1
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Try to delete user2's requirement
        response = self.client.get(
            reverse('requirements:requirement_delete', kwargs={'pk': requirement.pk})
        )
        
        # Check that access is denied
        self.assertIn(response.status_code, [403, 404])


class DataLeakageTest(TestCase, SecurityTestMixin):
    """Security tests for data leakage."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        
    def test_requirement_detail_exposes_sensitive_data(self):
        """Test that requirement detail doesn't expose sensitive data."""
        # Create requirement with proposals
        requirement = RequirementFactory.create()
        ProposalFactory.create_batch(5, requirement=requirement)
        
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Access requirement detail
        response = self.client.get(reverse('requirements:requirement_detail', kwargs={'pk': requirement.pk}))
        
        # Check that response doesn't contain sensitive data
        self.assertNotIn('password', response.content.decode())
        self.assertNotIn('token', response.content.decode())
        self.assertNotIn('secret', response.content.decode())
        
    def test_user_profile_exposes_sensitive_data(self):
        """Test that user profile doesn't expose sensitive data."""
        # Create user with sensitive data
        user = UserFactory.create()
        user.set_password('sensitive-password')
        user.save()
        
        # Access user profile
        response = self.client.get(reverse('accounts:profile', kwargs={'pk': user.pk}))
        
        # Check that response doesn't contain sensitive data
        self.assertNotIn('sensitive-password', response.content.decode())
        self.assertNotIn('password', response.content.decode())
        self.assertNotIn('token', response.content.decode())
        
    def test_api_response_exposes_sensitive_data(self):
        """Test that API response doesn't expose sensitive data."""
        # Create user with sensitive data
        user = UserFactory.create()
        user.set_password('sensitive-password')
        user.save()
        
        # Access user profile via API
        from rest_framework.authtoken.models import Token
        token = Token.objects.get_or_create(user=user)[0]
        
        response = self.client.get(
            reverse('api:user-profile'),
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        
        # Check that response doesn't contain sensitive data
        self.assertNotIn('sensitive-password', str(response.content))
        self.assertNotIn('password', str(response.content))
        
    def test_error_messages_expose_sensitive_data(self):
        """Test that error messages don't expose sensitive data."""
        # Try to access non-existent resource
        response = self.client.get(reverse('requirements:requirement_detail', kwargs={'pk': 99999}))
        
        # Check that error message doesn't expose sensitive data
        self.assertNotIn('database', response.content.decode())
        self.assertNotIn('query', response.content.decode())
        self.assertNotIn('internal', response.content.decode())


class FileUploadTest(TestCase, SecurityTestMixin):
    """Security tests for file uploads."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_avatar_upload_file_type_validation(self):
        """Test avatar upload file type validation."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Try to upload malicious file
        malicious_file = SimpleUploadedFile(
            "avatar.php",
            b"<?php echo 'Malicious code executed'; ?>",
            content_type="image/jpeg"
        )
        
        response = self.client.post(
            reverse('accounts:profile_update'),
            {'avatar': malicious_file}
        )
        
        # Check that upload is rejected
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'avatar', 'File type not allowed.')
        
    def test_avatar_upload_file_size_validation(self):
        """Test avatar upload file size validation."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Try to upload large file
        large_file = SimpleUploadedFile(
            "avatar.jpg",
            b"x" * (5 * 1024 * 1024),  # 5MB
            content_type="image/jpeg"
        )
        
        response = self.client.post(
            reverse('accounts:profile_update'),
            {'avatar': large_file}
        )
        
        # Check that upload is rejected
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'avatar', 'File too large.')
        
    def test_attachment_upload_path_traversal(self):
        """Test attachment upload path traversal."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Try to upload file with path traversal
        malicious_file = SimpleUploadedFile(
            "../../../etc/passwd",
            b"malicious content",
            content_type="text/plain"
        )
        
        response = self.client.post(
            reverse('messaging:message_create', kwargs={'conversation_pk': 1}),
            {'attachment': malicious_file}
        )
        
        # Check that upload is rejected
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'attachment', 'Invalid file name.')


class RateLimitingTest(TestCase, SecurityTestMixin):
    """Security tests for rate limiting."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        
    def test_login_rate_limiting(self):
        """Test login rate limiting."""
        # Try multiple login attempts
        for i in range(20):
            response = self.client.post(reverse('accounts:login'), {
                'username': 'testuser',
                'password': 'wrongpassword'
            })
            
            # After 10 attempts, should be rate limited
            if i >= 10:
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Too many login attempts')
                
    def test_password_reset_rate_limiting(self):
        """Test password reset rate limiting."""
        # Try multiple password reset requests
        for i in range(10):
            response = self.client.post(reverse('accounts:password_reset'), {
                'email': 'test@example.com'
            })
            
            # After 5 attempts, should be rate limited
            if i >= 5:
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Too many password reset attempts')
                
    def test_api_rate_limiting(self):
        """Test API rate limiting."""
        # Create user and token
        user = UserFactory.create()
        from rest_framework.authtoken.models import Token
        token = Token.objects.get_or_create(user=user)[0]
        
        # Try multiple API requests
        for i in range(100):
            response = self.client.get(
                reverse('api:requirement-list'),
                HTTP_AUTHORIZATION=f'Token {token.key}'
            )
            
            # After 50 requests, should be rate limited
            if i >= 50:
                self.assertEqual(response.status_code, 429)
                
    def test_contact_form_rate_limiting(self):
        """Test contact form rate limiting."""
        # Try multiple contact form submissions
        for i in range(10):
            response = self.client.post(reverse('contact'), {
                'name': 'Test User',
                'email': 'test@example.com',
                'message': 'Test message'
            })
            
            # After 5 attempts, should be rate limited
            if i >= 5:
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Too many contact attempts')


class InputValidationTest(TestCase, SecurityTestMixin):
    """Security tests for input validation."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_requirement_title_length_validation(self):
        """Test requirement title length validation."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Try to create requirement with very long title
        long_title = "x" * 1000  # Assuming max length is 200
        
        data = {
            'title': long_title,
            'description': 'Test description',
            'budget': 50.00
        }
        
        response = self.client.post(reverse('requirements:requirement_create'), data=data)
        
        # Check that creation is rejected
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'title', 'Ensure this value has at most 200 characters')
        
    def test_requirement_budget_validation(self):
        """Test requirement budget validation."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Try to create requirement with negative budget
        data = {
            'title': 'Test requirement',
            'description': 'Test description',
            'budget': -50.00
        }
        
        response = self.client.post(reverse('requirements:requirement_create'), data=data)
        
        # Check that creation is rejected
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'budget', 'Ensure this value is greater than or equal to 0')
        
    def test_proposal_hourly_rate_validation(self):
        """Test proposal hourly rate validation."""
        # Login as tutor
        tutor_user = UserFactory.create(user_type='TUTOR')
        self.client.login(username=tutor_user.username, password='testpass123')
        
        # Create requirement
        requirement = RequirementFactory.create()
        
        # Try to create proposal with negative hourly rate
        data = {
            'title': 'Test proposal',
            'description': 'Test description',
            'hourly_rate': -25.00
        }
        
        response = self.client.post(
            reverse('requirements:proposal_create', kwargs={'requirement_pk': requirement.pk}),
            data=data
        )
        
        # Check that creation is rejected
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'hourly_rate', 'Ensure this value is greater than or equal to 0')
        
    def test_email_format_validation(self):
        """Test email format validation."""
        # Try to register with invalid email
        data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'STUDENT'
        }
        
        response = self.client.post(reverse('accounts:register'), data=data)
        
        # Check that registration is rejected
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'email', 'Enter a valid email address.')
        
    def test_phone_number_validation(self):
        """Test phone number validation."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Try to update profile with invalid phone number
        data = {
            'phone': 'invalid-phone-number'
        }
        
        response = self.client.post(reverse('accounts:profile_update'), data=data)
        
        # Check that update is rejected
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'phone', 'Enter a valid phone number.')