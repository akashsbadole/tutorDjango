# Notifications App

This app provides a comprehensive notification system for the DjangoTutor platform, supporting in-app notifications, email notifications, and push notifications.

## Features

### Core Models

1. **Notification**
   - Main notification model with UUID primary key
   - Support for different notification types (MESSAGE, PROPOSAL, AWARD, SESSION, REVIEW, PAYMENT, SYSTEM)
   - Priority levels (LOW, MEDIUM, HIGH, URGENT)
   - Generic foreign key to link with any model
   - Email and push notification tracking
   - Action URL for direct navigation

2. **NotificationPreference**
   - User preferences for different notification types
   - Separate settings for email, push, and in-app notifications
   - Email frequency settings (immediate, hourly, daily, weekly, never)
   - Quiet hours configuration
   - Auto-delete settings for old notifications

3. **NotificationTemplate**
   - Template system for email notifications
   - Support for subject, body, and HTML templates
   - Variable placeholders for dynamic content
   - Default template per notification type

4. **EmailQueue**
   - Queue system for reliable email delivery
   - Retry mechanism with exponential backoff
   - Error logging and tracking
   - Status tracking (pending, processing, sent, failed, cancelled)

### Views

1. **NotificationListView**
   - List all notifications for current user
   - Filtering by read status, type, and priority
   - Pagination support

2. **NotificationDetailView**
   - View notification details
   - Auto-mark as read when viewed

3. **NotificationPreferenceView**
   - Update notification preferences
   - Form-based preference management

4. **AJAX Endpoints**
   - Mark notifications as read/unread
   - Delete notifications
   - Get notification count
   - Get recent notifications

### Utility Functions

The `utils.py` module provides helper functions for creating different types of notifications:

- `create_notification()` - Generic notification creation
- `create_system_notification()` - System notifications
- `create_message_notification()` - Message notifications
- `create_proposal_notification()` - Proposal notifications
- `create_award_notification()` - Award notifications
- `create_session_notification()` - Session notifications
- `create_review_notification()` - Review notifications
- `create_payment_notification()` - Payment notifications

### Management Commands

1. **process_email_queue**
   - Process pending emails in queue
   - Retry failed emails
   - Clean up old sent emails
   - Usage: `python manage.py process_email_queue --limit=50 --retry-failed`

## Integration with Other Apps

### Accounts App
- Automatically creates notification preferences for new users
- Links to User model for recipients and senders

### Requirements App
- Links to Requirement, Proposal, Award, Session, and Review models
- Creates notifications for requirement events

### Messaging App
- Links to Message and Conversation models
- Creates notifications for new messages

## Usage Examples

### Creating a Notification

```python
from notifications.utils import create_proposal_notification

# Create a proposal notification
create_proposal_notification(
    recipient=student_user,
    proposal=proposal_obj,
    action_url=reverse('requirements:proposal_detail', kwargs={'pk': proposal_obj.id}),
    send_email=True
)
```

### Getting Notification Count

```python
from notifications.utils import get_unread_count

# Get unread count for user
count = get_unread_count(request.user)
```

### Marking All as Read

```python
from notifications.utils import mark_all_as_read

# Mark all notifications as read for user
mark_all_as_read(request.user)
```

## Email Templates

Email templates support the following variables:

- `title` - Notification title
- `content` - Notification content
- `recipient_name` - Full name of recipient
- `recipient_username` - Username of recipient
- `sender_name` - Full name of sender
- `sender_username` - Username of sender
- `notification_type` - Type of notification
- `priority` - Priority level
- `created_at` - Creation timestamp
- `action_url` - Action URL
- `action_text` - Action button text
- `related_object` - Related object (if any)
- `related_object_type` - Type of related object

Example template:

```
Subject: {{ title }}

Hello {{ recipient_name }},

{{ content }}

{% if action_url %}
<a href="{{ action_url }}">{{ action_text }}</a>
{% endif %}

Thank you,
The DjangoTutor Team
```

## Settings

Add the following to your Django settings:

```python
# Default from email for notifications
DEFAULT_FROM_EMAIL = 'notifications@djangotutor.com'

# Email queue processing schedule
EMAIL_QUEUE_BATCH_SIZE = 50
EMAIL_QUEUE_RETRY_DELAY = 3600  # 1 hour
```

## URLs

The following URL patterns are available:

- `/notifications/` - List notifications
- `/notifications/<uuid:pk>/` - Notification detail
- `/notifications/preferences/` - Notification preferences
- `/notifications/<uuid:pk>/mark-read/` - Mark as read (AJAX)
- `/notifications/<uuid:pk>/mark-unread/` - Mark as unread (AJAX)
- `/notifications/<uuid:pk>/delete/` - Delete notification (AJAX)
- `/notifications/mark-all-read/` - Mark all as read (AJAX)
- `/notifications/count/` - Get unread count (AJAX)
- `/notifications/recent/` - Get recent notifications (AJAX)

## Frontend Integration

The notification system provides JSON endpoints for AJAX integration:

```javascript
// Get notification count
fetch('/notifications/count/')
  .then(response => response.json())
  .then(data => {
    // Update notification badge with data.count
  });

// Get recent notifications
fetch('/notifications/recent/')
  .then(response => response.json())
  .then(data => {
    // Render data.notifications in dropdown
  });

// Mark notification as read
fetch(`/notifications/${notificationId}/mark-read/`, {
  method: 'POST',
  headers: {
    'X-CSRFToken': getCookie('csrftoken')
  }
})
.then(response => response.json())
.then(data => {
  // Update UI
});
```

## Scheduled Tasks

Set up the following scheduled tasks (using Celery or cron):

1. Process email queue every 5 minutes:
   ```
   */5 * * * * python manage.py process_email_queue --limit=50
   ```

2. Clean up expired notifications daily:
   ```
   0 2 * * * python manage.py cleanup_expired_notifications
   ```

3. Clean up old read notifications weekly:
   ```
   0 3 * * 0 python manage.py cleanup_old_read_notifications