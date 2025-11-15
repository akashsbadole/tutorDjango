# Accounts Models Design

## 1. Custom User Model

### User (Custom AbstractUser)
- Inherits from Django's AbstractUser to extend built-in User model
- Fields:
  - id: BigAutoField (primary key)
  - username: CharField (unique)
  - email: EmailField (unique)
  - first_name: CharField
  - last_name: CharField
  - is_staff: BooleanField (admin access)
  - is_active: BooleanField
  - date_joined: DateTimeField (auto_now_add)
  - last_login: DateTimeField (auto_now)
  - user_type: CharField (choices: STUDENT, TUTOR, ADMIN)
  - is_online: BooleanField (default=False) - For tutor availability
  - is_verified: BooleanField (default=False) - For account verification
  - phone_number: CharField (blank=True, null=True)
  - timezone: CharField (default='UTC')
  - profile_picture: ImageField (blank=True, null=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - get_full_name()
  - get_short_name()
  - is_tutor() - Returns True if user_type is TUTOR
  - is_student() - Returns True if user_type is STUDENT
  - is_admin_user() - Returns True if user_type is ADMIN

## 2. Profile Models

### StudentProfile
- One-to-One relationship with User (user_type='STUDENT')
- Fields:
  - user: OneToOneField(User)
  - educational_status: CharField (choices: K12, UNDERGRADUATE, GRADUATE, PROFESSIONAL)
  - institution: CharField (blank=True, null=True)
  - grade_level: CharField (blank=True, null=True)
  - major_field: CharField (blank=True, null=True)
  - learning_goals: TextField (blank=True, null=True)
  - preferred_learning_style: CharField (choices: VISUAL, AUDITORY, KINESTHETIC, READING)
  - bio: TextField (blank=True, null=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

### TutorProfile
- One-to-One relationship with User (user_type='TUTOR')
- Fields:
  - user: OneToOneField(User)
  - professional_title: CharField (blank=True, null=True)
  - experience_years: PositiveIntegerField (default=0)
  - education: TextField (blank=True, null=True)
  - bio: TextField (blank=True, null=True)
  - hourly_rate_min: DecimalField (max_digits=6, decimal_places=2, null=True, blank=True)
  - hourly_rate_max: DecimalField (max_digits=6, decimal_places=2, null=True, blank=True)
  - availability_status: CharField (choices: AVAILABLE, BUSY, OFFLINE, default=OFFLINE)
  - response_time_hours: PositiveIntegerField (default=24)
  - languages: CharField (blank=True, null=True) - Comma-separated
  - teaching_experience: TextField (blank=True, null=True)
  - profile_completion_score: PositiveIntegerField (default=0)
  - is_featured: BooleanField (default=False)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - get_average_rating() - Calculate from reviews
  - get_completed_sessions() - Count completed requirements
  - update_profile_completion() - Calculate completion percentage

### AdminProfile
- One-to-One relationship with User (user_type='ADMIN')
- Fields:
  - user: OneToOneField(User)
  - department: CharField (blank=True, null=True)
  - permissions: JSONField (default=dict) - Store admin permissions
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

## 3. Subject and Certification Models

### Subject
- Hierarchical subject structure
- Fields:
  - id: BigAutoField (primary key)
  - name: CharField (unique=True)
  - slug: SlugField (unique=True)
  - parent: ForeignKey('self', null=True, blank=True, related_name='children')
  - description: TextField (blank=True, null=True)
  - icon: CharField (blank=True, null=True) - Icon class name
  - is_active: BooleanField (default=True)
  - order: PositiveIntegerField (default=0)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - get_full_path() - Returns subject hierarchy (e.g., "Math > Calculus > Integrals")
  - get_children() - Returns direct child subjects
  - get_all_children() - Returns all descendant subjects

### TutorSubject
- Many-to-Many relationship between TutorProfile and Subject with additional fields
- Fields:
  - id: BigAutoField (primary key)
  - tutor: ForeignKey(TutorProfile)
  - subject: ForeignKey(Subject)
  - proficiency_level: CharField (choices: BEGINNER, INTERMEDIATE, ADVANCED, EXPERT)
  - hourly_rate: DecimalField (max_digits=6, decimal_places=2, null=True, blank=True)
  - is_primary_subject: BooleanField (default=False)
  - years_of_experience: PositiveIntegerField (default=0)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Unique constraint: (tutor, subject)

## 4. Verification Models

### TutorVerification
- Store tutor credential verification information
- Fields:
  - id: BigAutoField (primary key)
  - tutor: ForeignKey(TutorProfile)
  - verification_type: CharField (choices: IDENTITY, EDUCATION, PROFESSIONAL, BACKGROUND_CHECK)
  - document: FileField (upload_to='verifications/')
  - document_number: CharField (blank=True, null=True)
  - issuing_authority: CharField (blank=True, null=True)
  - issue_date: DateField (null=True, blank=True)
  - expiry_date: DateField (null=True, blank=True)
  - status: CharField (choices: PENDING, APPROVED, REJECTED, EXPIRED, default=PENDING)
  - verified_by: ForeignKey(User, null=True, blank=True, related_name='verified_tutors')
  - verification_notes: TextField (blank=True, null=True)
  - admin_comments: TextField (blank=True, null=True)
  - submitted_at: DateTimeField (auto_now_add)
  - reviewed_at: DateTimeField (null=True, blank=True)
  - expires_at: DateTimeField (null=True, blank=True)

- Methods:
  - is_expired() - Check if verification is expired
  - is_valid() - Check if verification is valid and not expired

### TutorRating
- Store ratings and reviews for tutors
- Fields:
  - id: BigAutoField (primary key)
  - tutor: ForeignKey(TutorProfile, related_name='ratings')
  - student: ForeignKey(User, related_name='given_ratings')
  - requirement: ForeignKey('requirements.Requirement', null=True, blank=True)
  - rating: PositiveIntegerField (choices=[1,2,3,4,5])
  - review: TextField (blank=True, null=True)
  - is_public: BooleanField (default=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Unique constraint: (tutor, student, requirement)

## 5. User Preferences and Settings

### UserPreferences
- Store user-specific preferences
- Fields:
  - id: BigAutoField (primary key)
  - user: OneToOneField(User)
  - email_notifications: BooleanField (default=True)
  - sms_notifications: BooleanField (default=False)
  - push_notifications: BooleanField (default=True)
  - marketing_emails: BooleanField (default=False)
  - language: CharField (default='en')
  - timezone: CharField (default='UTC')
  - currency: CharField (default='USD')
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

## 6. Database Indexes for Performance

- User model:
  - Index on email
  - Index on user_type
  - Index on is_online
  - Index on is_verified
  - Composite index on (user_type, is_online) for finding available tutors

- TutorProfile:
  - Index on availability_status
  - Index on is_featured
  - Index on hourly_rate_min, hourly_rate_max

- Subject:
  - Index on slug
  - Index on parent_id
  - Index on is_active

- TutorSubject:
  - Index on subject_id
  - Index on tutor_id
  - Composite index on (subject_id, proficiency_level)

- TutorVerification:
  - Index on tutor_id
  - Index on status
  - Composite index on (tutor_id, status)

- TutorRating:
  - Index on tutor_id
  - Index on rating
  - Composite index on (tutor_id, rating) for sorting

## 7. Constraints and Validation Rules

- User:
  - Email must be unique
  - Username must be unique
  - Phone number format validation

- StudentProfile:
  - Educational status must be valid choice
  - Grade level validation based on educational status

- TutorProfile:
  - Hourly rate validation (min <= max)
  - Experience years must be non-negative

- Subject:
  - Name must be unique
  - Slug must be unique
  - Parent cannot be self

- TutorSubject:
  - Unique constraint on (tutor, subject)
  - Hourly rate must be positive
  - Proficiency level must be valid choice

- TutorVerification:
  - Expiry date must be after issue date
  - Status must be valid choice

- TutorRating:
  - Rating must be between 1-5
  - Unique constraint on (tutor, student, requirement)