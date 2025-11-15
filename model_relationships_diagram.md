# Django Tutoring Platform - Model Relationships Diagram

## 1. Overview

This document provides a comprehensive visualization of the model relationships in the Django tutoring platform database architecture. The diagram shows how all models across the different apps are interconnected.

## 2. Mermaid Diagram

```mermaid
erDiagram
    %% Accounts App Models
    User {
        BigAutoField id PK
        CharField username UK
        EmailField email UK
        CharField first_name
        CharField last_name
        BooleanField is_staff
        BooleanField is_active
        DateTimeField date_joined
        DateTimeField last_login
        CharField user_type
        BooleanField is_online
        BooleanField is_verified
        CharField phone_number
        CharField timezone
        ImageField profile_picture
        DateTimeField created_at
        DateTimeField updated_at
    }

    StudentProfile {
        BigAutoField id PK
        ForeignKey user FK
        CharField educational_status
        CharField institution
        CharField grade_level
        CharField major_field
        TextField learning_goals
        CharField preferred_learning_style
        TextField bio
        DateTimeField created_at
        DateTimeField updated_at
    }

    TutorProfile {
        BigAutoField id PK
        ForeignKey user FK
        CharField professional_title
        PositiveIntegerField experience_years
        TextField education
        TextField bio
        DecimalField hourly_rate_min
        DecimalField hourly_rate_max
        CharField availability_status
        PositiveIntegerField response_time_hours
        CharField languages
        TextField teaching_experience
        PositiveIntegerField profile_completion_score
        BooleanField is_featured
        DateTimeField created_at
        DateTimeField updated_at
    }

    AdminProfile {
        BigAutoField id PK
        ForeignKey user FK
        CharField department
        JSONField permissions
        DateTimeField created_at
        DateTimeField updated_at
    }

    Subject {
        BigAutoField id PK
        CharField name UK
        SlugField slug UK
        ForeignKey parent FK
        TextField description
        CharField icon
        BooleanField is_active
        PositiveIntegerField order
        DateTimeField created_at
        DateTimeField updated_at
    }

    TutorSubject {
        BigAutoField id PK
        ForeignKey tutor FK
        ForeignKey subject FK
        CharField proficiency_level
        DecimalField hourly_rate
        BooleanField is_primary_subject
        PositiveIntegerField years_of_experience
        DateTimeField created_at
        DateTimeField updated_at
    }

    TutorVerification {
        BigAutoField id PK
        ForeignKey tutor FK
        CharField verification_type
        FileField document
        CharField document_number
        CharField issuing_authority
        DateField issue_date
        DateField expiry_date
        CharField status
        ForeignKey verified_by FK
        TextField verification_notes
        TextField admin_comments
        DateTimeField submitted_at
        DateTimeField reviewed_at
        DateTimeField expires_at
    }

    TutorRating {
        BigAutoField id PK
        ForeignKey tutor FK
        ForeignKey student FK
        ForeignKey requirement FK
        PositiveIntegerField rating
        TextField review
        BooleanField is_public
        DateTimeField created_at
        DateTimeField updated_at
    }

    UserPreferences {
        BigAutoField id PK
        ForeignKey user FK
        BooleanField email_notifications
        BooleanField sms_notifications
        BooleanField push_notifications
        BooleanField marketing_emails
        CharField language
        CharField timezone
        CharField currency
        DateTimeField created_at
        DateTimeField updated_at
    }

    %% Requirements App Models
    Requirement {
        BigAutoField id PK
        ForeignKey student FK
        CharField title
        SlugField slug UK
        TextField description
        ForeignKey subject FK
        CharField learning_level
        TextField specific_topics
        CharField budget_type
        DecimalField budget_min
        DecimalField budget_max
        CharField currency
        CharField urgency_level
        DateField deadline
        TextField preferred_schedule
        CharField timezone
        PositiveIntegerField session_duration
        PositiveIntegerField number_of_sessions
        CharField location_type
        CharField status
        CharField visibility
        BooleanField is_featured
        PositiveIntegerField view_count
        PositiveIntegerField proposal_count
        DateTimeField created_at
        DateTimeField updated_at
        DateTimeField published_at
        DateTimeField closed_at
    }

    RequirementAttachment {
        BigAutoField id PK
        ForeignKey requirement FK
        FileField file
        CharField filename
        PositiveIntegerField file_size
        CharField file_type
        CharField description
        BooleanField is_public
        DateTimeField uploaded_at
    }

    Proposal {
        BigAutoField id PK
        ForeignKey requirement FK
        ForeignKey tutor FK
        TextField cover_letter
        DecimalField proposed_rate
        CharField rate_type
        PositiveIntegerField estimated_hours
        DecimalField total_amount
        TextField approach
        TextField availability
        BooleanField can_start_immediately
        DateField proposed_start_date
        CharField status
        BooleanField is_shortlisted
        DateTimeField submitted_at
        DateTimeField reviewed_at
        DateTimeField accepted_at
        DateTimeField created_at
        DateTimeField updated_at
    }

    ProposalAttachment {
        BigAutoField id PK
        ForeignKey proposal FK
        FileField file
        CharField filename
        PositiveIntegerField file_size
        CharField file_type
        CharField description
        BooleanField is_public
        DateTimeField uploaded_at
    }

    Award {
        BigAutoField id PK
        ForeignKey requirement FK
        ForeignKey proposal FK
        ForeignKey student FK
        ForeignKey tutor FK
        DecimalField agreed_rate
        CharField rate_type
        DecimalField total_amount
        CharField currency
        DateField start_date
        DateField expected_end_date
        DateField actual_end_date
        TextField terms_and_conditions
        CharField status
        TextField cancellation_reason
        ForeignKey cancelled_by FK
        DateTimeField created_at
        DateTimeField updated_at
        DateTimeField activated_at
        DateTimeField completed_at
        DateTimeField cancelled_at
    }

    Milestone {
        BigAutoField id PK
        ForeignKey award FK
        CharField title
        TextField description
        DecimalField amount
        DateField due_date
        CharField status
        TextField completion_notes
        PositiveIntegerField order
        DateTimeField created_at
        DateTimeField updated_at
        DateTimeField completed_at
    }

    Session {
        BigAutoField id PK
        ForeignKey award FK
        CharField title
        TextField description
        DateTimeField scheduled_start
        DateTimeField scheduled_end
        DateTimeField actual_start
        DateTimeField actual_end
        PositiveIntegerField duration_minutes
        CharField location_type
        URLField meeting_url
        TextField meeting_address
        CharField status
        TextField cancellation_reason
        ForeignKey cancelled_by FK
        TextField tutor_notes
        TextField student_notes
        DateTimeField created_at
        DateTimeField updated_at
    }

    Review {
        BigAutoField id PK
        ForeignKey award FK
        ForeignKey reviewer FK
        ForeignKey reviewee FK
        PositiveIntegerField rating
        TextField comment
        PositiveIntegerField communication_rating
        PositiveIntegerField expertise_rating
        PositiveIntegerField punctuality_rating
        BooleanField would_recommend
        BooleanField is_public
        BooleanField is_verified
        DateTimeField created_at
        DateTimeField updated_at
    }

    SavedRequirement {
        BigAutoField id PK
        ForeignKey user FK
        ForeignKey requirement FK
        DateTimeField created_at
    }

    FavoriteTutor {
        BigAutoField id PK
        ForeignKey student FK
        ForeignKey tutor FK
        DateTimeField created_at
    }

    %% Messaging App Models
    MaskedEmail {
        BigAutoField id PK
        ForeignKey award FK
        ForeignKey student FK
        ForeignKey tutor FK
        EmailField masked_address UK
        EmailField student_real_email
        EmailField tutor_real_email
        BooleanField is_active
        DateTimeField expires_at
        DateTimeField created_at
        DateTimeField last_used_at
        PositiveIntegerField usage_count
    }

    EmailLog {
        BigAutoField id PK
        ForeignKey masked_email FK
        EmailField from_address
        EmailField to_address
        CharField subject
        TextField body
        CharField direction
        CharField message_id UK
        CharField in_reply_to
        PositiveIntegerField attachments_count
        PositiveIntegerField size_bytes
        BooleanField is_processed
        TextField processing_error
        DateTimeField created_at
        DateTimeField processed_at
    }

    EmailAttachment {
        BigAutoField id PK
        ForeignKey email_log FK
        CharField filename
        CharField file_path
        PositiveIntegerField file_size
        CharField content_type
        BooleanField is_scanned
        CharField scan_result
        DateTimeField created_at
    }

    Conversation {
        BigAutoField id PK
        ForeignKey award FK
        ForeignKey proposal FK
        ForeignKey participant1 FK
        ForeignKey participant2 FK
        CharField subject
        BooleanField is_active
        DateTimeField last_message_at
        DateTimeField participant1_last_read
        DateTimeField participant2_last_read
        BooleanField participant1_deleted
        BooleanField participant2_deleted
        DateTimeField created_at
        DateTimeField updated_at
    }

    Message {
        BigAutoField id PK
        ForeignKey conversation FK
        ForeignKey sender FK
        TextField content
        CharField message_type
        BooleanField is_edited
        DateTimeField edited_at
        BooleanField is_deleted
        DateTimeField deleted_at
        BooleanField is_read
        DateTimeField read_at
        ForeignKey parent_message FK
        DateTimeField created_at
        DateTimeField updated_at
    }

    MessageAttachment {
        BigAutoField id PK
        ForeignKey message FK
        FileField file
        CharField filename
        PositiveIntegerField file_size
        CharField content_type
        ImageField thumbnail
        BooleanField is_scanned
        CharField scan_result
        DateTimeField created_at
    }

    SharedFile {
        BigAutoField id PK
        ForeignKey uploaded_by FK
        ForeignKey shared_with FK
        ForeignKey conversation FK
        ForeignKey award FK
        FileField file
        CharField filename
        PositiveIntegerField file_size
        CharField content_type
        CharField description
        PositiveIntegerField download_count
        BooleanField is_public
        DateTimeField expires_at
        BooleanField is_scanned
        CharField scan_result
        DateTimeField created_at
        DateTimeField last_downloaded_at
    }

    OnlineClass {
        BigAutoField id PK
        ForeignKey session FK
        ForeignKey host FK
        CharField title
        TextField description
        URLField meeting_url
        CharField meeting_id
        CharField password
        CharField platform
        DateTimeField scheduled_start
        DateTimeField scheduled_end
        DateTimeField actual_start
        DateTimeField actual_end
        PositiveIntegerField max_participants
        BooleanField is_recording
        URLField recording_url
        CharField status
        URLField join_url_participant
        URLField join_url_host
        JSONField settings
        DateTimeField created_at
        DateTimeField updated_at
    }

    ClassParticipant {
        BigAutoField id PK
        ForeignKey online_class FK
        ForeignKey user FK
        CharField role
        DateTimeField joined_at
        DateTimeField left_at
        PositiveIntegerField duration_minutes
        BooleanField is_active
        GenericIPAddressField ip_address
        TextField user_agent
        DateTimeField created_at
    }

    CommunicationPreference {
        BigAutoField id PK
        ForeignKey user FK
        BooleanField allow_platform_messages
        BooleanField allow_email_communication
        BooleanField allow_file_sharing
        BooleanField allow_online_classes
        CharField email_notification_frequency
        TextField auto_reply_message
        BooleanField is_auto_reply_enabled
        TimeField working_hours_start
        TimeField working_hours_end
        CharField timezone
        DateTimeField created_at
        DateTimeField updated_at
    }

    BlockedUser {
        BigAutoField id PK
        ForeignKey blocker FK
        ForeignKey blocked FK
        CharField reason
        BooleanField is_permanent
        DateTimeField expires_at
        DateTimeField created_at
    }

    %% Payments App Models
    PaymentMethod {
        BigAutoField id PK
        ForeignKey user FK
        CharField method_type
        CharField provider
        CharField provider_method_id
        BooleanField is_default
        CharField card_last4
        CharField card_brand
        PositiveIntegerField card_exp_month
        PositiveIntegerField card_exp_year
        CharField bank_name
        CharField bank_account_last4
        EmailField paypal_email
        BooleanField is_verified
        BooleanField is_active
        JSONField metadata
        DateTimeField created_at
        DateTimeField updated_at
        DateTimeField expires_at
    }

    EscrowAccount {
        BigAutoField id PK
        ForeignKey user FK
        CharField account_type
        DecimalField balance
        DecimalField available_balance
        DecimalField pending_balance
        CharField currency
        BooleanField is_active
        DateTimeField created_at
        DateTimeField updated_at
    }

    EscrowTransaction {
        BigAutoField id PK
        ForeignKey escrow_account FK
        CharField transaction_type
        DecimalField amount
        DecimalField fee
        DecimalField net_amount
        CharField currency
        CharField reference_id
        CharField description
        CharField status
        ForeignKey payment_method FK
        ForeignKey related_award FK
        ForeignKey related_payment FK
        CharField provider_transaction_id
        TextField failure_reason
        JSONField metadata
        DateTimeField created_at
        DateTimeField processed_at
    }

    Payment {
        BigAutoField id PK
        ForeignKey award FK
        ForeignKey student FK
        ForeignKey tutor FK
        DecimalField amount
        CharField currency
        CharField payment_type
        CharField status
        DateField due_date
        DateField paid_date
        ForeignKey payment_method FK
        ForeignKey escrow_transaction FK
        CharField invoice_number UK
        TextField description
        TextField student_notes
        TextField tutor_notes
        TextField admin_notes
        BooleanField is_released
        DateField release_date
        DecimalField refund_amount
        TextField refund_reason
        DateField refund_date
        DateTimeField created_at
        DateTimeField updated_at
    }

    PaymentSplit {
        BigAutoField id PK
        ForeignKey payment FK
        ForeignKey milestone FK
        ForeignKey session FK
        DecimalField amount
        CharField status
        DateField release_date
        DateTimeField created_at
        DateTimeField updated_at
    }

    Commission {
        BigAutoField id PK
        ForeignKey payment FK
        CharField commission_type
        DecimalField commission_rate
        DecimalField commission_amount
        CharField currency
        CharField description
        BooleanField is_collected
        DateField collected_date
        DateTimeField created_at
        DateTimeField updated_at
    }

    CommissionRate {
        BigAutoField id PK
        CharField name
        CharField rate_type
        DecimalField rate_value
        DecimalField min_amount
        DecimalField max_amount
        CharField user_type
        ForeignKey subject FK
        BooleanField is_active
        DateField effective_from
        DateField effective_to
        DateTimeField created_at
        DateTimeField updated_at
    }

    PayPalAccount {
        BigAutoField id PK
        ForeignKey user FK
        EmailField paypal_email UK
        CharField paypal_user_id
        CharField account_type
        CharField verification_status
        BooleanField is_primary
        BooleanField is_active
        CharField access_token
        CharField refresh_token
        DateTimeField token_expires_at
        JSONField metadata
        DateTimeField created_at
        DateTimeField updated_at
    }

    PayPalTransaction {
        BigAutoField id PK
        ForeignKey payment FK
        CharField paypal_transaction_id UK
        CharField paypal_order_id
        CharField paypal_payment_id
        CharField paypal_payer_id
        CharField paypal_status
        CharField paypal_intent
        DecimalField amount
        CharField currency
        DecimalField fee_amount
        DecimalField net_amount
        JSONField paypal_response
        DateTimeField created_at
        DateTimeField updated_at
    }

    Invoice {
        BigAutoField id PK
        CharField invoice_number UK
        ForeignKey user FK
        ForeignKey payment FK
        CharField invoice_type
        DecimalField amount
        DecimalField tax_amount
        DecimalField total_amount
        CharField currency
        CharField status
        DateField issue_date
        DateField due_date
        DateField paid_date
        TextField billing_address
        TextField notes
        TextField terms
        DateTimeField created_at
        DateTimeField updated_at
    }

    InvoiceItem {
        BigAutoField id PK
        ForeignKey invoice FK
        CharField description
        DecimalField quantity
        DecimalField unit_price
        DecimalField amount
        DateTimeField created_at
    }

    FinancialSummary {
        BigAutoField id PK
        CharField period_type
        DateField period_start
        DateField period_end
        DecimalField total_payments
        DecimalField total_commissions
        DecimalField total_refunds
        DecimalField net_revenue
        CharField currency
        DateTimeField created_at
    }

    %% Notifications App Models
    NotificationType {
        BigAutoField id PK
        CharField name UK
        CharField code UK
        CharField category
        TextField description
        TextField default_template
        TextField email_template
        TextField sms_template
        TextField push_template
        BooleanField is_active
        BooleanField is_system
        CharField priority
        PositiveIntegerField default_expiration_hours
        DateTimeField created_at
        DateTimeField updated_at
    }

    Notification {
        BigAutoField id PK
        ForeignKey recipient FK
        ForeignKey sender FK
        ForeignKey notification_type FK
        CharField title
        TextField message
        URLField action_url
        CharField action_text
        CharField related_object_type
        PositiveIntegerField related_object_id
        BooleanField is_read
        BooleanField is_email_sent
        BooleanField is_sms_sent
        BooleanField is_push_sent
        DateTimeField read_at
        DateTimeField email_sent_at
        DateTimeField sms_sent_at
        DateTimeField push_sent_at
        DateTimeField expires_at
        JSONField metadata
        DateTimeField created_at
        DateTimeField updated_at
    }

    NotificationPreference {
        BigAutoField id PK
        ForeignKey user FK
        BooleanField email_notifications
        BooleanField sms_notifications
        BooleanField push_notifications
        BooleanField in_app_notifications
        BooleanField marketing_emails
        CharField digest_frequency
        TimeField quiet_hours_start
        TimeField quiet_hours_end
        CharField timezone
        CharField minimum_priority
        DateTimeField created_at
        DateTimeField updated_at
    }

    NotificationTypePreference {
        BigAutoField id PK
        ForeignKey user FK
        ForeignKey notification_type FK
        BooleanField is_enabled
        BooleanField email_enabled
        BooleanField sms_enabled
        BooleanField push_enabled
        BooleanField in_app_enabled
        DateTimeField created_at
        DateTimeField updated_at
    }

    NotificationTemplate {
        BigAutoField id PK
        ForeignKey notification_type FK
        CharField language
        CharField channel
        CharField subject_template
        TextField body_template
        JSONField variables
        BooleanField is_active
        DateTimeField created_at
        DateTimeField updated_at
    }

    NotificationDelivery {
        BigAutoField id PK
        ForeignKey notification FK
        CharField channel
        CharField status
        CharField recipient_address
        DateTimeField sent_at
        DateTimeField delivered_at
        DateTimeField failed_at
        TextField failure_reason
        CharField delivery_provider
        JSONField provider_response
        DateTimeField created_at
        DateTimeField updated_at
    }

    NotificationDigest {
        BigAutoField id PK
        ForeignKey user FK
        CharField frequency
        TextField subject
        TextField content
        BooleanField is_sent
        DateTimeField sent_at
        DateTimeField created_at
        DateTimeField updated_at
    }

    PushDevice {
        BigAutoField id PK
        ForeignKey user FK
        CharField device_token
        CharField device_type
        CharField device_id
        CharField app_version
        CharField os_version
        BooleanField is_active
        DateTimeField last_used_at
        DateTimeField created_at
        DateTimeField updated_at
    }

    PushMessage {
        BigAutoField id PK
        ForeignKey notification FK
        ForeignKey device FK
        CharField title
        TextField body
        URLField icon
        URLField image
        CharField sound
        PositiveIntegerField badge
        JSONField data
        CharField status
        DateTimeField sent_at
        DateTimeField delivered_at
        DateTimeField failed_at
        TextField failure_reason
        DateTimeField created_at
        DateTimeField updated_at
    }

    SystemNotification {
        BigAutoField id PK
        CharField title
        TextField message
        CharField notification_type
        CharField priority
        BooleanField is_active
        DateTimeField start_time
        DateTimeField end_time
        CharField target_audience
        URLField action_url
        CharField action_text
        BooleanField is_dismissible
        ForeignKey created_by FK
        DateTimeField created_at
        DateTimeField updated_at
    }

    SystemNotificationDismissal {
        BigAutoField id PK
        ForeignKey system_notification FK
        ForeignKey user FK
        DateTimeField dismissed_at
    }

    NotificationAnalytics {
        BigAutoField id PK
        DateField date
        ForeignKey notification_type FK
        PositiveIntegerField total_sent
        PositiveIntegerField email_sent
        PositiveIntegerField sms_sent
        PositiveIntegerField push_sent
        PositiveIntegerField total_delivered
        PositiveIntegerField email_delivered
        PositiveIntegerField sms_delivered
        PositiveIntegerField push_delivered
        PositiveIntegerField total_read
        DateTimeField created_at
    }

    %% Relationships
    User ||--o{ StudentProfile : has
    User ||--o{ TutorProfile : has
    User ||--o{ AdminProfile : has
    User ||--o{ UserPreferences : has
    User ||--o{ TutorSubject : teaches
    User ||--o{ TutorVerification : verifies
    User ||--o{ TutorRating : rates
    User ||--o{ Requirement : posts
    User ||--o{ Proposal : submits
    User ||--o{ SavedRequirement : saves
    User ||--o{ FavoriteTutor : favors
    User ||--o{ Review : writes
    User ||--o{ MaskedEmail : participates
    User ||--o{ Conversation : participates
    User ||--o{ Message : sends
    User ||--o{ SharedFile : shares
    User ||--o{ OnlineClass : hosts
    User ||--o{ ClassParticipant : attends
    User ||--o{ CommunicationPreference : sets
    User ||--o{ BlockedUser : blocks
    User ||--o{ PaymentMethod : owns
    User ||--o{ EscrowAccount : has
    User ||--o{ PayPalAccount : connects
    User ||--o{ Invoice : receives
    User ||--o{ Notification : receives
    User ||--o{ NotificationPreference : sets
    User ||--o{ NotificationTypePreference : configures
    User ||--o{ PushDevice : registers
    User ||--o{ SystemNotificationDismissal : dismisses

    Subject ||--o{ Subject : parent_child
    Subject ||--o{ TutorSubject : taught_in
    Subject ||--o{ Requirement : required_for
    Subject ||--o{ CommissionRate : applies_to

    Requirement ||--o{ RequirementAttachment : has
    Requirement ||--o{ Proposal : receives
    Requirement ||--o{ Award : results_in
    Requirement ||--o{ SavedRequirement : saved_by
    Requirement ||--o{ TutorRating : rated_in

    Proposal ||--o{ ProposalAttachment : has
    Proposal ||--o{ Award : becomes

    Award ||--o{ Milestone : contains
    Award ||--o{ Session : includes
    Award ||--o{ Review : receives
    Award ||--o{ MaskedEmail : enables
    Award ||--o{ Conversation : starts
    Award ||--o{ SharedFile : shares
    Award ||--o{ Payment : requires
    Award ||--o{ Payment : pays_for

    Milestone ||--o{ PaymentSplit : pays

    Session ||--o{ OnlineClass : has
    Session ||--o{ PaymentSplit : pays

    MaskedEmail ||--o{ EmailLog : logs
    EmailLog ||--o{ EmailAttachment : contains

    Conversation ||--o{ Message : contains
    Message ||--o{ MessageAttachment : contains
    Message ||--o{ Message : replies_to

    OnlineClass ||--o{ ClassParticipant : has

    EscrowAccount ||--o{ EscrowTransaction : processes

    Payment ||--o{ PaymentSplit : splits
    Payment ||--o{ Commission : generates
    Payment ||--o{ Invoice : creates
    Payment ||--o{ PayPalTransaction : processes

    Invoice ||--o{ InvoiceItem : contains

    Notification ||--o{ NotificationDelivery : delivers
    Notification ||--o{ PushMessage : sends

    NotificationType ||--o{ Notification : generates
    NotificationType ||--o{ NotificationTypePreference : configured_in
    NotificationType ||--o{ NotificationTemplate : templated_for
    NotificationType ||--o{ NotificationAnalytics : tracked_in

    SystemNotification ||--o{ SystemNotificationDismissal : dismissed_by
```

## 3. Key Relationship Patterns

### 3.1 User-Centric Relationships
The User model is central to the platform, connecting to:
- Profile models (StudentProfile, TutorProfile, AdminProfile)
- Activity models (Requirements, Proposals, Awards)
- Communication models (Conversations, Messages)
- Payment models (PaymentMethods, EscrowAccounts)
- Notification models (Notifications, Preferences)

### 3.2 Requirement-to-Award Workflow
The core business flow follows this pattern:
1. User creates Requirement
2. Tutor submits Proposal
3. Student accepts Proposal → creates Award
4. Award triggers:
   - Payment processing
   - Masked email creation
   - Conversation initiation
   - Session scheduling

### 3.3 Payment Flow
Payment processing follows this pattern:
1. Award creates Payment
2. Payment funds go to Escrow
3. Escrow releases funds upon completion
4. Commission is deducted
5. Remaining funds go to tutor

### 3.4 Notification System
Notifications are generated by:
- System events (Requirement posted, Proposal received)
- User actions (Message sent, Payment made)
- Scheduled events (Session reminders)

## 4. Data Integrity Constraints

### 4.1 Unique Constraints
- User.username, User.email
- Subject.name, Subject.slug
- Requirement.slug
- Payment.invoice_number
- NotificationType.name, NotificationType.code
- PayPalTransaction.paypal_transaction_id

### 4.2 Foreign Key Constraints
All relationships maintain referential integrity through Django's ForeignKey constraints.

### 4.3 Check Constraints
- Positive values for counts, amounts, durations
- Valid choice values for status fields
- Date validations (end_date > start_date)

## 5. Performance Considerations

### 5.1 Critical Query Paths
1. Finding available tutors (User.user_type='TUTOR', TutorProfile.availability_status='AVAILABLE')
2. Filtering requirements by subject and status
3. Retrieving user notifications (unread count, recent notifications)
4. Payment status tracking for users

### 5.2 Index Strategy
- Composite indexes for frequently queried field combinations
- Partial indexes for active records only
- Full-text indexes for search functionality

### 5.3 Query Optimization
- Use select_related for forward ForeignKey relationships
- Use prefetch_related for reverse ForeignKey and ManyToMany relationships
- Implement pagination for large result sets

## 6. Scaling Considerations

### 6.1 High-Volume Tables
- Notification (high write volume)
- Message (high write volume)
- EmailLog (high write volume)
- PaymentTransaction (high financial volume)

### 6.2 Partitioning Strategy
Consider partitioning by:
- Date for time-series data (notifications, transactions)
- User ID for user-specific data
- Geographic region for performance

### 6.3 Caching Strategy
- Cache frequently accessed user profiles
- Cache subject hierarchies
- Cache notification counts
- Cache payment status for active awards