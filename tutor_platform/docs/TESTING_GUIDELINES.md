# Django Tutoring Platform - Testing Guidelines for Contributors

## Overview

This document provides guidelines for contributors on how to write, run, and maintain tests for the Django Tutoring Platform. Following these guidelines ensures consistent, high-quality tests across the project.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Running Tests](#running-tests)
3. [Writing Tests](#writing-tests)
4. [Test Structure](#test-structure)
5. [Test Data Management](#test-data-management)
6. [Mocking and External Services](#mocking-and-external-services)
7. [Performance Considerations](#performance-considerations)
8. [Security Testing](#security-testing)
9. [Frontend Testing](#frontend-testing)
10. [Code Review Guidelines](#code-review-guidelines)
11. [Troubleshooting](#troubleshooting)

## Getting Started

### Prerequisites

1. **Python 3.10+**: Ensure you have the correct Python version installed
2. **Virtual Environment**: Set up a virtual environment for the project
3. **Database**: PostgreSQL for integration tests (SQLite works for unit tests)
4. **Node.js 18+**: Required for frontend tests

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/your-org/django-tutor-platform.git
cd django-tutor-platform

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt

# Install Node.js dependencies (for frontend tests)
npm install

# Set up test database
python manage.py migrate --settings=tutor_platform.test_settings

# Create initial test data
python manage.py generate_test_data --settings=tutor_platform.test_settings
```

## Running Tests

### Running All Tests

```bash
# Run all tests with coverage
python manage.py run_all_tests

# Or using pytest directly
pytest --cov=tutor_platform --cov-report=html
```

### Running Specific Test Categories

```bash
# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run API tests only
pytest tests/api/

# Run performance tests only
pytest tests/performance/

# Run security tests only
pytest tests/security/

# Run frontend tests only
pytest tests/frontend/
```

### Running Specific Test Files

```bash
# Run specific test file
pytest tests/unit/test_accounts_models.py

# Run specific test class
pytest tests/unit/test_accounts_models.py::TestUserModel

# Run specific test method
pytest tests/unit/test_accounts_models.py::TestUserModel::test_create_user_with_email_successful
```

### Running Tests with Different Options

```bash
# Run tests with verbose output
pytest -v

# Run tests with coverage report
pytest --cov=tutor_platform --cov-report=html

# Run tests with specific markers
pytest -m "unit"

# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Stop on first failure
pytest -x

# Run failed tests only
pytest --lf
```

## Writing Tests

### Test Naming Conventions

1. **Test Files**: Use `test_` prefix, e.g., `test_user_model.py`
2. **Test Classes**: Use `Test` prefix, e.g., `TestUserModel`
3. **Test Methods**: Use `test_` prefix with descriptive names, e.g., `test_user_creation_with_valid_email`

### Test Structure

```python
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class TestUserModel(TestCase):
    """Test cases for the User model."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up data for the entire test class."""
        cls.user_data = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
        }
    
    def setUp(self):
        """Set up data for each test method."""
        self.user = User.objects.create_user(**self.user_data)
    
    def test_user_creation_with_valid_data(self):
        """Test creating a user with valid data."""
        self.assertEqual(self.user.email, self.user_data['email'])
        self.assertTrue(self.user.check_password(self.user_data['password']))
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
    
    def test_user_str_representation(self):
        """Test the string representation of a user."""
        expected = f"{self.user.first_name} {self.user.last_name}"
        self.assertEqual(str(self.user), expected)
    
    def tearDown(self):
        """Clean up after each test method."""
        self.user.delete()
```

### Test Categories and When to Use Them

#### Unit Tests
- **Purpose**: Test individual components in isolation
- **When to use**: For model methods, utility functions, form validation
- **Characteristics**: Fast, isolated, no external dependencies

```python
def test_normalize_email_function():
    """Test email normalization function."""
    from accounts.utils import normalize_email
    
    assert normalize_email('Test@Example.COM') == 'test@example.com'
    assert normalize_email('user@sub.example.com') == 'user@sub.example.com'
```

#### Integration Tests
- **Purpose**: Test interactions between components
- **When to use**: For user workflows, API endpoints, database operations
- **Characteristics**: Slower, uses real database, tests multiple components

```python
def test_user_registration_workflow(self):
    """Test complete user registration workflow."""
    response = self.client.post('/register/', {
        'email': 'newuser@example.com',
        'password1': 'complexpass123',
        'password2': 'complexpass123',
        'first_name': 'New',
        'last_name': 'User',
    })
    
    self.assertEqual(response.status_code, 302)
    self.assertTrue(User.objects.filter(email='newuser@example.com').exists())
```

#### API Tests
- **Purpose**: Test API endpoints specifically
- **When to use**: For REST API endpoints, authentication, permissions
- **Characteristics**: Uses API client, tests HTTP responses

```python
def test_api_user_retrieval(self):
    """Test API user retrieval endpoint."""
    url = reverse('api:user-detail', kwargs={'pk': self.user.pk})
    response = self.client.get(url)
    
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.data['email'], self.user.email)
```

#### Performance Tests
- **Purpose**: Test performance characteristics
- **When to use**: For database queries, API response times, memory usage
- **Characteristics**: Uses benchmarking, measures performance metrics

```python
def test_user_query_performance(self, benchmark):
    """Test user query performance."""
    def query_users():
        return list(User.objects.filter(is_active=True))
    
    result = benchmark(query_users)
    assert len(result) > 0
```

## Test Data Management

### Using Factories

```python
import pytest
from tests.factories import UserFactory, TutorProfileFactory

def test_tutor_profile_creation():
    """Test tutor profile creation using factory."""
    tutor = TutorProfileFactory()
    
    assert tutor.user is not None
    assert tutor.hourly_rate > 0
    assert len(tutor.subjects.all()) > 0
```

### Creating Custom Fixtures

```python
@pytest.fixture
def active_tutor(db):
    """Create an active tutor for testing."""
    user = UserFactory(is_active=True)
    tutor = TutorProfileFactory(user=user, is_verified=True)
    return tutor

def test_tutor_can_create_proposal(active_tutor):
    """Test that an active tutor can create a proposal."""
    proposal = ProposalFactory(tutor=active_tutor)
    assert proposal.status == Proposal.PENDING
```

### Test Data Cleanup

```python
class TestWithTemporaryData(TestCase):
    """Base class for tests with temporary data."""
    
    def setUp(self):
        """Set up temporary test data."""
        self.temp_files = []
        self.temp_users = []
    
    def tearDown(self):
        """Clean up temporary test data."""
        for file_path in self.temp_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        for user in self.temp_users:
            user.delete()
```

## Mocking and External Services

### Mocking External APIs

```python
from unittest.mock import patch, Mock

@patch('paypal_integration.services.PayPalAPI.create_payment')
def test_paypal_payment_creation(self, mock_create_payment):
    """Test PayPal payment creation with mocked API."""
    # Configure mock
    mock_create_payment.return_value = {
        'id': 'PAY-123456789',
        'status': 'created',
        'links': [{'rel': 'approve', 'href': 'https://paypal.com/approve'}]
    }
    
    # Test the function
    result = create_paypal_payment(100.00, 'USD')
    
    # Assertions
    self.assertEqual(result['id'], 'PAY-123456789')
    mock_create_payment.assert_called_once_with(100.00, 'USD')
```

### Mocking Email Sending

```python
from django.core import mail
from django.test import override_settings

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
def test_email_notification_sending(self):
    """Test email notification sending."""
    # Trigger email sending
    send_notification_email(self.user, 'Test Subject', 'Test Message')
    
    # Assertions
    self.assertEqual(len(mail.outbox), 1)
    self.assertEqual(mail.outbox[0].subject, 'Test Subject')
    self.assertEqual(mail.outbox[0].to, [self.user.email])
```

### Mocking File Operations

```python
from unittest.mock import mock_open, patch

@patch('builtins.open', new_callable=mock_open, read_data='file content')
def test_file_processing(self, mock_file):
    """Test file processing with mocked file operations."""
    result = process_file('test_file.txt')
    
    self.assertEqual(result, 'processed: file content')
    mock_file.assert_called_once_with('test_file.txt', 'r')
```

## Performance Considerations

### Database Query Optimization

```python
def test_optimized_user_query(self):
    """Test optimized user query with select_related."""
    # Inefficient query (N+1 problem)
    with self.assertNumQueries(5):  # One query per tutor profile
        tutors = TutorProfile.objects.all()
        for tutor in tutors:
            print(tutor.user.email)
    
    # Optimized query
    with self.assertNumQueries(1):
        tutors = TutorProfile.objects.select_related('user').all()
        for tutor in tutors:
            print(tutor.user.email)
```

### Test Performance Measurement

```python
import time
from django.test.utils import override_settings

def test_page_load_performance(self):
    """Test page load performance."""
    start_time = time.time()
    
    response = self.client.get('/requirements/')
    
    end_time = time.time()
    load_time = end_time - start_time
    
    self.assertEqual(response.status_code, 200)
    self.assertLess(load_time, 1.0)  # Should load in less than 1 second
```

### Memory Usage Testing

```python
import psutil
import os

def test_memory_usage(self):
    """Test memory usage of a function."""
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss
    
    # Run memory-intensive operation
    process_large_dataset()
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Memory increase should be reasonable (less than 100MB)
    self.assertLess(memory_increase, 100 * 1024 * 1024)
```

## Security Testing

### Testing Authentication

```python
def test_authentication_required(self):
    """Test that authentication is required for protected views."""
    response = self.client.get('/dashboard/')
    
    self.assertEqual(response.status_code, 302)
    self.assertIn('login', response.url)
    
    # Test with authenticated user
    self.client.login(email='test@example.com', password='testpass123')
    response = self.client.get('/dashboard/')
    
    self.assertEqual(response.status_code, 200)
```

### Testing Authorization

```python
def test_authorization_permissions(self):
    """Test that users can only access their own data."""
    # Create two users
    user1 = UserFactory()
    user2 = UserFactory()
    
    # User1 tries to access User2's profile
    self.client.login(email=user1.email, password='password')
    response = self.client.get(f'/profile/{user2.pk}/')
    
    self.assertEqual(response.status_code, 403)
```

### Testing Input Validation

```python
def test_sql_injection_prevention(self):
    """Test SQL injection prevention."""
    malicious_input = "'; DROP TABLE users; --"
    
    # This should not cause any SQL injection
    response = self.client.post('/search/', {'q': malicious_input})
    
    self.assertEqual(response.status_code, 200)
    # Users table should still exist
    self.assertTrue(User.objects.exists())
```

### Testing XSS Prevention

```python
def test_xss_prevention(self):
    """Test XSS prevention in user input."""
    xss_payload = '<script>alert("XSS")</script>'
    
    # Create user with malicious input
    user = UserFactory(first_name=xss_payload)
    
    # Render template with user data
    response = self.client.get(f'/profile/{user.pk}/')
    
    self.assertEqual(response.status_code, 200)
    # Script tag should be escaped
    self.assertNotIn('<script>', response.content.decode())
    self.assertIn('<script>', response.content.decode())
```

## Frontend Testing

### Testing JavaScript Functionality

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_form_validation_with_selenium(self):
    """Test form validation using Selenium."""
    self.driver = webdriver.Chrome()
    self.driver.get(self.live_server_url + '/register/')
    
    # Try to submit form without required fields
    submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
    submit_button.click()
    
    # Check for validation errors
    error_elements = self.driver.find_elements(By.CSS_SELECTOR, '.error-message')
    self.assertGreater(len(error_elements), 0)
    
    self.driver.quit()
```

### Testing HTMX Interactions

```python
def test_htmx_dynamic_content_loading(self):
    """Test HTMX dynamic content loading."""
    response = self.client.post(
        '/load-more-requirements/',
        {'offset': 10},
        HTTP_HX_REQUEST='true'
    )
    
    self.assertEqual(response.status_code, 200)
    self.assertContains(response, 'requirement-card')
```

### Testing Responsive Design

```python
def test_mobile_responsive_design(self):
    """Test mobile responsive design."""
    # Test with mobile viewport
    self.client.defaults['HTTP_USER_AGENT'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
    
    response = self.client.get('/')
    
    self.assertEqual(response.status_code, 200)
    # Check for mobile-specific elements
    self.assertContains(response, 'mobile-navigation')
```

## Code Review Guidelines

### Before Submitting Code

1. **Run Tests Locally**
   ```bash
   python manage.py run_all_tests
   ```

2. **Check Test Coverage**
   ```bash
   python manage.py test_coverage
   ```

3. **Run Security Tests**
   ```bash
   python manage.py security_test
   ```

4. **Run Performance Tests**
   ```bash
   python manage.py performance_test
   ```

### Test Requirements for New Features

1. **Unit Tests**: At least 80% coverage for new code
2. **Integration Tests**: For new workflows
3. **API Tests**: For new API endpoints
4. **Security Tests**: For authentication/authorization changes
5. **Performance Tests**: For database-intensive features

### Code Review Checklist

- [ ] Tests are included for new functionality
- [ ] Tests cover edge cases and error conditions
- [ ] Tests use appropriate mocking for external services
- [ ] Tests have meaningful assertions
- [ ] Tests follow naming conventions
- [ ] Tests are well-structured and readable
- [ ] Tests don't have unnecessary dependencies
- [ ] Tests clean up after themselves

## Troubleshooting

### Common Issues

#### Test Database Issues

```bash
# Reset test database
python manage.py flush --settings=tutor_platform.test_settings

# Recreate test database
python manage.py migrate --settings=tutor_platform.test_settings
```

#### Flaky Tests

```python
# Add retry decorator for flaky tests
from pytest import mark

@mark.flaky(reruns=3, reruns_delay=1)
def test_sometimes_failing_test(self):
    """Test that sometimes fails."""
    pass
```

#### Slow Tests

```python
# Use pytest-benchmark to identify slow tests
pytest --benchmark-only

# Profile slow tests
pytest --profile
```

#### Import Issues

```bash
# Check Python path
python -c "import sys; print(sys.path)"

# Verify Django settings
python manage.py check --settings=tutor_platform.test_settings
```

### Debugging Tips

1. **Use pdb for debugging**
   ```python
   import pdb; pdb.set_trace()
   ```

2. **Enable Django debug toolbar**
   ```python
   # In test_settings.py
   DEBUG = True
   INSTALLED_APPS += ['debug_toolbar']
   ```

3. **Print query information**
   ```python
   from django.db import connection
   print(connection.queries)
   ```

4. **Use Django test client debugging**
   ```python
   response = self.client.get('/some-url/')
   print(response.content.decode())
   print(response.context)
   ```

### Getting Help

1. **Check existing tests** for similar patterns
2. **Consult the test documentation** in `docs/TEST_CASES.md`
3. **Ask for help** in project discussions or issues
4. **Review pytest documentation** for advanced features

## Conclusion

Following these guidelines ensures that our test suite remains maintainable, reliable, and comprehensive. Good tests are essential for the long-term success of the Django Tutoring Platform.

Remember:
- Write tests before or alongside code
- Keep tests simple and focused
- Test behavior, not implementation
- Maintain high test coverage
- Run tests frequently

Thank you for contributing to the Django Tutoring Platform!