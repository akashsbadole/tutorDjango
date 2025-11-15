# Notifications Models Design

## 1. Core Notification Models

### NotificationType
- Define types of notifications
- Fields:
  - id: BigAutoField (primary key)
  - name: CharField (max_length=100, unique=True)
  - code: CharField (max_length=50, unique=True) - Machine-readable code
  - category: CharField (choices: REQUIREMENT, PROPOSAL, AWARD, PAYMENT, MESSAGE, SYSTEM, ADMIN)
  - description: TextField(blank=True, null=True)
  - default_template: TextField() - Default message template
  - email_template: TextField(blank=True, null=True) - Email-specific template
  - sms_template: TextField(blank=True, null=True) - SMS-specific template
  - push_template: TextField(blank=True, null=True) - Push notification template
  - is_active: BooleanField (default=True)
  - is_system: BooleanField (default=False) - System-generated notifications
  - priority: CharField (choices: LOW, NORMAL, HIGH, URGENT, default=NORMAL)
  - default_expiration_hours: PositiveIntegerField (default=720) - 30 days default
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - get_template(channel) - Get template for specific channel
  - render_template(context) - Render template with context

### Notification
- Main notification model
- Fields:
  - id: BigAutoField (primary key)
  - recipient: ForeignKey(User, related_name='notifications')
  - sender: ForeignKey(User, null=True, blank=True, related_name='sent_notifications')
  - notification_type: ForeignKey(NotificationType, related_name='notifications')
  - title: CharField (max_length=255)
  - message: TextField()
  - action_url: URLField(blank=True, null=True) - URL to redirect when clicked
  - action_text: CharField (max_length=100, blank=True, null=True) - Text for action button
  - related_object_type: CharField (max_length=50, blank=True, null=True) - Type of related object
  - related_object_id: PositiveIntegerField(null=True, blank=True) - ID of related object
  - is_read: BooleanField (default=False)
  - is_email_sent: BooleanField (default=False)
  - is_sms_sent: BooleanField (default=False)
  - is_push_sent: BooleanField (default=False)
  - read_at: DateTimeField (null=True, blank=True)
  - email_sent_at: DateTimeField (null=True, blank=True)
  - sms_sent_at: DateTimeField (null=True, blank=True)
  - push_sent_at: DateTimeField (null=True, blank=True)
  - expires_at: DateTimeField (null=True, blank=True)
  - metadata: JSONField (default=dict) - Additional notification data
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - mark_as_read() - Mark notification as read
  - send_email() - Send email notification
  - send_sms() - Send SMS notification
  - send_push() - Send push notification
  - is_expired() - Check if notification is expired
  - get_related_object() - Get related object using generic relation

## 2. Notification Preferences and Settings

### NotificationPreference
- User notification preferences
- Fields:
  - id: BigAutoField (primary key)
  - user: OneToOneField(User)
  - email_notifications: BooleanField (default=True)
  - sms_notifications: BooleanField (default=False)
  - push_notifications: BooleanField (default=True)
  - in_app_notifications: BooleanField (default=True)
  - marketing_emails: BooleanField (default=False)
  - digest_frequency: CharField (choices: IMMEDIATE, HOURLY, DAILY, WEEKLY, NEVER, default=IMMEDIATE)
  - quiet_hours_start: TimeField(null=True, blank=True)
  - quiet_hours_end: TimeField(null=True, blank=True)
  - timezone: CharField (default='UTC')
  - minimum_priority: CharField (choices: LOW, NORMAL, HIGH, URGENT, default=LOW)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - is_within_quiet_hours() - Check if current time is within quiet hours
  - should_send_notification(notification_type, priority) - Check if notification should be sent

### NotificationTypePreference
- Per-type notification preferences
- Fields:
  - id: BigAutoField (primary key)
  - user: ForeignKey(User, related_name='notification_type_preferences')
  - notification_type: ForeignKey(NotificationType, related_name='user_preferences')
  - is_enabled: BooleanField (default=True)
  - email_enabled: BooleanField (default=True)
  - sms_enabled: BooleanField (default=False)
  - push_enabled: BooleanField (default=True)
  - in_app_enabled: BooleanField (default=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Unique constraint: (user, notification_type)

## 3. Notification Templates and Localization

### NotificationTemplate
- Customizable notification templates
- Fields:
  - id: BigAutoField (primary key)
  - notification_type: ForeignKey(NotificationType, related_name='templates')
  - language: CharField (max_length=10, default='en')
  - channel: CharField (choices: IN_APP, EMAIL, SMS, PUSH, default=IN_APP)
  - subject_template: CharField (max_length=255, blank=True, null=True) - For emails
  - body_template: TextField()
  - variables: JSONField (default=dict) - Available template variables
  - is_active: BooleanField (default=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Unique constraint: (notification_type, language, channel)
- Methods:
  - render(context) - Render template with context

## 4. Notification Delivery and Tracking

### NotificationDelivery
- Track delivery status of notifications
- Fields:
  - id: BigAutoField (primary key)
  - notification: ForeignKey(Notification, related_name='deliveries')
  - channel: CharField (choices: IN_APP, EMAIL, SMS, PUSH)
  - status: CharField (choices: PENDING, SENT, DELIVERED, FAILED, BOUNCED, default=PENDING)
  - recipient_address: CharField (max_length=255) - Email/phone/push token
  - sent_at: DateTimeField (null=True, blank=True)
  - delivered_at: DateTimeField (null=True, blank=True)
  - failed_at: DateTimeField (null=True, blank=True)
  - failure_reason: TextField(blank=True, null=True)
  - delivery_provider: CharField (max_length=50, blank=True, null=True) - SendGrid, Twilio, etc.
  - provider_response: JSONField (default=dict) - Provider response data
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - mark_as_sent() - Mark delivery as sent
  - mark_as_delivered() - Mark delivery as delivered
  - mark_as_failed(reason) - Mark delivery as failed

### NotificationDigest
- Digest notifications for batch sending
- Fields:
  - id: BigAutoField (primary key)
  - user: ForeignKey(User, related_name='notification_digests')
  - frequency: CharField (choices: HOURLY, DAILY, WEEKLY)
  - notifications: ManyToManyField(Notification, related_name='digests')
  - subject: CharField (max_length=255)
  - content: TextField()
  - is_sent: BooleanField (default=False)
  - sent_at: DateTimeField (null=True, blank=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - add_notification(notification) - Add notification to digest
  - generate_content() - Generate digest content
  - send_digest() - Send digest email

## 5. Push Notification Models

### PushDevice
- User push notification devices
- Fields:
  - id: BigAutoField (primary key)
  - user: ForeignKey(User, related_name='push_devices')
  - device_token: CharField (max_length=255)
  - device_type: CharField (choices: IOS, ANDROID, WEB)
  - device_id: CharField (max_length=255, blank=True, null=True) - Unique device identifier
  - app_version: CharField (max_length=50, blank=True, null=True)
  - os_version: CharField (max_length=50, blank=True, null=True)
  - is_active: BooleanField (default=True)
  - last_used_at: DateTimeField (null=True, blank=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Unique constraint: (user, device_token)

### PushMessage
- Push notification messages
- Fields:
  - id: BigAutoField (primary key)
  - notification: ForeignKey(Notification, related_name='push_messages')
  - device: ForeignKey(PushDevice, related_name='messages')
  - title: CharField (max_length=255)
  - body: TextField()
  - icon: URLField(blank=True, null=True)
  - image: URLField(blank=True, null=True)
  - sound: CharField (max_length=100, default='default')
  - badge: PositiveIntegerField(null=True, blank=True)
  - data: JSONField (default=dict) - Additional data payload
  - status: CharField (choices: PENDING, SENT, DELIVERED, FAILED, default=PENDING)
  - sent_at: DateTimeField (null=True, blank=True)
  - delivered_at: DateTimeField (null=True, blank=True)
  - failed_at: DateTimeField (null=True, blank=True)
  - failure_reason: TextField(blank=True, null=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

## 6. System and Admin Notifications

### SystemNotification
- System-wide notifications
- Fields:
  - id: BigAutoField (primary key)
  - title: CharField (max_length=255)
  - message: TextField()
  - notification_type: CharField (choices: MAINTENANCE, ANNOUNCEMENT, WARNING, INFO)
  - priority: CharField (choices: LOW, NORMAL, HIGH, URGENT, default=NORMAL)
  - is_active: BooleanField (default=True)
  - start_time: DateTimeField()
  - end_time: DateTimeField(null=True, blank=True)
  - target_audience: CharField (choices: ALL, STUDENTS, TUTORS, ADMINS, default=ALL)
  - action_url: URLField(blank=True, null=True)
  - action_text: CharField (max_length=100, blank=True, null=True)
  - is_dismissible: BooleanField (default=True)
  - created_by: ForeignKey(User, related_name='created_system_notifications')
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - is_currently_active() - Check if notification is currently active
  - should_show_to_user(user) - Check if notification should show to user

### SystemNotificationDismissal
- Track system notification dismissals
- Fields:
  - id: BigAutoField (primary key)
  - system_notification: ForeignKey(SystemNotification, related_name='dismissals')
  - user: ForeignKey(User, related_name='dismissed_system_notifications')
  - dismissed_at: DateTimeField (auto_now_add)

- Unique constraint: (system_notification, user)

## 7. Notification Analytics and Statistics

### NotificationAnalytics
- Daily notification statistics
- Fields:
  - id: BigAutoField (primary key)
  - date: DateField()
  - notification_type: ForeignKey(NotificationType, related_name='analytics')
  - total_sent: PositiveIntegerField(default=0)
  - email_sent: PositiveIntegerField(default=0)
  - sms_sent: PositiveIntegerField(default=0)
  - push_sent: PositiveIntegerField(default=0)
  - total_delivered: PositiveIntegerField(default=0)
  - email_delivered: PositiveIntegerField(default=0)
  - sms_delivered: PositiveIntegerField(default=0)
  - push_delivered: PositiveIntegerField(default=0)
  - total_read: PositiveIntegerField(default=0)
  - created_at: DateTimeField (auto_now_add)

- Unique constraint: (date, notification_type)

## 8. Database Indexes for Performance

- NotificationType:
  - Index on code
  - Index on category
  - Index on is_active
  - Index on priority

- Notification:
  - Index on recipient_id
  - Index on sender_id
  - Index on notification_type_id
  - Index on is_read
  - Index on created_at
  - Index on expires_at
  - Composite index on (recipient_id, is_read)
  - Composite index on (recipient_id, created_at)
  - Composite index on (notification_type_id, created_at)

- NotificationPreference:
  - Index on user_id
  - Index on email_notifications
  - Index on sms_notifications
  - Index on push_notifications

- NotificationTypePreference:
  - Index on user_id
  - Index on notification_type_id
  - Index on is_enabled
  - Composite index on (user_id, notification_type_id)

- NotificationDelivery:
  - Index on notification_id
  - Index on channel
  - Index on status
  - Index on sent_at
  - Composite index on (notification_id, channel)
  - Composite index on (channel, status)

- PushDevice:
  - Index on user_id
  - Index on device_token
  - Index on device_type
  - Index on is_active
  - Composite index on (user_id, is_active)

- PushMessage:
  - Index on notification_id
  - Index on device_id
  - Index on status
  - Index on created_at
  - Composite index on (notification_id, device_id)

- SystemNotification:
  - Index on is_active
  - Index on start_time
  - Index on end_time
  - Index on target_audience
  - Index on priority

- NotificationAnalytics:
  - Index on date
  - Index on notification_type_id
  - Composite index on (date, notification_type_id)

## 9. Constraints and Validation Rules

- NotificationType:
  - Code must be unique
  - Name must be unique
  - Priority must be valid choice

- Notification:
  - Recipient must be specified
  - Title and message cannot be empty
  - Expires at must be in the future if specified

- NotificationPreference:
  - Quiet hours end must be after quiet hours start
  - Digest frequency must be valid choice
  - Minimum priority must be valid choice

- NotificationTypePreference:
  - Unique constraint on (user, notification_type)
  - All enabled flags must be valid booleans

- NotificationTemplate:
  - Unique constraint on (notification_type, language, channel)
  - Body template cannot be empty

- NotificationDelivery:
  - Status must be valid choice
  - Channel must be valid choice
  - Recipient address cannot be empty

- PushDevice:
  - Device token must be unique per user
  - Device type must be valid choice
  - Unique constraint on (user, device_token)

- SystemNotification:
  - Title and message cannot be empty
  - End time must be after start time
  - Target audience must be valid choice

- SystemNotificationDismissal:
  - Unique constraint on (system_notification, user)

- NotificationAnalytics:
  - Unique constraint on (date, notification_type)
  - All count fields must be non-negative