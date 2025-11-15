# Django Tutoring Platform - Testing Infrastructure

This directory contains the comprehensive testing infrastructure for the Django Tutoring Platform. It includes unit tests, integration tests, API tests, performance tests, security tests, frontend tests, and all supporting utilities.

## Directory Structure

```
tests/
├── __init__.py                 # Tests package initialization
├── apps.py                     # Tests app configuration
├── factories.py                # Test data factories
├── unit/                       # Unit tests
│   ├── test_accounts_models.py
│   ├── test_requirements_models.py
│   ├── test_messaging_models.py
│   ├── test_paymentsdetails_models.py
│   ├── test_notifications_models.py
│   ├── test_paypal_integration_models.py
│   ├── test_admin_portal_models.py
│   ├── test_search_models.py
│   ├── test_ui_components_models.py
│   ├── test_accounts_views.py
│   ├── test_requirements_views.py
│   ├── test_forms.py
│   └── test_utils.py
├── integration/                # Integration tests
│   └── test_user_workflows.py
├── api/                        # API tests
│   └── test_api_endpoints.py
├── performance/                # Performance tests
│   └── test_performance.py
├── security/                   # Security tests
│   └── test_security.py
├── frontend/                   # Frontend tests
│   ├── test_frontend.py
│   └── test_mobile.py
├── payment/                    # Payment tests
│   └── test_payment.py
├── email/                      # Email tests
│   └── test_email.py
├── fixtures/                   # Test fixtures
│   └── test_fixtures.py
├── utils/                      # Test utilities
│   ├── helpers.py
│   └── security_mixins.py
└── management/                 # Test management commands
    └── commands/
        ├── run_all_tests.py
        ├── generate_test_data.py
        ├── test_coverage.py
        ├── performance_test.py
        └── security_test.py
```

## Quick Start

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

### Test Configuration

The test configuration is located in `tutor_platform/test_settings.py` and includes:

- Test database configuration
- Email backend for testing
- Debug settings for testing
- Test-specific middleware
- Mocked external services

## Test Categories

### Unit Tests

Unit tests focus on testing individual components in isolation:

- **Model Tests**: Test model methods, properties, validation, and relationships
- **View Tests**: Test view logic, permissions, and responses
- **Form Tests**: Test form validation, cleaning, and processing
- **Utility Tests**: Test utility functions and helpers

### Integration Tests

Integration tests test interactions between components:

- **User Workflows**: Test complete user journeys
- **API Integration**: Test API endpoints with real data
- **Database Integration**: Test database operations

### API Tests

API tests specifically focus on API functionality:

- **Endpoint Tests**: Test all API endpoints
- **Authentication Tests**: Test API authentication
- **Permission Tests**: Test API permissions
- **Validation Tests**: Test API data validation

### Performance Tests

Performance tests ensure the application performs well:

- **Database Performance**: Test query efficiency
- **API Performance**: Test response times
- **Load Tests**: Test performance under load
- **Memory Tests**: Test memory usage

### Security Tests

Security tests ensure the application is secure:

- **SQL Injection**: Test SQL injection prevention
- **XSS Protection**: Test XSS protection
- **CSRF Protection**: Test CSRF protection
- **Authentication**: Test authentication security
- **Authorization**: Test authorization security

### Frontend Tests

Frontend tests ensure the user interface works correctly:

- **JavaScript Tests**: Test JavaScript functionality
- **Browser Tests**: Test browser interactions
- **Mobile Tests**: Test mobile compatibility
- **Accessibility Tests**: Test accessibility compliance

### Payment Tests

Payment tests ensure payment processing works correctly:

- **PayPal Integration**: Test PayPal integration
- **Escrow Tests**: Test escrow functionality
- **Payment Processing**: Test payment processing
- **Refund Tests**: Test refund handling

### Email Tests

Email tests ensure email functionality works correctly:

- **Email Delivery**: Test email sending
- **Email Templates**: Test email templates
- **Notification Emails**: Test notification emails
- **Masked Emails**: Test masked email functionality

## Test Data Management

### Factories

Test factories are defined in `tests/factories.py` and use the factory-boy library to generate test data:

```python
# Example usage
from tests.factories import UserFactory, TutorProfileFactory

# Create a user
user = UserFactory()

# Create a tutor profile
tutor = TutorProfileFactory(user=user)
```

### Fixtures

Test fixtures are defined in `tests/fixtures/test_fixtures.py` and provide functions to create specific test scenarios:

```python
# Example usage
from tests.fixtures import create_test_users, create_test_requirements

# Create test users
users = create_test_users(count=10)

# Create test requirements
requirements = create_test_requirements(count=20)
```

## Test Utilities

### Helpers

Test helpers are defined in `tests/utils/helpers.py` and provide common testing functionality:

```python
# Example usage
from tests.utils.helpers import TestCaseWithTestData, APITestCaseWithAuth

class MyTestCase(TestCaseWithTestData):
    def test_something(self):
        user = self.create_user()
        # Test implementation
```

### Security Mixins

Security mixins are defined in `tests/utils/security_mixins.py` and provide security testing utilities:

```python
# Example usage
from tests.utils.security_mixins import SecurityTestMixin

class MySecurityTest(SecurityTestMixin, TestCase):
    def test_sql_injection(self):
        self.assert_no_sql_injection("'; DROP TABLE users; --")
```

## Test Management Commands

### run_all_tests

Runs all tests with coverage reporting:

```bash
python manage.py run_all_tests
```

### generate_test_data

Generates test data for testing:

```bash
python manage.py generate_test_data --users=50 --requirements=100
```

### test_coverage

Checks test coverage:

```bash
python manage.py test_coverage
```

### performance_test

Runs performance tests:

```bash
python manage.py performance_test
```

### security_test

Runs security tests:

```bash
python manage.py security_test
```

## Continuous Integration

The test suite is integrated with GitHub Actions and runs automatically on:

- Push to main branch
- Pull requests
- Scheduled runs

The CI/CD workflows are defined in `.github/workflows/`:

- `test.yml`: Main test workflow
- `coverage.yml`: Coverage reporting
- `performance.yml`: Performance testing
- `security.yml`: Security testing
- `frontend.yml`: Frontend testing

## Test Coverage

We aim for high test coverage across all layers of the application:

- **Overall Coverage**: 90%+
- **Model Coverage**: 95%+
- **View Coverage**: 90%+
- **Utility Coverage**: 95%+

Coverage reports are generated in HTML format and can be viewed in `htmlcov/index.html`.

## Best Practices

### Writing Tests

1. **Use descriptive test names**: `test_user_creation_with_valid_email`
2. **Follow the AAA pattern**: Arrange, Act, Assert
3. **Test one thing at a time**: Keep tests focused
4. **Use factories for test data**: Avoid hardcoded test data
5. **Mock external services**: Don't depend on external services

### Test Organization

1. **Group related tests**: Use test classes to group related tests
2. **Use setUp and tearDown**: Set up and clean up test data
3. **Keep tests independent**: Tests should not depend on each other
4. **Use appropriate test categories**: Unit, integration, API, etc.

### Performance

1. **Keep tests fast**: Use efficient test data setup
2. **Use appropriate test databases**: SQLite for unit tests, PostgreSQL for integration
3. **Avoid unnecessary database queries**: Use select_related and prefetch_related
4. **Clean up test data**: Use tearDown to clean up test data

## Troubleshooting

### Common Issues

1. **Test database issues**: Reset the test database
2. **Flaky tests**: Add retry logic or fix race conditions
3. **Slow tests**: Optimize test data setup and queries
4. **Import issues**: Check Python path and Django settings

### Debugging

1. **Use pdb**: Add `import pdb; pdb.set_trace()` to debug tests
2. **Enable debug toolbar**: Add to test settings for debugging
3. **Print queries**: Use `connection.queries` to see database queries
4. **Use verbose output**: Run tests with `-v` flag for more information

## Documentation

For more detailed information about testing:

- [Test Strategy](../docs/TEST_STRATEGY.md): Overall testing strategy
- [Test Cases](../docs/TEST_CASES.md): Detailed test case documentation
- [Testing Guidelines](../docs/TESTING_GUIDELINES.md): Guidelines for contributors
- [Bug Report Template](../docs/BUG_REPORT_TEMPLATE.md): Template for reporting bugs

## Contributing

When contributing to the test suite:

1. Write tests for new functionality
2. Maintain or improve test coverage
3. Follow the testing guidelines
4. Run the full test suite before submitting
5. Update documentation as needed

## Support

For questions or issues with the test suite:

1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information
4. Ask for help in project discussions