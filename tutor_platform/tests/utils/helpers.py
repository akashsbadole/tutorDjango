"""
Test utilities and helpers for Django Tutor Platform.

This module contains utility functions and helper classes for testing.
"""
import json
import time
from contextlib import contextmanager
from unittest.mock import Mock, patch
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.mail import outbox
from rest_framework.test import APITestCase
from rest_framework import status
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

User = get_user_model()


class TestMixin:
    """Mixin class with common test utilities."""
    
    def setUp(self):
        """Set up test environment."""
        self.client = Client()
        self.api_client = APIClient()
        
    def tearDown(self):
        """Clean up after tests."""
        # Reset email outbox
        outbox.clear()
        
    def create_authenticated_client(self, user):
        """Create an authenticated client for the given user."""
        client = Client()
        client.force_login(user)
        return client
        
    def create_authenticated_api_client(self, user):
        """Create an authenticated API client for the given user."""
        client = APIClient()
        client.force_authenticate(user=user)
        return client
        
    def assert_response_status(self, response, expected_status):
        """Assert response has expected status code."""
        self.assertEqual(response.status_code, expected_status,
                        f"Expected status {expected_status}, got {response.status_code}")
                        
    def assert_json_response(self, response, expected_data=None, status_code=200):
        """Assert response is valid JSON with expected data."""
        self.assert_response_status(response, status_code)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        if expected_data is not None:
            actual_data = json.loads(response.content)
            self.assertEqual(actual_data, expected_data)
            
    def assert_template_used(self, response, template_name):
        """Assert specific template was used."""
        self.assertTemplateUsed(response, template_name)
        
    def assert_messages(self, response, expected_messages):
        """Assert messages contain expected content."""
        messages = list(response.context['messages'])
        actual_messages = [str(msg) for msg in messages]
        for expected_msg in expected_messages:
            self.assertIn(expected_msg, actual_messages)
            
    def get_reverse_url(self, name, args=None, kwargs=None):
        """Get URL by reverse name with optional args/kwargs."""
        return reverse(name, args=args, kwargs=kwargs)
        
    def post_json(self, url, data, **kwargs):
        """Make a POST request with JSON data."""
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json',
            **kwargs
        )
        
    def put_json(self, url, data, **kwargs):
        """Make a PUT request with JSON data."""
        return self.client.put(
            url,
            data=json.dumps(data),
            content_type='application/json',
            **kwargs
        )
        
    def patch_json(self, url, data, **kwargs):
        """Make a PATCH request with JSON data."""
        return self.client.patch(
            url,
            data=json.dumps(data),
            content_type='application/json',
            **kwargs
        )


class AuthTestMixin(TestMixin):
    """Mixin for authentication-related tests."""
    
    def create_test_user(self, **kwargs):
        """Create a test user."""
        from tests.factories import UserFactory
        return UserFactory.create(**kwargs)
        
    def create_test_tutor(self, **kwargs):
        """Create a test tutor."""
        from tests.factories import create_test_tutor
        return create_test_tutor(**kwargs)
        
    def create_test_student(self, **kwargs):
        """Create a test student."""
        from tests.factories import create_test_student
        return create_test_student(**kwargs)
        
    def create_test_admin(self, **kwargs):
        """Create a test admin user."""
        from tests.factories import AdminUserFactory
        return AdminUserFactory.create(**kwargs)
        
    def login_user(self, user):
        """Log in a user."""
        self.client.login(username=user.username, password='password')
        return self.client
        
    def logout_user(self):
        """Log out current user."""
        self.client.logout()


class APITestMixin(TestMixin):
    """Mixin for API-related tests."""
    
    def setUp(self):
        """Set up API test environment."""
        super().setUp()
        self.api_prefix = '/api/v1'
        
    def get_api_url(self, endpoint):
        """Get full API URL for endpoint."""
        return f"{self.api_prefix}/{endpoint}"
        
    def assert_api_response(self, response, expected_status=status.HTTP_200_OK):
        """Assert API response has expected status."""
        self.assertEqual(response.status_code, expected_status)
        
    def assert_api_error(self, response, expected_error, expected_status=status.HTTP_400_BAD_REQUEST):
        """Assert API response contains expected error."""
        self.assert_api_response(response, expected_status)
        self.assertIn(expected_error, str(response.content))
        
    def get_api_response(self, endpoint, **kwargs):
        """Make GET request to API endpoint."""
        url = self.get_api_url(endpoint)
        return self.api_client.get(url, **kwargs)
        
    def post_api_response(self, endpoint, data, **kwargs):
        """Make POST request to API endpoint."""
        url = self.get_api_url(endpoint)
        return self.api_client.post(url, data, **kwargs)
        
    def put_api_response(self, endpoint, data, **kwargs):
        """Make PUT request to API endpoint."""
        url = self.get_api_url(endpoint)
        return self.api_client.put(url, data, **kwargs)
        
    def delete_api_response(self, endpoint, **kwargs):
        """Make DELETE request to API endpoint."""
        url = self.get_api_url(endpoint)
        return self.api_client.delete(url, **kwargs)


class SeleniumTestMixin:
    """Mixin for Selenium-based frontend tests."""
    
    def setUp(self):
        """Set up Selenium test environment."""
        from selenium.webdriver.chrome.webdriver import WebDriver
        self.driver = WebDriver()
        self.driver.implicitly_wait(10)
        
    def tearDown(self):
        """Clean up Selenium test environment."""
        self.driver.quit()
        
    def wait_for_element(self, locator, timeout=10):
        """Wait for element to be present."""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
        
    def wait_for_clickable(self, locator, timeout=10):
        """Wait for element to be clickable."""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )
        
    def find_element(self, locator):
        """Find element on page."""
        return self.driver.find_element(*locator)
        
    def find_elements(self, locator):
        """Find multiple elements on page."""
        return self.driver.find_elements(*locator)
        
    def click_element(self, locator):
        """Click element on page."""
        element = self.wait_for_clickable(locator)
        element.click()
        return element
        
    def type_text(self, locator, text):
        """Type text into input field."""
        element = self.wait_for_element(locator)
        element.clear()
        element.send_keys(text)
        return element
        
    def get_element_text(self, locator):
        """Get text from element."""
        element = self.wait_for_element(locator)
        return element.text
        
    def is_element_present(self, locator):
        """Check if element is present on page."""
        try:
            self.driver.find_element(*locator)
            return True
        except:
            return False
            
    def scroll_to_element(self, locator):
        """Scroll to element on page."""
        element = self.wait_for_element(locator)
        self.driver.execute_script("arguments[0].scrollIntoView();", element)
        return element


class PerformanceTestMixin:
    """Mixin for performance-related tests."""
    
    @contextmanager
    def measure_time(self):
        """Context manager to measure execution time."""
        start_time = time.time()
        yield
        end_time = time.time()
        self.execution_time = end_time - start_time
        
    def assert_max_execution_time(self, max_seconds):
        """Assert execution time is within limits."""
        self.assertLessEqual(
            self.execution_time, max_seconds,
            f"Execution time {self.execution_time}s exceeds maximum {max_seconds}s"
        )
        
    def measure_query_count(self):
        """Context manager to measure database queries."""
        from django.test.utils import override_settings
        from django.db import connection
        
        with self.assertNumQueries(0):  # Will be overridden by actual usage
            yield connection.queries
            
    def assert_query_count(self, expected_count):
        """Assert specific number of database queries were executed."""
        from django.test.utils import override_settings
        from django.db import connection
        
        initial_queries = len(connection.queries)
        yield
        final_queries = len(connection.queries)
        actual_count = final_queries - initial_queries
        self.assertEqual(
            actual_count, expected_count,
            f"Expected {expected_count} queries, got {actual_count}"
        )


class SecurityTestMixin:
    """Mixin for security-related tests."""
    
    def test_sql_injection_protection(self, url, injection_strings):
        """Test SQL injection protection on endpoint."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "1' UNION SELECT * FROM users --",
            "'; DELETE FROM auth_user; --"
        ]
        
        for injection in malicious_inputs:
            response = self.client.get(url, {'q': injection})
            # Should not return 500 error (indicating SQL injection worked)
            self.assertNotEqual(response.status_code, 500)
            
    def test_xss_protection(self, url, xss_strings):
        """Test XSS protection on endpoint."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "'\"><script>alert('XSS')</script>"
        ]
        
        for payload in xss_payloads:
            response = self.client.post(url, {'content': payload})
            # Response should not contain unescaped script tags
            self.assertNotIn('<script>', response.content.decode())
            
    def test_csrf_protection(self, url):
        """Test CSRF protection on endpoint."""
        # Request without CSRF token should fail
        response = self.client.post(url, {'data': 'test'})
        self.assertEqual(response.status_code, 403)
        
    def test_authentication_required(self, url):
        """Test endpoint requires authentication."""
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
    def test_authorization_required(self, url, unauthorized_user):
        """Test endpoint requires proper authorization."""
        self.client.force_login(unauthorized_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


class EmailTestMixin:
    """Mixin for email-related tests."""
    
    def assert_email_sent(self, count=1):
        """Assert specific number of emails were sent."""
        self.assertEqual(len(outbox), count)
        
    def assert_email_contains(self, content, email_index=0):
        """Assert email contains specific content."""
        email = outbox[email_index]
        self.assertIn(content, email.body)
        self.assertIn(content, email.subject)
        
    def assert_email_recipient(self, recipient, email_index=0):
        """Assert email was sent to specific recipient."""
        email = outbox[email_index]
        self.assertIn(recipient, [addr[1] for addr in email.to])
        
    def get_latest_email(self):
        """Get the most recent email sent."""
        return outbox[-1] if outbox else None
        
    def clear_emails(self):
        """Clear email outbox."""
        outbox.clear()


class FileTestMixin:
    """Mixin for file upload/download tests."""
    
    def create_test_file(self, filename='test.txt', content=b'test content'):
        """Create a test file for upload."""
        return SimpleUploadedFile(
            filename,
            content,
            content_type='text/plain'
        )
        
    def create_test_image(self, filename='test.jpg', size=(100, 100)):
        """Create a test image file for upload."""
        from PIL import Image
        import io
        
        image = Image.new('RGB', size, color='red')
        image_io = io.BytesIO()
        image.save(image_io, 'JPEG')
        image_io.seek(0)
        
        return SimpleUploadedFile(
            filename,
            image_io.getvalue(),
            content_type='image/jpeg'
        )
        
    def assert_file_downloaded(self, response, filename=None):
        """Assert file was downloaded successfully."""
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.streaming or response.has_header('Content-Disposition'))
        
        if filename:
            content_disposition = response.get('Content-Disposition', '')
            self.assertIn(filename, content_disposition)


class MockMixin:
    """Mixin for mocking external services."""
    
    @contextmanager
    def mock_paypal_service(self):
        """Mock PayPal service."""
        with patch('paypal_integration.services.PayPalPaymentService') as mock:
            yield mock
            
    @contextmanager
    def mock_email_service(self):
        """Mock email service."""
        with patch('django.core.mail.send_mail') as mock:
            yield mock
            
    @contextmanager
    def mock_notification_service(self):
        """Mock notification service."""
        with patch('notifications.services.NotificationService') as mock:
            yield mock
            
    @contextmanager
    def mock_search_service(self):
        """Mock search service."""
        with patch('search.services.SearchService') as mock:
            yield mock
            
    def create_mock_response(self, data, status_code=200):
        """Create a mock HTTP response."""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = data
        mock_response.content = json.dumps(data).encode()
        return mock_response


class DateTimeTestMixin:
    """Mixin for date/time related tests."""
    
    def create_past_date(self, days=1, hours=0, minutes=0):
        """Create a date in the past."""
        return timezone.now() - timezone.timedelta(
            days=days, hours=hours, minutes=minutes
        )
        
    def create_future_date(self, days=1, hours=0, minutes=0):
        """Create a date in the future."""
        return timezone.now() + timezone.timedelta(
            days=days, hours=hours, minutes=minutes
        )
        
    def assert_datetime_close(self, actual, expected, tolerance_seconds=60):
        """Assert two datetimes are close within tolerance."""
        difference = abs(actual - expected)
        self.assertLessEqual(
            difference.total_seconds(), tolerance_seconds,
            f"Datetime difference {difference.total_seconds()}s exceeds tolerance {tolerance_seconds}s"
        )


class PaginationTestMixin:
    """Mixin for pagination-related tests."""
    
    def test_pagination(self, url, total_items, page_size=20):
        """Test pagination functionality."""
        # Test first page
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Test page parameter
        response = self.client.get(url, {'page': 2})
        self.assertEqual(response.status_code, 200)
        
        # Test page size parameter
        response = self.client.get(url, {'page_size': 10})
        self.assertEqual(response.status_code, 200)
        
        # Test invalid page number
        response = self.client.get(url, {'page': 999})
        self.assertEqual(response.status_code, 404)
        
        # Test invalid page size
        response = self.client.get(url, {'page_size': 999})
        self.assertEqual(response.status_code, 400)