from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import (
    Requirement, RequirementAttachment, Proposal, ProposalAttachment,
    Award, Session, Review, SavedRequirement, FavoriteTutor
)
from accounts.models import Subject

User = get_user_model()


class RequirementPostForm(forms.ModelForm):
    """Form for students to post new tutoring requirements"""
    
    class Meta:
        model = Requirement
        fields = [
            'title', 'description', 'subject', 'learning_level', 'specific_topics',
            'budget_type', 'budget_min', 'budget_max', 'currency', 'urgency_level',
            'deadline', 'preferred_schedule', 'timezone', 'session_duration',
            'number_of_sessions', 'location_type', 'visibility'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a descriptive title for your tutoring requirement'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe what you need help with...'
            }),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'learning_level': forms.Select(attrs={'class': 'form-control'}),
            'specific_topics': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Specific topics or areas you need help with...'
            }),
            'budget_type': forms.Select(attrs={'class': 'form-control'}),
            'budget_min': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Minimum budget'
            }),
            'budget_max': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Maximum budget'
            }),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'urgency_level': forms.Select(attrs={'class': 'form-control'}),
            'deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().strftime('%Y-%m-%d')
            }),
            'preferred_schedule': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Your preferred schedule (days, times, etc.)'
            }),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
            'session_duration': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '15',
                'step': '15',
                'placeholder': 'Duration in minutes'
            }),
            'number_of_sessions': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Number of sessions'
            }),
            'location_type': forms.Select(attrs={'class': 'form-control'}),
            'visibility': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter subjects to only active ones
        self.fields['subject'].queryset = Subject.objects.filter(is_active=True)
        
        # Set initial currency from user preferences if available
        if self.user and hasattr(self.user, 'preferences'):
            self.fields['currency'].initial = self.user.preferences.currency
        
        # Set initial timezone from user profile if available
        if self.user and self.user.timezone:
            self.fields['timezone'].initial = self.user.timezone
    
    def clean(self):
        cleaned_data = super().clean()
        budget_type = cleaned_data.get('budget_type')
        budget_min = cleaned_data.get('budget_min')
        budget_max = cleaned_data.get('budget_max')
        deadline = cleaned_data.get('deadline')
        
        # Validate budget fields
        if budget_type != 'NOT_SPECIFIED':
            if not budget_min and not budget_max:
                raise ValidationError(_('Please specify at least a minimum or maximum budget'))
        
        if budget_min and budget_max and budget_min > budget_max:
            raise ValidationError(_('Minimum budget cannot be greater than maximum budget'))
        
        # Validate deadline
        if deadline and deadline <= timezone.now().date():
            raise ValidationError(_('Deadline must be in the future'))
        
        return cleaned_data
    
    def save(self, commit=True):
        requirement = super().save(commit=False)
        if self.user:
            requirement.student = self.user
        if commit:
            requirement.save()
        return requirement


class RequirementAttachmentForm(forms.ModelForm):
    """Form for uploading attachments to requirements"""
    
    class Meta:
        model = RequirementAttachment
        fields = ['file', 'description', 'is_public']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Describe this attachment'
            }),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.requirement = kwargs.pop('requirement', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        attachment = super().save(commit=False)
        if self.requirement:
            attachment.requirement = self.requirement
            if commit:
                attachment.save()
        return attachment


class ProposalForm(forms.ModelForm):
    """Form for tutors to submit proposals"""
    
    class Meta:
        model = Proposal
        fields = [
            'cover_letter', 'proposed_rate', 'rate_type', 'estimated_hours',
            'total_amount', 'approach', 'availability', 'can_start_immediately',
            'proposed_start_date'
        ]
        widgets = {
            'cover_letter': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Introduce yourself and explain why you\'re the right tutor for this requirement...'
            }),
            'proposed_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Your proposed rate'
            }),
            'rate_type': forms.Select(attrs={'class': 'form-control'}),
            'estimated_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Estimated hours (for hourly rate)'
            }),
            'total_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'placeholder': 'Total amount (for fixed price)'
            }),
            'approach': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your approach to helping the student...'
            }),
            'availability': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Your availability for this requirement...'
            }),
            'can_start_immediately': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'proposed_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().strftime('%Y-%m-%d')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.requirement = kwargs.pop('requirement', None)
        super().__init__(*args, **kwargs)
        
        # Set initial rate type based on requirement
        if self.requirement and self.requirement.budget_type != 'NOT_SPECIFIED':
            self.fields['rate_type'].initial = self.requirement.budget_type
    
    def clean(self):
        cleaned_data = super().clean()
        rate_type = cleaned_data.get('rate_type')
        proposed_rate = cleaned_data.get('proposed_rate')
        estimated_hours = cleaned_data.get('estimated_hours')
        total_amount = cleaned_data.get('total_amount')
        proposed_start_date = cleaned_data.get('proposed_start_date')
        
        # Validate rate fields
        if not proposed_rate or proposed_rate <= 0:
            raise ValidationError(_('Proposed rate must be greater than 0'))
        
        if rate_type == 'HOURLY_RATE':
            if not estimated_hours or estimated_hours <= 0:
                raise ValidationError(_('Estimated hours must be specified for hourly rate'))
        elif rate_type == 'FIXED_PRICE':
            if not total_amount or total_amount <= 0:
                raise ValidationError(_('Total amount must be specified for fixed price'))
        
        # Validate start date
        if proposed_start_date and proposed_start_date <= timezone.now().date():
            raise ValidationError(_('Proposed start date must be in the future'))
        
        return cleaned_data
    
    def save(self, commit=True):
        proposal = super().save(commit=False)
        if self.user:
            proposal.tutor = self.user
        if self.requirement:
            proposal.requirement = self.requirement
        if commit:
            proposal.save()
        return proposal


class ProposalAttachmentForm(forms.ModelForm):
    """Form for uploading attachments to proposals"""
    
    class Meta:
        model = ProposalAttachment
        fields = ['file', 'description', 'is_public']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Describe this attachment'
            }),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.proposal = kwargs.pop('proposal', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        attachment = super().save(commit=False)
        if self.proposal:
            attachment.proposal = self.proposal
            if commit:
                attachment.save()
        return attachment


class AwardForm(forms.ModelForm):
    """Form for confirming tutor selection and awarding requirements"""
    
    class Meta:
        model = Award
        fields = [
            'agreed_rate', 'rate_type', 'total_amount', 'currency',
            'start_date', 'expected_end_date', 'terms_and_conditions'
        ]
        widgets = {
            'agreed_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'readonly': True
            }),
            'rate_type': forms.Select(attrs={'class': 'form-control', 'readonly': True}),
            'total_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '0.01',
                'readonly': True
            }),
            'currency': forms.Select(attrs={'class': 'form-control', 'readonly': True}),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().strftime('%Y-%m-%d')
            }),
            'expected_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date().strftime('%Y-%m-%d')
            }),
            'terms_and_conditions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Any specific terms and conditions for this arrangement...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.proposal = kwargs.pop('proposal', None)
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        
        # Pre-fill form fields from proposal
        if self.proposal:
            self.fields['agreed_rate'].initial = self.proposal.proposed_rate
            self.fields['rate_type'].initial = self.proposal.rate_type
            self.fields['total_amount'].initial = self.proposal.calculate_total_amount()
            self.fields['currency'].initial = self.proposal.requirement.currency
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        expected_end_date = cleaned_data.get('expected_end_date')
        
        # Validate dates
        if start_date and start_date <= timezone.now().date():
            raise ValidationError(_('Start date must be in the future'))
        
        if start_date and expected_end_date and expected_end_date <= start_date:
            raise ValidationError(_('Expected end date must be after start date'))
        
        return cleaned_data
    
    def save(self, commit=True):
        award = super().save(commit=False)
        if self.proposal:
            award.proposal = self.proposal
            award.requirement = self.proposal.requirement
            award.tutor = self.proposal.tutor
        if self.student:
            award.student = self.student
        if commit:
            award.save()
        return award


class SessionForm(forms.ModelForm):
    """Form for scheduling tutoring sessions"""
    
    class Meta:
        model = Session
        fields = [
            'title', 'description', 'scheduled_start', 'scheduled_end',
            'duration_minutes', 'location_type', 'meeting_url', 'meeting_address'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Session title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Session description or topics to cover'
            }),
            'scheduled_start': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'scheduled_end': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'duration_minutes': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '15',
                'step': '15',
                'placeholder': 'Duration in minutes'
            }),
            'location_type': forms.Select(attrs={'class': 'form-control'}),
            'meeting_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Meeting URL (for online sessions)'
            }),
            'meeting_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Meeting address (for in-person sessions)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.award = kwargs.pop('award', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        scheduled_start = cleaned_data.get('scheduled_start')
        scheduled_end = cleaned_data.get('scheduled_end')
        duration_minutes = cleaned_data.get('duration_minutes')
        location_type = cleaned_data.get('location_type')
        meeting_url = cleaned_data.get('meeting_url')
        meeting_address = cleaned_data.get('meeting_address')
        
        # Validate date/time
        if scheduled_start and scheduled_end:
            if scheduled_start >= scheduled_end:
                raise ValidationError(_('End time must be after start time'))
            
            if scheduled_start <= timezone.now():
                raise ValidationError(_('Start time must be in the future'))
        
        # Validate duration
        if not duration_minutes or duration_minutes <= 0:
            raise ValidationError(_('Duration must be positive'))
        
        # Validate location-specific fields
        if location_type == 'ONLINE' and not meeting_url:
            raise ValidationError(_('Meeting URL is required for online sessions'))
        
        if location_type == 'IN_PERSON' and not meeting_address:
            raise ValidationError(_('Meeting address is required for in-person sessions'))
        
        return cleaned_data
    
    def save(self, commit=True):
        session = super().save(commit=False)
        if self.award:
            session.award = self.award
        if commit:
            session.save()
        return session


class ReviewForm(forms.ModelForm):
    """Form for submitting reviews after completed sessions"""
    
    class Meta:
        model = Review
        fields = [
            'rating', 'comment', 'communication_rating',
            'expertise_rating', 'punctuality_rating', 'would_recommend', 'is_public'
        ]
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Share your experience with this tutor...'
            }),
            'communication_rating': forms.Select(attrs={'class': 'form-control'}),
            'expertise_rating': forms.Select(attrs={'class': 'form-control'}),
            'punctuality_rating': forms.Select(attrs={'class': 'form-control'}),
            'would_recommend': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.award = kwargs.pop('award', None)
        self.reviewer = kwargs.pop('reviewer', None)
        self.reviewee = kwargs.pop('reviewee', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        rating = cleaned_data.get('rating')
        communication_rating = cleaned_data.get('communication_rating')
        expertise_rating = cleaned_data.get('expertise_rating')
        punctuality_rating = cleaned_data.get('punctuality_rating')
        
        # Validate rating fields
        if rating and (rating < 1 or rating > 5):
            raise ValidationError(_('Overall rating must be between 1 and 5'))
        
        if communication_rating and (communication_rating < 1 or communication_rating > 5):
            raise ValidationError(_('Communication rating must be between 1 and 5'))
        
        if expertise_rating and (expertise_rating < 1 or expertise_rating > 5):
            raise ValidationError(_('Expertise rating must be between 1 and 5'))
        
        if punctuality_rating and (punctuality_rating < 1 or punctuality_rating > 5):
            raise ValidationError(_('Punctuality rating must be between 1 and 5'))
        
        return cleaned_data
    
    def save(self, commit=True):
        review = super().save(commit=False)
        if self.award:
            review.award = self.award
        if self.reviewer:
            review.reviewer = self.reviewer
        if self.reviewee:
            review.reviewee = self.reviewee
        if commit:
            review.save()
        return review


class SavedRequirementForm(forms.ModelForm):
    """Form for saving requirements"""
    
    class Meta:
        model = SavedRequirement
        fields = []
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.requirement = kwargs.pop('requirement', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        saved = super().save(commit=False)
        if self.user:
            saved.user = self.user
        if self.requirement:
            saved.requirement = self.requirement
        if commit:
            saved.save()
        return saved


class FavoriteTutorForm(forms.ModelForm):
    """Form for favoriting tutors"""
    
    class Meta:
        model = FavoriteTutor
        fields = []
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        self.tutor = kwargs.pop('tutor', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        favorite = super().save(commit=False)
        if self.student:
            favorite.student = self.student
        if self.tutor:
            favorite.tutor = self.tutor
        if commit:
            favorite.save()
        return favorite


class RequirementSearchForm(forms.Form):
    """Form for searching and filtering requirements"""
    
    q = forms.CharField(
        label=_('Search'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search requirements...'
        })
    )
    
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(is_active=True),
        empty_label=_('All Subjects'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    learning_level = forms.ChoiceField(
        choices=[('', _('All Levels'))],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    budget_type = forms.ChoiceField(
        choices=[('', _('Any Budget Type'))],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    urgency_level = forms.ChoiceField(
        choices=[('', _('Any Urgency'))],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    location_type = forms.ChoiceField(
        choices=[('', _('Any Location'))],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set choices from model - hardcoded to avoid type issues
        self.fields['learning_level'].choices = [('', _('All Levels'))] + [
            ('ELEMENTARY', 'Elementary School'),
            ('MIDDLE_SCHOOL', 'Middle School'),
            ('HIGH_SCHOOL', 'High School'),
            ('UNDERGRADUATE', 'Undergraduate'),
            ('GRADUATE', 'Graduate'),
            ('PROFESSIONAL', 'Professional')
        ]
        self.fields['budget_type'].choices = [('', _('Any Budget Type'))] + [
            ('HOURLY_RATE', 'Hourly Rate'),
            ('FIXED_PRICE', 'Fixed Price'),
            ('NOT_SPECIFIED', 'Not Specified')
        ]
        self.fields['urgency_level'].choices = [('', _('Any Urgency'))] + [
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('URGENT', 'Urgent')
        ]
        self.fields['location_type'].choices = [('', _('Any Location'))] + [
            ('ONLINE', 'Online'),
            ('IN_PERSON', 'In Person'),
            ('HYBRID', 'Hybrid')
        ]
    
    min_budget = forms.DecimalField(
        label=_('Minimum Budget'),
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min budget'
        })
    )
    
    max_budget = forms.DecimalField(
        label=_('Maximum Budget'),
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max budget'
        })
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('-created_at', _('Newest First')),
            ('created_at', _('Oldest First')),
            ('-deadline', _('Urgent First')),
            ('-view_count', _('Most Viewed')),
            ('-proposal_count', _('Most Proposals')),
        ],
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-control'})
    )