# Messaging Models Design

## 1. Masked Email Communication Models

### MaskedEmail
- Core model for privacy-focused email communication
- Fields:
  - id: BigAutoField (primary key)
  - award: ForeignKey(Award, related_name='masked_emails')
  - student: ForeignKey(User, related_name='masked_emails_sent')
  - tutor: ForeignKey(User, related_name='masked_emails_received')
  - masked_address: EmailField (unique=True) - Generated unique email
  - student_real_email: EmailField()
  - tutor_real_email: EmailField()
  - is_active: BooleanField (default=True)
  - expires_at: DateTimeField() - When the masked email expires
  - created_at: DateTimeField (auto_now_add)
  - last_used_at: DateTimeField (null=True, blank=True)
  - usage_count: PositiveIntegerField (default=0)

- Methods:
  - is_expired() - Check if masked email has expired
  - generate_masked_address() - Generate unique masked email
  - increment_usage() - Increment usage counter and update last_used_at

### EmailLog
- Log all emails sent through masked addresses
- Fields:
  - id: BigAutoField (primary key)
  - masked_email: ForeignKey(MaskedEmail, related_name='emails')
  - from_address: EmailField() - Original sender
  - to_address: EmailField() - Original recipient (masked)
  - subject: CharField (max_length=255)
  - body: TextField()
  - direction: CharField (choices: STUDENT_TO_TUTOR, TUTOR_TO_STUDENT)
  - message_id: CharField (max_length=255, unique=True) - Unique email ID
  - in_reply_to: CharField (max_length=255, null=True, blank=True) - Thread tracking
  - attachments_count: PositiveIntegerField (default=0)
  - size_bytes: PositiveIntegerField (default=0)
  - is_processed: BooleanField (default=False)
  - processing_error: TextField (blank=True, null=True)
  - created_at: DateTimeField (auto_now_add)
  - processed_at: DateTimeField (null=True, blank=True)

- Methods:
  - get_thread_id() - Extract thread ID for email threading
  - has_attachments() - Check if email has attachments

### EmailAttachment
- Store attachments for emails sent through masked addresses
- Fields:
  - id: BigAutoField (primary key)
  - email_log: ForeignKey(EmailLog, related_name='attachments')
  - filename: CharField (max_length=255)
  - file_path: CharField (max_length=500) - Path to stored file
  - file_size: PositiveIntegerField()
  - content_type: CharField (max_length=100)
  - is_scanned: BooleanField (default=False) - Security scan status
  - scan_result: CharField (max_length=50, blank=True, null=True)
  - created_at: DateTimeField (auto_now_add)

## 2. Platform Messaging Models

### Conversation
- Platform-based messaging between users
- Fields:
  - id: BigAutoField (primary key)
  - award: ForeignKey(Award, related_name='conversations', null=True, blank=True)
  - proposal: ForeignKey(Proposal, related_name='conversations', null=True, blank=True)
  - participant1: ForeignKey(User, related_name='conversations_started')
  - participant2: ForeignKey(User, related_name='conversations_joined')
  - subject: CharField (max_length=200, blank=True, null=True)
  - is_active: BooleanField (default=True)
  - last_message_at: DateTimeField (null=True, blank=True)
  - participant1_last_read: DateTimeField (null=True, blank=True)
  - participant2_last_read: DateTimeField (null=True, blank=True)
  - participant1_deleted: BooleanField (default=False)
  - participant2_deleted: BooleanField (default=False)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - get_other_participant(user) - Return the other participant in conversation
  - get_unread_count(user) - Count unread messages for user
  - mark_as_read(user) - Mark conversation as read for user
  - can_participant_access(user) - Check if user can access conversation

### Message
- Individual messages in conversations
- Fields:
  - id: BigAutoField (primary key)
  - conversation: ForeignKey(Conversation, related_name='messages')
  - sender: ForeignKey(User, related_name='sent_messages')
  - content: TextField()
  - message_type: CharField (choices: TEXT, FILE, SYSTEM, NOTIFICATION, default=TEXT)
  - is_edited: BooleanField (default=False)
  - edited_at: DateTimeField (null=True, blank=True)
  - is_deleted: BooleanField (default=False)
  - deleted_at: DateTimeField (null=True, blank=True)
  - is_read: BooleanField (default=False)
  - read_at: DateTimeField (null=True, blank=True)
  - parent_message: ForeignKey('self', null=True, blank=True, related_name='replies')
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - can_edit() - Check if message can be edited
  - can_delete() - Check if message can be deleted
  - get_thread() - Get message thread (replies)

### MessageAttachment
- Attachments for platform messages
- Fields:
  - id: BigAutoField (primary key)
  - message: ForeignKey(Message, related_name='attachments')
  - file: FileField (upload_to='message_attachments/')
  - filename: CharField (max_length=255)
  - file_size: PositiveIntegerField()
  - content_type: CharField (max_length=100)
  - thumbnail: ImageField (upload_to='message_thumbnails/', null=True, blank=True)
  - is_scanned: BooleanField (default=False)
  - scan_result: CharField (max_length=50, blank=True, null=True)
  - created_at: DateTimeField (auto_now_add)

## 3. File Sharing Models

### SharedFile
- General file sharing between users
- Fields:
  - id: BigAutoField (primary key)
  - uploaded_by: ForeignKey(User, related_name='shared_files')
  - shared_with: ForeignKey(User, related_name='received_files')
  - conversation: ForeignKey(Conversation, related_name='shared_files', null=True, blank=True)
  - award: ForeignKey(Award, related_name='shared_files', null=True, blank=True)
  - file: FileField (upload_to='shared_files/')
  - filename: CharField (max_length=255)
  - file_size: PositiveIntegerField()
  - content_type: CharField (max_length=100)
  - description: CharField (max_length=255, blank=True, null=True)
  - download_count: PositiveIntegerField (default=0)
  - is_public: BooleanField (default=False) - Can be downloaded by both parties
  - expires_at: DateTimeField (null=True, blank=True)
  - is_scanned: BooleanField (default=False)
  - scan_result: CharField (max_length=50, blank=True, null=True)
  - created_at: DateTimeField (auto_now_add)
  - last_downloaded_at: DateTimeField (null=True, blank=True)

- Methods:
  - is_expired() - Check if file has expired
  - increment_download() - Increment download counter
  - can_access(user) - Check if user can access file

## 4. Online Class Models

### OnlineClass
- Store online class URLs and details
- Fields:
  - id: BigAutoField (primary key)
  - session: ForeignKey(Session, related_name='online_classes')
  - host: ForeignKey(User, related_name='hosted_classes')
  - title: CharField (max_length=200)
  - description: TextField (blank=True, null=True)
  - meeting_url: URLField()
  - meeting_id: CharField (max_length=100, blank=True, null=True)
  - password: CharField (max_length=50, blank=True, null=True)
  - platform: CharField (choices: ZOOM, GOOGLE_MEET, SKYPE, TEAMS, CUSTOM, default=CUSTOM)
  - scheduled_start: DateTimeField()
  - scheduled_end: DateTimeField()
  - actual_start: DateTimeField (null=True, blank=True)
  - actual_end: DateTimeField (null=True, blank=True)
  - max_participants: PositiveIntegerField (default=2)
  - is_recording: BooleanField (default=False)
  - recording_url: URLField (blank=True, null=True)
  - status: CharField (choices: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED, default=SCHEDULED)
  - join_url_participant: URLField (blank=True, null=True)
  - join_url_host: URLField (blank=True, null=True)
  - settings: JSONField (default=dict) - Platform-specific settings
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - is_joinable() - Check if class can be joined
  - get_duration() - Calculate class duration
  - generate_join_urls() - Generate join URLs for participants

### ClassParticipant
- Track participants in online classes
- Fields:
  - id: BigAutoField (primary key)
  - online_class: ForeignKey(OnlineClass, related_name='participants')
  - user: ForeignKey(User, related_name='class_participations')
  - role: CharField (choices: HOST, PARTICIPANT, OBSERVER, default=PARTICIPANT)
  - joined_at: DateTimeField (null=True, blank=True)
  - left_at: DateTimeField (null=True, blank=True)
  - duration_minutes: PositiveIntegerField (default=0)
  - is_active: BooleanField (default=False)
  - ip_address: GenericIPAddressField (null=True, blank=True)
  - user_agent: TextField (blank=True, null=True)
  - created_at: DateTimeField (auto_now_add)

- Methods:
  - calculate_duration() - Calculate participation duration

## 5. Communication Preferences and Settings

### CommunicationPreference
- User preferences for communication
- Fields:
  - id: BigAutoField (primary key)
  - user: OneToOneField(User)
  - allow_platform_messages: BooleanField (default=True)
  - allow_email_communication: BooleanField (default=True)
  - allow_file_sharing: BooleanField (default=True)
  - allow_online_classes: BooleanField (default=True)
  - email_notification_frequency: CharField (choices: IMMEDIATE, HOURLY, DAILY, NEVER, default=IMMEDIATE)
  - auto_reply_message: TextField (blank=True, null=True)
  - is_auto_reply_enabled: BooleanField (default=False)
  - working_hours_start: TimeField (null=True, blank=True)
  - working_hours_end: TimeField (null=True, blank=True)
  - timezone: CharField (default='UTC')
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - is_within_working_hours() - Check if current time is within working hours

### BlockedUser
- Users blocked from communication
- Fields:
  - id: BigAutoField (primary key)
  - blocker: ForeignKey(User, related_name='blocked_users')
  - blocked: ForeignKey(User, related_name='blocked_by')
  - reason: CharField (max_length=255, blank=True, null=True)
  - is_permanent: BooleanField (default=True)
  - expires_at: DateTimeField (null=True, blank=True)
  - created_at: DateTimeField (auto_now_add)

- Unique constraint: (blocker, blocked)

## 6. Database Indexes for Performance

- MaskedEmail:
  - Index on award_id
  - Index on student_id
  - Index on tutor_id
  - Index on masked_address
  - Index on is_active
  - Index on expires_at
  - Composite index on (is_active, expires_at)

- EmailLog:
  - Index on masked_email_id
  - Index on from_address
  - Index on to_address
  - Index on direction
  - Index on created_at
  - Index on message_id
  - Composite index on (masked_email_id, created_at)

- Conversation:
  - Index on award_id
  - Index on proposal_id
  - Index on participant1_id
  - Index on participant2_id
  - Index on is_active
  - Index on last_message_at
  - Composite index on (participant1_id, is_active)
  - Composite index on (participant2_id, is_active)

- Message:
  - Index on conversation_id
  - Index on sender_id
  - Index on created_at
  - Index on is_read
  - Index on parent_message_id
  - Composite index on (conversation_id, created_at)

- OnlineClass:
  - Index on session_id
  - Index on host_id
  - Index on scheduled_start
  - Index on status
  - Composite index on (scheduled_start, status)

- ClassParticipant:
  - Index on online_class_id
  - Index on user_id
  - Index on joined_at
  - Composite index on (online_class_id, user_id)

## 7. Constraints and Validation Rules

- MaskedEmail:
  - Masked address must be unique
  - Expires at must be in the future
  - Unique constraint on (award, student, tutor)

- EmailLog:
  - Message ID must be unique
  - Direction must be valid choice
  - Size bytes must be non-negative

- Conversation:
  - Participant1 and participant2 must be different users
  - Unique constraint on (participant1, participant2) with condition to prevent duplicates

- Message:
  - Sender must be one of the conversation participants
  - Parent message must belong to same conversation
  - Content cannot be empty for text messages

- OnlineClass:
  - Scheduled end must be after scheduled start
  - Actual end must be after actual start
  - Max participants must be positive

- ClassParticipant:
  - User must be participant in the online class
  - Left at must be after joined at
  - Unique constraint on (online_class, user)

- BlockedUser:
  - Blocker and blocked must be different users
  - Unique constraint on (blocker, blocked)
  - Expires at must be in the future if not permanent