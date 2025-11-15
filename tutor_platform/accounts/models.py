import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


def user_profile_picture_path(instance, filename):
    """Generate path for user profile picture"""
    return f"profile_pictures/{instance.username}/{filename}"


class UserManager(BaseUserManager):
    """Custom manager for User model"""
    
    def create_user(self, username, email, password=None, user_type='STUDENT', **extra_fields):
        """Create and return a regular user"""
        if not username:
            raise ValueError(_('The Username must be set'))
        if not email:
            raise ValueError(_('The Email must be set'))
        
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        user = self.model(
            username=username, 
            email=email, 
            user_type=user_type,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'ADMIN')
        extra_fields.setdefault('is_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
            
        return self.create_user(username, email, password, **extra_fields)
    
    def get_students(self):
        """Get all student users"""
        return self.filter(user_type='STUDENT')
    
    def get_tutors(self):
        """Get all tutor users"""
        return self.filter(user_type='TUTOR')
    
    def get_admins(self):
        """Get all admin users"""
        return self.filter(user_type='ADMIN')
    
    def get_online_tutors(self):
        """Get all online tutors"""
        return self.filter(user_type='TUTOR', is_online=True, is_active=True)
    
    def get_verified_tutors(self):
        """Get all verified tutors"""
        return self.filter(user_type='TUTOR', is_verified=True, is_active=True)


class User(AbstractUser):
    """Custom User model with role-based access"""
    
    class UserType(models.TextChoices):
        STUDENT = 'STUDENT', _('Student')
        TUTOR = 'TUTOR', _('Tutor')
        ADMIN = 'ADMIN', _('Admin')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[UnicodeUsernameValidator()],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    email = models.EmailField(_('email address'), unique=True)
    user_type = models.CharField(
        _('user type'),
        max_length=10,
        choices=UserType.choices,
        default=UserType.STUDENT,
    )
    is_online = models.BooleanField(_('online status'), default=False)
    is_verified = models.BooleanField(_('verified status'), default=False)
    phone_number = models.CharField(
        _('phone number'),
        max_length=20,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message=_("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
            )
        ]
    )
    timezone = models.CharField(_('timezone'), max_length=50, default='UTC')
    profile_picture = models.ImageField(
        _('profile picture'),
        upload_to=user_profile_picture_path,
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(_('date created'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date updated'), auto_now=True)
    
    objects = UserManager()  # type: ignore
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
            models.Index(fields=['is_online']),
            models.Index(fields=['is_verified']),
            models.Index(fields=['user_type', 'is_online']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    def get_full_name(self):
        """Return the user's full name"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username
    
    def get_short_name(self):
        """Return the user's short name"""
        return self.first_name or self.username
    
    def is_tutor(self):
        """Check if user is a tutor"""
        return self.user_type == self.UserType.TUTOR
    
    def is_student(self):
        """Check if user is a student"""
        return self.user_type == self.UserType.STUDENT
    
    def is_admin_user(self):
        """Check if user is an admin"""
        return self.user_type == self.UserType.ADMIN
    
    def get_profile(self):
        """Get the profile related to this user"""
        if self.is_student():
            return getattr(self, 'studentprofile', None)
        elif self.is_tutor():
            return getattr(self, 'tutorprofile', None)
        elif self.is_admin_user():
            return getattr(self, 'adminprofile', None)
        return None


class StudentProfile(models.Model):
    """Profile model for students"""
    
    class EducationalStatus(models.TextChoices):
        K12 = 'K12', _('K-12')
        UNDERGRADUATE = 'UNDERGRADUATE', _('Undergraduate')
        GRADUATE = 'GRADUATE', _('Graduate')
        PROFESSIONAL = 'PROFESSIONAL', _('Professional')
    
    class LearningStyle(models.TextChoices):
        VISUAL = 'VISUAL', _('Visual')
        AUDITORY = 'AUDITORY', _('Auditory')
        KINESTHETIC = 'KINESTHETIC', _('Kinesthetic')
        READING = 'READING', _('Reading/Writing')
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='studentprofile',
        verbose_name=_('user')
    )
    educational_status = models.CharField(
        _('educational status'),
        max_length=20,
        choices=EducationalStatus.choices,
        default=EducationalStatus.UNDERGRADUATE
    )
    institution = models.CharField(_('institution'), max_length=200, blank=True, null=True)
    grade_level = models.CharField(_('grade level'), max_length=50, blank=True, null=True)
    major_field = models.CharField(_('major field'), max_length=100, blank=True, null=True)
    learning_goals = models.TextField(_('learning goals'), blank=True, null=True)
    preferred_learning_style = models.CharField(
        _('preferred learning style'),
        max_length=20,
        choices=LearningStyle.choices,
        blank=True,
        null=True
    )
    bio = models.TextField(_('bio'), max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(_('date created'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date updated'), auto_now=True)
    
    class Meta:
        verbose_name = _('Student Profile')
        verbose_name_plural = _('Student Profiles')
    
    def __str__(self):
        return f"Student Profile: {self.user.get_full_name()}"


class TutorProfile(models.Model):
    """Profile model for tutors"""
    
    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', _('Available')
        BUSY = 'BUSY', _('Busy')
        OFFLINE = 'OFFLINE', _('Offline')
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='tutorprofile',
        verbose_name=_('user')
    )
    professional_title = models.CharField(_('professional title'), max_length=100, blank=True, null=True)
    experience_years = models.PositiveIntegerField(_('years of experience'), default=0)
    education = models.TextField(_('education'), blank=True, null=True)
    bio = models.TextField(_('bio'), max_length=500, blank=True, null=True)
    hourly_rate_min = models.DecimalField(
        _('minimum hourly rate'),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Minimum hourly rate in USD')
    )
    hourly_rate_max = models.DecimalField(
        _('maximum hourly rate'),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Maximum hourly rate in USD')
    )
    availability_status = models.CharField(
        _('availability status'),
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.OFFLINE
    )
    response_time_hours = models.PositiveIntegerField(
        _('response time in hours'),
        default=24,
        help_text=_('Average response time to student inquiries')
    )
    languages = models.CharField(
        _('languages'),
        max_length=200,
        blank=True,
        null=True,
        help_text=_('Comma-separated list of languages spoken')
    )
    teaching_experience = models.TextField(_('teaching experience'), blank=True, null=True)
    profile_completion_score = models.PositiveIntegerField(
        _('profile completion score'),
        default=0,
        help_text=_('Percentage of profile completion (0-100)')
    )
    is_featured = models.BooleanField(_('featured tutor'), default=False)
    created_at = models.DateTimeField(_('date created'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date updated'), auto_now=True)
    
    class Meta:
        verbose_name = _('Tutor Profile')
        verbose_name_plural = _('Tutor Profiles')
        indexes = [
            models.Index(fields=['availability_status']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['hourly_rate_min']),
            models.Index(fields=['hourly_rate_max']),
        ]
    
    def __str__(self):
        return f"Tutor Profile: {self.user.get_full_name()}"
    
    def clean(self):
        """Validate the model data"""
        if self.hourly_rate_min and self.hourly_rate_max:
            if self.hourly_rate_min > self.hourly_rate_max:
                raise ValidationError(_('Minimum hourly rate cannot be greater than maximum hourly rate'))
    
    def get_average_rating(self):
        """Calculate average rating from reviews"""
        ratings = self.ratings.all()
        if ratings.exists():
            return sum(rating.rating for rating in ratings) / ratings.count()
        return 0
    
    def get_completed_sessions(self):
        """Count completed tutoring sessions"""
        # This will be implemented when we create the requirements app
        return 0
    
    def update_profile_completion(self):
        """Calculate and update profile completion percentage"""
        fields_to_check = [
            self.professional_title,
            self.education,
            self.bio,
            self.hourly_rate_min,
            self.hourly_rate_max,
            self.languages,
            self.teaching_experience,
        ]
        
        completed_fields = sum(1 for field in fields_to_check if field)
        completion_percentage = (completed_fields / len(fields_to_check)) * 100
        self.profile_completion_score = int(completion_percentage)
        self.save(update_fields=['profile_completion_score'])


class AdminProfile(models.Model):
    """Profile model for administrators"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='adminprofile',
        verbose_name=_('user')
    )
    department = models.CharField(_('department'), max_length=100, blank=True, null=True)
    permissions = models.JSONField(
        _('permissions'),
        default=dict,
        help_text=_('Store admin permissions as JSON')
    )
    created_at = models.DateTimeField(_('date created'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date updated'), auto_now=True)
    
    class Meta:
        verbose_name = _('Admin Profile')
        verbose_name_plural = _('Admin Profiles')
    
    def __str__(self):
        return f"Admin Profile: {self.user.get_full_name()}"


class Subject(models.Model):
    """Hierarchical subject model"""
    
    name = models.CharField(_('name'), max_length=100, unique=True)
    slug = models.SlugField(_('slug'), max_length=120, unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('parent subject')
    )
    description = models.TextField(_('description'), blank=True, null=True)
    icon = models.CharField(
        _('icon'),
        max_length=50,
        blank=True,
        null=True,
        help_text=_('Icon class name (e.g., "fas fa-math")')
    )
    is_active = models.BooleanField(_('active'), default=True)
    order = models.PositiveIntegerField(_('order'), default=0)
    created_at = models.DateTimeField(_('date created'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date updated'), auto_now=True)
    
    class Meta:
        verbose_name = _('Subject')
        verbose_name_plural = _('Subjects')
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['parent_id']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.get_full_path() if self.parent else self.name
    
    def get_full_path(self):
        """Returns subject hierarchy (e.g., "Math > Calculus > Integrals")"""
        if self.parent:
            return f"{self.parent.get_full_path()} > {self.name}"
        return self.name
    
    def get_children(self):
        """Returns direct child subjects"""
        return self.children.filter(is_active=True)
    
    def get_all_children(self):
        """Returns all descendant subjects"""
        children = []
        for child in self.get_children():
            children.append(child)
            children.extend(child.get_all_children())
        return children


class TutorSubject(models.Model):
    """Many-to-Many relationship between TutorProfile and Subject with additional fields"""
    
    class ProficiencyLevel(models.TextChoices):
        BEGINNER = 'BEGINNER', _('Beginner')
        INTERMEDIATE = 'INTERMEDIATE', _('Intermediate')
        ADVANCED = 'ADVANCED', _('Advanced')
        EXPERT = 'EXPERT', _('Expert')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tutor = models.ForeignKey(
        TutorProfile,
        on_delete=models.CASCADE,
        related_name='tutor_subjects',
        verbose_name=_('tutor')
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='tutor_subjects',
        verbose_name=_('subject')
    )
    proficiency_level = models.CharField(
        _('proficiency level'),
        max_length=20,
        choices=ProficiencyLevel.choices,
        default=ProficiencyLevel.INTERMEDIATE
    )
    hourly_rate = models.DecimalField(
        _('hourly rate'),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Specific hourly rate for this subject')
    )
    is_primary_subject = models.BooleanField(_('primary subject'), default=False)
    years_of_experience = models.PositiveIntegerField(
        _('years of experience'),
        default=0,
        help_text=_('Years of experience teaching this specific subject')
    )
    created_at = models.DateTimeField(_('date created'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date updated'), auto_now=True)
    
    class Meta:
        verbose_name = _('Tutor Subject')
        verbose_name_plural = _('Tutor Subjects')
        unique_together = ['tutor', 'subject']
        indexes = [
            models.Index(fields=['subject_id']),
            models.Index(fields=['tutor_id']),
            models.Index(fields=['subject_id', 'proficiency_level']),
        ]
    
    def __str__(self):
        return f"{self.tutor.user.get_full_name()} - {self.subject.name}"


class TutorVerification(models.Model):
    """Store tutor credential verification information"""
    
    class VerificationType(models.TextChoices):
        IDENTITY = 'IDENTITY', _('Identity Verification')
        EDUCATION = 'EDUCATION', _('Education Verification')
        PROFESSIONAL = 'PROFESSIONAL', _('Professional Certification')
        BACKGROUND_CHECK = 'BACKGROUND_CHECK', _('Background Check')
    
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        EXPIRED = 'EXPIRED', _('Expired')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tutor = models.ForeignKey(
        TutorProfile,
        on_delete=models.CASCADE,
        related_name='verifications',
        verbose_name=_('tutor')
    )
    verification_type = models.CharField(
        _('verification type'),
        max_length=20,
        choices=VerificationType.choices
    )
    document = models.FileField(
        _('document'),
        upload_to='verifications/',
        help_text=_('Upload verification document')
    )
    document_number = models.CharField(_('document number'), max_length=100, blank=True, null=True)
    issuing_authority = models.CharField(_('issuing authority'), max_length=200, blank=True, null=True)
    issue_date = models.DateField(_('issue date'), null=True, blank=True)
    expiry_date = models.DateField(_('expiry date'), null=True, blank=True)
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_tutors',
        verbose_name=_('verified by')
    )
    verification_notes = models.TextField(_('verification notes'), blank=True, null=True)
    admin_comments = models.TextField(_('admin comments'), blank=True, null=True)
    submitted_at = models.DateTimeField(_('submitted at'), auto_now_add=True)
    reviewed_at = models.DateTimeField(_('reviewed at'), null=True, blank=True)
    expires_at = models.DateTimeField(_('expires at'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Tutor Verification')
        verbose_name_plural = _('Tutor Verifications')
        indexes = [
            models.Index(fields=['tutor_id']),
            models.Index(fields=['status']),
            models.Index(fields=['tutor_id', 'status']),
        ]
    
    def __str__(self):
        return f"{self.tutor.user.get_full_name()} - {self.get_verification_type_display()}"
    
    def clean(self):
        """Validate the model data"""
        if self.issue_date and self.expiry_date:
            if self.issue_date > self.expiry_date:
                raise ValidationError(_('Issue date cannot be after expiry date'))
    
    def is_expired(self):
        """Check if verification is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False
    
    def is_valid(self):
        """Check if verification is valid and not expired"""
        return self.status == self.VerificationStatus.APPROVED and not self.is_expired()


class TutorRating(models.Model):
    """Store ratings and reviews for tutors"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tutor = models.ForeignKey(
        TutorProfile,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name=_('tutor')
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_ratings',
        verbose_name=_('student')
    )
    # requirement = models.ForeignKey(
    #     'requirements.Requirement',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='ratings',
    #     verbose_name=_('requirement')
    # )
    # Temporarily commented out until requirements app is implemented
    requirement = None
    rating = models.PositiveIntegerField(
        _('rating'),
        choices=[
            (1, '1 - Poor'),
            (2, '2 - Fair'),
            (3, '3 - Good'),
            (4, '4 - Very Good'),
            (5, '5 - Excellent')
        ],
        help_text=_('Rating from 1 to 5')
    )
    review = models.TextField(_('review'), blank=True, null=True)
    is_public = models.BooleanField(_('public'), default=True)
    created_at = models.DateTimeField(_('date created'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date updated'), auto_now=True)
    
    class Meta:
        verbose_name = _('Tutor Rating')
        verbose_name_plural = _('Tutor Ratings')
        # Temporarily commented out until requirements app is implemented
        # unique_together = ['tutor', 'student', 'requirement']
        unique_together = ['tutor', 'student']
        indexes = [
            models.Index(fields=['tutor_id']),
            models.Index(fields=['rating']),
            models.Index(fields=['tutor_id', 'rating']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} rated {self.tutor.user.get_full_name()}: {self.rating}/5"


class UserPreferences(models.Model):
    """Store user-specific preferences"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preferences',
        verbose_name=_('user')
    )
    email_notifications = models.BooleanField(_('email notifications'), default=True)
    sms_notifications = models.BooleanField(_('SMS notifications'), default=False)
    push_notifications = models.BooleanField(_('push notifications'), default=True)
    marketing_emails = models.BooleanField(_('marketing emails'), default=False)
    language = models.CharField(_('language'), max_length=10, default='en')
    timezone = models.CharField(_('timezone'), max_length=50, default='UTC')
    currency = models.CharField(_('currency'), max_length=3, default='USD')
    created_at = models.DateTimeField(_('date created'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date updated'), auto_now=True)
    
    class Meta:
        verbose_name = _('User Preferences')
        verbose_name_plural = _('User Preferences')
    
    def __str__(self):
        return f"Preferences for {self.user.get_full_name()}"
