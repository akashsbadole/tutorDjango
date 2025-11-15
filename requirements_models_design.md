# Requirements Models Design

## 1. Core Requirement Models

### Requirement
- Main model for student-posted tutoring requirements
- Fields:
  - id: BigAutoField (primary key)
  - student: ForeignKey(User, related_name='posted_requirements')
  - title: CharField (max_length=200)
  - slug: SlugField (unique=True)
  - description: TextField()
  - subject: ForeignKey(Subject, related_name='requirements')
  - learning_level: CharField (choices: ELEMENTARY, MIDDLE_SCHOOL, HIGH_SCHOOL, UNDERGRADUATE, GRADUATE, PROFESSIONAL)
  - specific_topics: TextField (blank=True, null=True) - Detailed topic information
  - budget_type: CharField (choices: HOURLY_RATE, FIXED_PRICE, NOT_SPECIFIED)
  - budget_min: DecimalField (max_digits=8, decimal_places=2, null=True, blank=True)
  - budget_max: DecimalField (max_digits=8, decimal_places=2, null=True, blank=True)
  - currency: CharField (default='USD')
  - urgency_level: CharField (choices: LOW, MEDIUM, HIGH, URGENT)
  - deadline: DateField (null=True, blank=True)
  - preferred_schedule: TextField (blank=True, null=True) - JSON field for schedule preferences
  - timezone: CharField (default='UTC')
  - session_duration: PositiveIntegerField (null=True, blank=True) - In minutes
  - number_of_sessions: PositiveIntegerField (null=True, blank=True)
  - location_type: CharField (choices: ONLINE, IN_PERSON, HYBRID, default=ONLINE)
  - status: CharField (choices: DRAFT, OPEN, IN_PROGRESS, AWARDED, COMPLETED, CANCELLED, default=DRAFT)
  - visibility: CharField (choices: PUBLIC, PRIVATE, INVITE_ONLY, default=PUBLIC)
  - is_featured: BooleanField (default=False)
  - view_count: PositiveIntegerField (default=0)
  - proposal_count: PositiveIntegerField (default=0)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)
  - published_at: DateTimeField (null=True, blank=True)
  - closed_at: DateTimeField (null=True, blank=True)

- Methods:
  - get_budget_range() - Returns formatted budget range
  - is_open_for_proposals() - Check if requirement accepts new proposals
  - increment_view_count() - Increment view counter
  - get_absolute_url() - Return URL to requirement detail

### RequirementAttachment
- Files attached to requirements
- Fields:
  - id: BigAutoField (primary key)
  - requirement: ForeignKey(Requirement, related_name='attachments')
  - file: FileField (upload_to='requirement_attachments/')
  - filename: CharField (max_length=255)
  - file_size: PositiveIntegerField()
  - file_type: CharField (max_length=50)
  - description: CharField (max_length=255, blank=True, null=True)
  - is_public: BooleanField (default=True) - Whether tutors can see this file
  - uploaded_at: DateTimeField (auto_now_add)

## 2. Proposal Models

### Proposal
- Tutor responses to requirements
- Fields:
  - id: BigAutoField (primary key)
  - requirement: ForeignKey(Requirement, related_name='proposals')
  - tutor: ForeignKey(User, related_name='proposals')
  - cover_letter: TextField()
  - proposed_rate: DecimalField (max_digits=8, decimal_places=2)
  - rate_type: CharField (choices: HOURLY_RATE, FIXED_PRICE)
  - estimated_hours: PositiveIntegerField (null=True, blank=True)
  - total_amount: DecimalField (max_digits=10, decimal_places=2, null=True, blank=True)
  - approach: TextField (blank=True, null=True) - How tutor plans to help
  - availability: TextField (blank=True, null=True) - Tutor's availability
  - can_start_immediately: BooleanField (default=False)
  - proposed_start_date: DateField (null=True, blank=True)
  - status: CharField (choices: DRAFT, SUBMITTED, WITHDRAWN, SHORTLISTED, REJECTED, ACCEPTED, default=DRAFT)
  - is_shortlisted: BooleanField (default=False)
  - submitted_at: DateTimeField (null=True, blank=True)
  - reviewed_at: DateTimeField (null=True, blank=True)
  - accepted_at: DateTimeField (null=True, blank=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - calculate_total_amount() - Calculate total based on rate and hours
  - is_withdrawable() - Check if proposal can be withdrawn
  - get_status_display() - Return formatted status

### ProposalAttachment
- Files attached to proposals
- Fields:
  - id: BigAutoField (primary key)
  - proposal: ForeignKey(Proposal, related_name='attachments')
  - file: FileField (upload_to='proposal_attachments/')
  - filename: CharField (max_length=255)
  - file_size: PositiveIntegerField()
  - file_type: CharField (max_length=50)
  - description: CharField (max_length=255, blank=True, null=True)
  - is_public: BooleanField (default=True)
  - uploaded_at: DateTimeField (auto_now_add)

## 3. Award and Contract Models

### Award
- Contract between student and tutor when a proposal is accepted
- Fields:
  - id: BigAutoField (primary key)
  - requirement: ForeignKey(Requirement, related_name='award')
  - proposal: ForeignKey(Proposal, related_name='award')
  - student: ForeignKey(User, related_name='awards_received')
  - tutor: ForeignKey(User, related_name='awards_given')
  - agreed_rate: DecimalField (max_digits=8, decimal_places=2)
  - rate_type: CharField (choices: HOURLY_RATE, FIXED_PRICE)
  - total_amount: DecimalField (max_digits=10, decimal_places=2)
  - currency: CharField (default='USD')
  - start_date: DateField()
  - expected_end_date: DateField (null=True, blank=True)
  - actual_end_date: DateField (null=True, blank=True)
  - terms_and_conditions: TextField (blank=True, null=True)
  - status: CharField (choices: PENDING, ACTIVE, COMPLETED, CANCELLED, DISPUTED, default=PENDING)
  - cancellation_reason: TextField (blank=True, null=True)
  - cancelled_by: ForeignKey(User, null=True, blank=True, related_name='cancelled_awards')
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)
  - activated_at: DateTimeField (null=True, blank=True)
  - completed_at: DateTimeField (null=True, blank=True)
  - cancelled_at: DateTimeField (null=True, blank=True)

- Methods:
  - is_active() - Check if award is currently active
  - get_duration() - Calculate duration in days
  - is_overdue() - Check if past expected end date

### Milestone
- For breaking down large requirements into milestones
- Fields:
  - id: BigAutoField (primary key)
  - award: ForeignKey(Award, related_name='milestones')
  - title: CharField (max_length=200)
  - description: TextField()
  - amount: DecimalField (max_digits=10, decimal_places=2)
  - due_date: DateField (null=True, blank=True)
  - status: CharField (choices: PENDING, IN_PROGRESS, COMPLETED, CANCELLED, default=PENDING)
  - completion_notes: TextField (blank=True, null=True)
  - order: PositiveIntegerField (default=0)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)
  - completed_at: DateTimeField (null=True, blank=True)

## 4. Session Models

### Session
- Individual tutoring sessions
- Fields:
  - id: BigAutoField (primary key)
  - award: ForeignKey(Award, related_name='sessions')
  - title: CharField (max_length=200)
  - description: TextField (blank=True, null=True)
  - scheduled_start: DateTimeField()
  - scheduled_end: DateTimeField()
  - actual_start: DateTimeField (null=True, blank=True)
  - actual_end: DateTimeField (null=True, blank=True)
  - duration_minutes: PositiveIntegerField()
  - location_type: CharField (choices: ONLINE, IN_PERSON)
  - meeting_url: URLField (blank=True, null=True) - For online sessions
  - meeting_address: TextField (blank=True, null=True) - For in-person sessions
  - status: CharField (choices: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED, NO_SHOW, default=SCHEDULED)
  - cancellation_reason: TextField (blank=True, null=True)
  - cancelled_by: ForeignKey(User, null=True, blank=True, related_name='cancelled_sessions')
  - tutor_notes: TextField (blank=True, null=True)
  - student_notes: TextField (blank=True, null=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - get_duration() - Calculate actual duration
  - is_upcoming() - Check if session is in the future
  - is_past() - Check if session is in the past
  - can_be_cancelled() - Check cancellation rules

## 5. Review and Feedback Models

### Review
- Reviews for completed requirements/sessions
- Fields:
  - id: BigAutoField (primary key)
  - award: ForeignKey(Award, related_name='reviews')
  - reviewer: ForeignKey(User, related_name='given_reviews')
  - reviewee: ForeignKey(User, related_name='received_reviews')
  - rating: PositiveIntegerField (choices=[1,2,3,4,5])
  - comment: TextField (blank=True, null=True)
  - communication_rating: PositiveIntegerField (choices=[1,2,3,4,5], null=True, blank=True)
  - expertise_rating: PositiveIntegerField (choices=[1,2,3,4,5], null=True, blank=True)
  - punctuality_rating: PositiveIntegerField (choices=[1,2,3,4,5], null=True, blank=True)
  - would_recommend: BooleanField (default=True)
  - is_public: BooleanField (default=True)
  - is_verified: BooleanField (default=False) - Verified by platform
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - get_average_rating() - Calculate average of all rating fields

## 6. Saved and Favorite Models

### SavedRequirement
- Requirements saved by students
- Fields:
  - id: BigAutoField (primary key)
  - user: ForeignKey(User, related_name='saved_requirements')
  - requirement: ForeignKey(Requirement, related_name='saved_by')
  - created_at: DateTimeField (auto_now_add)

- Unique constraint: (user, requirement)

### FavoriteTutor
- Tutors favorited by students
- Fields:
  - id: BigAutoField (primary key)
  - student: ForeignKey(User, related_name='favorite_tutors')
  - tutor: ForeignKey(User, related_name='favorited_by')
  - created_at: DateTimeField (auto_now_add)

- Unique constraint: (student, tutor)

## 7. Database Indexes for Performance

- Requirement:
  - Index on student_id
  - Index on subject_id
  - Index on status
  - Index on visibility
  - Index on created_at
  - Index on deadline
  - Composite index on (status, visibility)
  - Composite index on (subject_id, learning_level)
  - Composite index on (status, created_at) for filtering open requirements

- Proposal:
  - Index on requirement_id
  - Index on tutor_id
  - Index on status
  - Index on submitted_at
  - Composite index on (requirement_id, status)
  - Composite index on (tutor_id, status)

- Award:
  - Index on requirement_id
  - Index on proposal_id
  - Index on student_id
  - Index on tutor_id
  - Index on status
  - Index on created_at
  - Composite index on (student_id, status)
  - Composite index on (tutor_id, status)

- Session:
  - Index on award_id
  - Index on scheduled_start
  - Index on status
  - Composite index on (award_id, status)
  - Composite index on (scheduled_start, status) for upcoming sessions

- Review:
  - Index on award_id
  - Index on reviewer_id
  - Index on reviewee_id
  - Index on rating
  - Index on is_public
  - Composite index on (reviewee_id, rating) for sorting tutors by rating

## 8. Constraints and Validation Rules

- Requirement:
  - Budget max must be >= budget min
  - Deadline must be in the future
  - Session duration must be positive
  - Number of sessions must be positive

- Proposal:
  - Proposed rate must be positive
  - Estimated hours must be positive
  - Total amount must be positive
  - Unique constraint on (requirement, tutor)

- Award:
  - Agreed rate must be positive
  - Total amount must be positive
  - Start date must be after award creation
  - Expected end date must be after start date

- Session:
  - Scheduled end must be after scheduled start
  - Actual end must be after actual start
  - Duration must be positive

- Review:
  - Rating must be between 1-5
  - All rating fields must be between 1-5
  - Reviewer and reviewee must be different users
  - Unique constraint on (award, reviewer)