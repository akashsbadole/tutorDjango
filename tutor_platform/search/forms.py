from django import forms
from django.contrib.auth import get_user_model
from django.forms import formset_factory
from accounts.models import Subject, TutorProfile
from requirements.models import Requirement

User = get_user_model()


class TutorSearchForm(forms.Form):
    """Form for searching tutors with various filters"""
    
    query = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search tutors by name, subject, or expertise...',
            'autocomplete': 'off'
        })
    )
    
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.filter(is_active=True).order_by('name'),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2-multiple',
            'data-placeholder': 'Select subjects...'
        })
    )
    
    hourly_rate_min = forms.DecimalField(
        min_value=0,
        max_value=500,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min rate',
            'step': '0.01'
        })
    )
    
    hourly_rate_max = forms.DecimalField(
        min_value=0,
        max_value=500,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max rate',
            'step': '0.01'
        })
    )
    
    availability_status = forms.ChoiceField(
        choices=[('', 'Any')] + list(TutorProfile.AvailabilityStatus.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_verified = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    is_online = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    is_featured = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    experience_years_min = forms.IntegerField(
        min_value=0,
        max_value=50,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min years'
        })
    )
    
    experience_years_max = forms.IntegerField(
        min_value=0,
        max_value=50,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max years'
        })
    )
    
    languages = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., English, Spanish, French'
        })
    )
    
    rating_min = forms.ChoiceField(
        choices=[('', 'Any')] + [(i, f'{i}+ stars') for i in range(1, 6)],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('relevance', 'Relevance'),
            ('rating', 'Rating'),
            ('hourly_rate', 'Hourly Rate'),
            ('experience', 'Experience'),
            ('created_at', 'Newest'),
        ],
        initial='relevance',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate rate range
        min_rate = cleaned_data.get('hourly_rate_min')
        max_rate = cleaned_data.get('hourly_rate_max')
        
        if min_rate and max_rate and min_rate > max_rate:
            raise forms.ValidationError(
                'Minimum hourly rate cannot be greater than maximum hourly rate.'
            )
        
        # Validate experience range
        min_exp = cleaned_data.get('experience_years_min')
        max_exp = cleaned_data.get('experience_years_max')
        
        if min_exp and max_exp and min_exp > max_exp:
            raise forms.ValidationError(
                'Minimum experience cannot be greater than maximum experience.'
            )
        
        return cleaned_data


class RequirementSearchForm(forms.Form):
    """Form for searching requirements with various filters"""
    
    query = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search requirements by title or description...',
            'autocomplete': 'off'
        })
    )
    
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(is_active=True).order_by('name'),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'data-placeholder': 'Select subject...'
        })
    )
    
    learning_level = forms.ChoiceField(
        choices=[('', 'Any')] + [('ELEMENTARY', 'Elementary School'), ('MIDDLE_SCHOOL', 'Middle School'), ('HIGH_SCHOOL', 'High School'), ('UNDERGRADUATE', 'Undergraduate'), ('GRADUATE', 'Graduate'), ('PROFESSIONAL', 'Professional')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    budget_min = forms.DecimalField(
        min_value=0,
        max_value=10000,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min budget',
            'step': '0.01'
        })
    )
    
    budget_max = forms.DecimalField(
        min_value=0,
        max_value=10000,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max budget',
            'step': '0.01'
        })
    )
    
    budget_type = forms.ChoiceField(
        choices=[('', 'Any')] + list(Requirement.BudgetType.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    urgency_level = forms.ChoiceField(
        choices=[('', 'Any')] + list(Requirement.UrgencyLevel.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    location_type = forms.ChoiceField(
        choices=[('', 'Any')] + list(Requirement.LocationType.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    deadline_days = forms.IntegerField(
        min_value=0,
        max_value=365,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Days until deadline'
        })
    )
    
    is_featured = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('relevance', 'Relevance'),
            ('created_at', 'Newest'),
            ('deadline', 'Deadline'),
            ('budget', 'Budget'),
            ('urgency', 'Urgency'),
        ],
        initial='created_at',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate budget range
        min_budget = cleaned_data.get('budget_min')
        max_budget = cleaned_data.get('budget_max')
        
        if min_budget and max_budget and min_budget > max_budget:
            raise forms.ValidationError(
                'Minimum budget cannot be greater than maximum budget.'
            )
        
        return cleaned_data


class AdvancedSearchForm(forms.Form):
    """Advanced search form with complex filtering options"""
    
    query = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search across all content...',
            'autocomplete': 'off'
        })
    )
    
    content_types = forms.MultipleChoiceField(
        choices=[
            ('tutor', 'Tutors'),
            ('requirement', 'Requirements'),
            ('message', 'Messages'),
            ('payment', 'Payments'),
        ],
        initial=['tutor', 'requirement'],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
    
    date_range = forms.ChoiceField(
        choices=[
            ('', 'Any time'),
            ('1', 'Last 24 hours'),
            ('7', 'Last week'),
            ('30', 'Last month'),
            ('90', 'Last 3 months'),
            ('365', 'Last year'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    user_type = forms.ChoiceField(
        choices=[
            ('', 'Any'),
            ('STUDENT', 'Students'),
            ('TUTOR', 'Tutors'),
            ('ADMIN', 'Administrators'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    is_verified = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('relevance', 'Relevance'),
            ('created_at', 'Date'),
            ('updated_at', 'Last updated'),
            ('title', 'Title'),
        ],
        initial='relevance',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    results_per_page = forms.ChoiceField(
        choices=[
            ('10', '10 results'),
            ('20', '20 results'),
            ('50', '50 results'),
            ('100', '100 results'),
        ],
        initial='20',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    include_archived = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class SearchFilterForm(forms.Form):
    """Form for saving search filters"""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter name...'
        })
    )
    
    search_type = forms.ChoiceField(
        choices=[
            ('GLOBAL', 'Global Search'),
            ('TUTOR', 'Tutor Search'),
            ('REQUIREMENT', 'Requirement Search'),
            ('MESSAGE', 'Message Search'),
            ('PAYMENT', 'Payment Search'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_default = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    is_public = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    description = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional description...'
        })
    )


class MessageSearchForm(forms.Form):
    """Form for searching messages"""
    
    query = forms.CharField(
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search messages...',
            'autocomplete': 'off'
        })
    )
    
    conversation_type = forms.ChoiceField(
        choices=[
            ('', 'All conversations'),
            ('sent', 'Sent messages'),
            ('received', 'Received messages'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    has_attachments = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    is_unread = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('relevance', 'Relevance'),
            ('created_at', 'Date'),
            ('sender', 'Sender'),
        ],
        initial='created_at',
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class PaymentSearchForm(forms.Form):
    """Form for searching payments"""
    
    query = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search payments...',
            'autocomplete': 'off'
        })
    )
    
    payment_type = forms.ChoiceField(
        choices=[('', 'Any')] + list([
            ('FULL_PAYMENT', 'Full Payment'),
            ('MILESTONE', 'Milestone'),
            ('SESSION', 'Session'),
            ('REFUND', 'Refund'),
        ]),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[('', 'Any')] + list([
            ('PENDING', 'Pending'),
            ('PROCESSING', 'Processing'),
            ('COMPLETED', 'Completed'),
            ('FAILED', 'Failed'),
            ('REFUNDED', 'Refunded'),
        ]),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    amount_min = forms.DecimalField(
        min_value=0,
        max_value=10000,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min amount',
            'step': '0.01'
        })
    )
    
    amount_max = forms.DecimalField(
        min_value=0,
        max_value=10000,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max amount',
            'step': '0.01'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    currency = forms.ChoiceField(
        choices=[('', 'Any')] + [('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('relevance', 'Relevance'),
            ('created_at', 'Date'),
            ('amount', 'Amount'),
            ('status', 'Status'),
        ],
        initial='created_at',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate amount range
        min_amount = cleaned_data.get('amount_min')
        max_amount = cleaned_data.get('amount_max')
        
        if min_amount and max_amount and min_amount > max_amount:
            raise forms.ValidationError(
                'Minimum amount cannot be greater than maximum amount.'
            )
        
        # Validate date range
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError(
                'Start date cannot be after end date.'
            )
        
        return cleaned_data


class ExportSearchResultsForm(forms.Form):
    """Form for exporting search results"""
    
    export_format = forms.ChoiceField(
        choices=[
            ('csv', 'CSV'),
            ('excel', 'Excel'),
            ('json', 'JSON'),
            ('pdf', 'PDF'),
        ],
        initial='csv',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    include_fields = forms.MultipleChoiceField(
        choices=[
            ('title', 'Title'),
            ('description', 'Description'),
            ('url', 'URL'),
            ('relevance_score', 'Relevance Score'),
            ('created_at', 'Created Date'),
            ('metadata', 'Metadata'),
        ],
        initial=['title', 'description', 'url', 'created_at'],
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        })
    )
    
    max_results = forms.IntegerField(
        min_value=1,
        max_value=1000,
        initial=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 1000
        })
    )
    
    include_highlights = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )