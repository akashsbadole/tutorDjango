# Bug Report Template

## Description

A clear and concise description of what the bug is.

## Steps to Reproduce

Please provide detailed steps to reproduce the issue:

1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

## Expected Behavior

A clear and concise description of what you expected to happen.

## Actual Behavior

A clear and concise description of what actually happened.

## Screenshots

If applicable, add screenshots to help explain your problem.

## Environment

- **Operating System**: [e.g., Windows 10, macOS 11.0, Ubuntu 20.04]
- **Browser**: [e.g., Chrome 91.0, Firefox 89.0, Safari 14.0]
- **Python Version**: [e.g., Python 3.9.5]
- **Django Version**: [e.g., Django 4.0.0]
- **Node.js Version**: [e.g., Node.js 16.0.0]

## Test Coverage

- [ ] I have verified that the issue is not covered by existing tests
- [ ] I have written a failing test that reproduces the issue
- [ ] I have included the test in this bug report

## Additional Context

Add any other context about the problem here.

## Possible Solution

If you have a possible solution, please describe it here.

## Priority

- [ ] Low
- [ ] Medium
- [ ] High
- [ ] Critical

## Assignee

Who should be assigned to this issue?

## Labels

Add relevant labels to this issue:
- [ ] bug
- [ ] security
- [ ] performance
- [ ] ui/ux
- [ ] api
- [ ] database
- [ ] testing

## Checklist

- [ ] I have searched for existing issues that match this one
- [ ] I have checked the latest version of the software
- [ ] I have provided enough information to reproduce the issue
- [ ] I have included relevant error messages or logs
- [ ] I have followed the contribution guidelines

## Test Case Example

If you have written a test that reproduces the issue, please include it here:

```python
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class BugReproductionTest(TestCase):
    """Test case to reproduce the bug."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_bug_reproduction(self):
        """Test that reproduces the bug."""
        # Steps to reproduce the bug
        # This test should fail with the current code
        pass
```

## Error Messages and Logs

Please include any relevant error messages, stack traces, or logs:

```
Paste error messages or logs here
```

## Related Issues

List any related issues or pull requests:

- Related to #123
- Depends on #456

## Additional Information

Add any other information that might be helpful in resolving this issue.