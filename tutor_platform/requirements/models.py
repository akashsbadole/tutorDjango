import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

User = get_user_model()


def requirement_attachment_path(instance, filename):
    """Generate path for requirement attachment files"""
    return f"requirement_attachments/{instance.requirement.id}/{filename}"


def proposal_attachment_path(instance, filename):
    """Generate path for proposal attachment files"""
    return f"proposal_attachments/{instance.proposal.id}/{filename}"


class Requirement(models.Model):
    """Main model for student-posted tutoring requirements"""
    
    class BudgetType(models.TextChoices):
        HOURLY_RATE = 'HOURLY_RATE', 'Hourly Rate'
        FIXED_PRICE = 'FIXED_PRICE', 'Fixed Price'
        NOT_SPECIFIED = 'NOT_SPECIFIED', 'Not Specified'
    
    class UrgencyLevel(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'
    
    class LocationType(models.TextChoices):
        ONLINE = 'ONLINE', 'Online'
        IN_PERSON = 'IN_PERSON', 'In Person'
        HYBRID = 'HYBRID', 'Hybrid'
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        AWARDED = 'AWARDED', 'Awarded'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    class Visibility(models.TextChoices):
        PUBLIC = 'PUBLIC', 'Public'
        PRIVATE = 'PRIVATE', 'Private'
        INVITE_ONLY = 'INVITE_ONLY', 'Invite Only'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posted_requirements',
        limit_choices_to={'user_type': 'STUDENT'}
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=250)
    description = models.TextField()
    subject = models.ForeignKey(
        'accounts.Subject',
        on_delete=models.CASCADE,
        related_name='requirements'
    )
    learning_level = models.CharField(
        max_length=20,
        choices=[
            ('ELEMENTARY', 'Elementary School'),
            ('MIDDLE_SCHOOL', 'Middle School'),
            ('HIGH_SCHOOL', 'High School'),
            ('UNDERGRADUATE', 'Undergraduate'),
            ('GRADUATE', 'Graduate'),
            ('PROFESSIONAL', 'Professional')
        ]
    )
    specific_topics = models.TextField(blank=True, null=True)
    budget_type = models.CharField(
        max_length=20,
        choices=BudgetType.choices,
        default=BudgetType.NOT_SPECIFIED
    )
    budget_min = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    budget_max = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    currency = models.CharField(max_length=3, default='USD')
    urgency_level = models.CharField(
        max_length=10,
        choices=UrgencyLevel.choices,
        default=UrgencyLevel.MEDIUM
    )
    deadline = models.DateField(null=True, blank=True)
    preferred_schedule = models.TextField(blank=True, null=True)
    timezone = models.CharField(max_length=50, default='UTC')
    session_duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in minutes"
    )
    number_of_sessions = models.PositiveIntegerField(null=True, blank=True)
    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices,
        default=LocationType.ONLINE
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC
    )
    is_featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    proposal_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Requirement'
        verbose_name_plural = 'Requirements'
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['subject_id']),
            models.Index(fields=['status']),
            models.Index(fields=['visibility']),
            models.Index(fields=['created_at']),
            models.Index(fields=['deadline']),
            models.Index(fields=['status', 'visibility']),
            models.Index(fields=['subject_id', 'learning_level']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} by {self.student.get_full_name()}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.title}-{self.student.username}-{uuid.uuid4().hex[:8]}")
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validate the model data"""
        if self.budget_min and self.budget_max:
            if self.budget_min > self.budget_max:
                raise ValidationError('Budget minimum cannot be greater than budget maximum')
        
        if self.deadline and self.deadline <= timezone.now().date():
            raise ValidationError('Deadline must be in the future')
        
        if self.session_duration and self.session_duration <= 0:
            raise ValidationError('Session duration must be positive')
        
        if self.number_of_sessions and self.number_of_sessions <= 0:
            raise ValidationError('Number of sessions must be positive')
    
    def get_budget_range(self):
        """Returns formatted budget range"""
        if self.budget_type == self.BudgetType.NOT_SPECIFIED:
            return "Not specified"
        elif self.budget_min and self.budget_max:
            return f"{self.currency} {self.budget_min} - {self.budget_max}"
        elif self.budget_min:
            return f"{self.currency} {self.budget_min}+"
        elif self.budget_max:
            return f"Up to {self.currency} {self.budget_max}"
        else:
            return "Not specified"
    
    def is_open_for_proposals(self):
        """Check if requirement accepts new proposals"""
        return self.status in [self.Status.OPEN, self.Status.IN_PROGRESS]
    
    def increment_view_count(self):
        """Increment view counter"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def get_absolute_url(self):
        """Return URL to requirement detail"""
        return reverse('requirements:detail', kwargs={'slug': self.slug})


class RequirementAttachment(models.Model):
    """Files attached to requirements"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requirement = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to=requirement_attachment_path)
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_type = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True, null=True)
    is_public = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Requirement Attachment'
        verbose_name_plural = 'Requirement Attachments'
    
    def __str__(self):
        return f"{self.filename} attached to {self.requirement.title}"


class Proposal(models.Model):
    """Tutor responses to requirements"""
    
    class RateType(models.TextChoices):
        HOURLY_RATE = 'HOURLY_RATE', 'Hourly Rate'
        FIXED_PRICE = 'FIXED_PRICE', 'Fixed Price'
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
        SHORTLISTED = 'SHORTLISTED', 'Shortlisted'
        REJECTED = 'REJECTED', 'Rejected'
        ACCEPTED = 'ACCEPTED', 'Accepted'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requirement = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name='proposals'
    )
    tutor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='proposals',
        limit_choices_to={'user_type': 'TUTOR'}
    )
    cover_letter = models.TextField()
    proposed_rate = models.DecimalField(max_digits=8, decimal_places=2)
    rate_type = models.CharField(
        max_length=20,
        choices=RateType.choices
    )
    estimated_hours = models.PositiveIntegerField(null=True, blank=True)
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    approach = models.TextField(blank=True, null=True)
    availability = models.TextField(blank=True, null=True)
    can_start_immediately = models.BooleanField(default=False)
    proposed_start_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    is_shortlisted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Proposal'
        verbose_name_plural = 'Proposals'
        unique_together = ['requirement', 'tutor']
        indexes = [
            models.Index(fields=['requirement_id']),
            models.Index(fields=['tutor_id']),
            models.Index(fields=['status']),
            models.Index(fields=['submitted_at']),
            models.Index(fields=['requirement_id', 'status']),
            models.Index(fields=['tutor_id', 'status']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Proposal by {self.tutor.get_full_name()} for {self.requirement.title}"
    
    def clean(self):
        """Validate the model data"""
        if self.proposed_rate <= 0:
            raise ValidationError('Proposed rate must be positive')
        
        if self.estimated_hours and self.estimated_hours <= 0:
            raise ValidationError('Estimated hours must be positive')
        
        if self.total_amount and self.total_amount <= 0:
            raise ValidationError('Total amount must be positive')
        
        if self.proposed_start_date and self.proposed_start_date <= timezone.now().date():
            raise ValidationError('Proposed start date must be in the future')
    
    def calculate_total_amount(self):
        """Calculate total based on rate and hours"""
        if self.rate_type == self.RateType.HOURLY_RATE and self.estimated_hours:
            return self.proposed_rate * self.estimated_hours
        return self.total_amount
    
    def is_withdrawable(self):
        """Check if proposal can be withdrawn"""
        return self.status in [self.Status.DRAFT, self.Status.SUBMITTED]


class ProposalAttachment(models.Model):
    """Files attached to proposals"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to=proposal_attachment_path)
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_type = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True, null=True)
    is_public = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Proposal Attachment'
        verbose_name_plural = 'Proposal Attachments'
    
    def __str__(self):
        return f"{self.filename} attached to proposal by {self.proposal.tutor.get_full_name()}"


class Award(models.Model):
    """Contract between student and tutor when a proposal is accepted"""
    
    class RateType(models.TextChoices):
        HOURLY_RATE = 'HOURLY_RATE', 'Hourly Rate'
        FIXED_PRICE = 'FIXED_PRICE', 'Fixed Price'
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACTIVE = 'ACTIVE', 'Active'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        DISPUTED = 'DISPUTED', 'Disputed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requirement = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name='award'
    )
    proposal = models.OneToOneField(
        Proposal,
        on_delete=models.CASCADE,
        related_name='award'
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='awards_received'
    )
    tutor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='awards_given'
    )
    agreed_rate = models.DecimalField(max_digits=8, decimal_places=2)
    rate_type = models.CharField(
        max_length=20,
        choices=RateType.choices
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    start_date = models.DateField()
    expected_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    terms_and_conditions = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    cancellation_reason = models.TextField(blank=True, null=True)
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_awards'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Award'
        verbose_name_plural = 'Awards'
        indexes = [
            models.Index(fields=['requirement_id']),
            models.Index(fields=['proposal_id']),
            models.Index(fields=['student_id']),
            models.Index(fields=['tutor_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['student_id', 'status']),
            models.Index(fields=['tutor_id', 'status']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Award for {self.requirement.title} - {self.tutor.get_full_name()}"
    
    def clean(self):
        """Validate the model data"""
        if self.agreed_rate <= 0:
            raise ValidationError('Agreed rate must be positive')
        
        if self.total_amount <= 0:
            raise ValidationError('Total amount must be positive')
        
        if self.start_date and self.start_date <= timezone.now().date():
            raise ValidationError('Start date must be in the future')
        
        if self.expected_end_date and self.start_date:
            if self.expected_end_date <= self.start_date:
                raise ValidationError('Expected end date must be after start date')
    
    def is_active(self):
        """Check if award is currently active"""
        return self.status == self.Status.ACTIVE
    
    def get_duration(self):
        """Calculate duration in days"""
        if self.actual_end_date:
            return (self.actual_end_date - self.start_date).days
        elif self.expected_end_date:
            return (self.expected_end_date - self.start_date).days
        return None
    
    def is_overdue(self):
        """Check if past expected end date"""
        if self.expected_end_date and timezone.now().date() > self.expected_end_date:
            return self.status not in [self.Status.COMPLETED, self.Status.CANCELLED]
        return False


class Milestone(models.Model):
    """For breaking down large requirements into milestones"""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    award = models.ForeignKey(
        Award,
        on_delete=models.CASCADE,
        related_name='milestones'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    completion_notes = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Milestone'
        verbose_name_plural = 'Milestones'
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.title} - {self.award.requirement.title}"


class Session(models.Model):
    """Individual tutoring sessions"""
    
    class LocationType(models.TextChoices):
        ONLINE = 'ONLINE', 'Online'
        IN_PERSON = 'IN_PERSON', 'In Person'
    
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        NO_SHOW = 'NO_SHOW', 'No Show'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    award = models.ForeignKey(
        Award,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField()
    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices
    )
    meeting_url = models.URLField(blank=True, null=True)
    meeting_address = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    cancellation_reason = models.TextField(blank=True, null=True)
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_sessions'
    )
    tutor_notes = models.TextField(blank=True, null=True)
    student_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Session'
        verbose_name_plural = 'Sessions'
        indexes = [
            models.Index(fields=['award_id']),
            models.Index(fields=['scheduled_start']),
            models.Index(fields=['status']),
            models.Index(fields=['award_id', 'status']),
            models.Index(fields=['scheduled_start', 'status']),
        ]
        ordering = ['scheduled_start']
    
    def __str__(self):
        return f"Session: {self.title} ({self.scheduled_start})"
    
    def clean(self):
        """Validate the model data"""
        if self.scheduled_end <= self.scheduled_start:
            raise ValidationError('Scheduled end time must be after start time')
        
        if self.actual_start and self.actual_end:
            if self.actual_end <= self.actual_start:
                raise ValidationError('Actual end time must be after start time')
        
        if self.duration_minutes <= 0:
            raise ValidationError('Duration must be positive')
    
    def get_duration(self):
        """Calculate actual duration"""
        if self.actual_start and self.actual_end:
            return (self.actual_end - self.actual_start).total_seconds() / 60
        return self.duration_minutes
    
    def is_upcoming(self):
        """Check if session is in the future"""
        return self.scheduled_start > timezone.now()
    
    def is_past(self):
        """Check if session is in the past"""
        return self.scheduled_end < timezone.now()
    
    def can_be_cancelled(self):
        """Check cancellation rules"""
        return self.status in [self.Status.SCHEDULED] and self.is_upcoming()


class Review(models.Model):
    """Reviews for completed requirements/sessions"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    award = models.ForeignKey(
        Award,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_reviews'
    )
    reviewee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_reviews'
    )
    rating = models.PositiveIntegerField(
        choices=[(i, f'{i}') for i in range(1, 6)]
    )
    comment = models.TextField(blank=True, null=True)
    communication_rating = models.PositiveIntegerField(
        choices=[(i, f'{i}') for i in range(1, 6)],
        null=True,
        blank=True
    )
    expertise_rating = models.PositiveIntegerField(
        choices=[(i, f'{i}') for i in range(1, 6)],
        null=True,
        blank=True
    )
    punctuality_rating = models.PositiveIntegerField(
        choices=[(i, f'{i}') for i in range(1, 6)],
        null=True,
        blank=True
    )
    would_recommend = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Review'
        verbose_name_plural = 'Reviews'
        unique_together = ['award', 'reviewer']
        indexes = [
            models.Index(fields=['award_id']),
            models.Index(fields=['reviewer_id']),
            models.Index(fields=['reviewee_id']),
            models.Index(fields=['rating']),
            models.Index(fields=['is_public']),
            models.Index(fields=['reviewee_id', 'rating']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review by {self.reviewer.get_full_name()} for {self.reviewee.get_full_name()}"
    
    def clean(self):
        """Validate the model data"""
        if self.rating < 1 or self.rating > 5:
            raise ValidationError('Rating must be between 1 and 5')
        
        if self.communication_rating and (self.communication_rating < 1 or self.communication_rating > 5):
            raise ValidationError('Communication rating must be between 1 and 5')
        
        if self.expertise_rating and (self.expertise_rating < 1 or self.expertise_rating > 5):
            raise ValidationError('Expertise rating must be between 1 and 5')
        
        if self.punctuality_rating and (self.punctuality_rating < 1 or self.punctuality_rating > 5):
            raise ValidationError('Punctuality rating must be between 1 and 5')
        
        if self.reviewer == self.reviewee:
            raise ValidationError('Reviewer and reviewee must be different users')
    
    def get_average_rating(self):
        """Calculate average of all rating fields"""
        ratings = [self.rating]
        if self.communication_rating:
            ratings.append(self.communication_rating)
        if self.expertise_rating:
            ratings.append(self.expertise_rating)
        if self.punctuality_rating:
            ratings.append(self.punctuality_rating)
        return sum(ratings) / len(ratings)


class SavedRequirement(models.Model):
    """Requirements saved by students"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_requirements'
    )
    requirement = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name='saved_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Saved Requirement'
        verbose_name_plural = 'Saved Requirements'
        unique_together = ['user', 'requirement']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['requirement_id']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name()} saved {self.requirement.title}"


class FavoriteTutor(models.Model):
    """Tutors favorited by students"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorite_tutors'
    )
    tutor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorited_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Favorite Tutor'
        verbose_name_plural = 'Favorite Tutors'
        unique_together = ['student', 'tutor']
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['tutor_id']),
        ]
    
    def __str__(self):
        return f"{self.student.get_full_name()} favorited {self.tutor.get_full_name()}"
