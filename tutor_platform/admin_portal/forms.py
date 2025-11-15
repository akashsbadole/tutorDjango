"""
Django Tutor Platform Admin Portal Forms

This module contains forms for the admin portal including profile management,
bulk actions, and system settings.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q

# Import models
from accounts.models import User, TutorProfile, StudentProfile
from requirements.models import Requirement
from .models import AdminProfile, SystemSetting, AdminRole

User = get_user_model()


class AdminProfileForm(forms.ModelForm):
    """Form for managing admin profiles"""
    
    class Meta:
        model = AdminProfile
        fields = ['role', 'department', 'phone', 'is_super_admin']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'is_super_admin': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = AdminRole.objects.filter(is_active=True)
        self.fields['role'].empty_label = _("Select a role")
        
        # Add placeholders
        self.fields['department'].widget.attrs.update({
            'placeholder': _('Enter department name')
        })
        self.fields['phone'].widget.attrs.update({
            'placeholder': _('Enter phone number')
        })


class SystemSettingForm(forms.ModelForm):
    """Form for managing system settings"""
    
    class Meta:
        model = SystemSetting
        fields = ['key', 'value', 'description', 'is_public']
        widgets = {
            'key': forms.TextInput(attrs={'class': 'form-control'}),
            'value': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add placeholders
        self.fields['key'].widget.attrs.update({
            'placeholder': _('Enter setting key')
        })
        self.fields['value'].widget.attrs.update({
            'placeholder': _('Enter setting value')
        })
        self.fields['description'].widget.attrs.update({
            'placeholder': _('Enter description')
        })
    
    def clean_key(self):
        """Validate key format"""
        key = self.cleaned_data['key']
        if not key.replace('_', '').replace('-', '').isalnum():
            raise ValidationError(
                _('Key can only contain alphanumeric characters, underscores, and hyphens')
            )
        
        # Check for uniqueness (exclude current instance if editing)
        queryset = SystemSetting.objects.filter(key=key)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError(_('This key already exists'))
        
        return key.upper()  # Store keys in uppercase for consistency


class BulkActionForm(forms.Form):
    """Form for bulk actions on users and other objects"""
    
    ACTION_CHOICES = [
        ('', _('Select an action')),
        ('activate', _('Activate')),
        ('deactivate', _('Deactivate')),
        ('delete', _('Delete')),
        ('send_notification', _('Send Notification')),
        ('export', _('Export Data')),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    notification_message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Enter notification message')
        }),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        notification_message = cleaned_data.get('notification_message')
        
        if action == 'send_notification' and not notification_message:
            raise ValidationError({
                'notification_message': _('Notification message is required when sending notifications')
            })
        
        return cleaned_data


class DataExportForm(forms.Form):
    """Form for data export"""
    
    EXPORT_TYPES = [
        ('USERS', _('Users')),
        ('REQUIREMENTS', _('Requirements')),
        ('PAYMENTS', _('Payments')),
        ('MESSAGES', _('Messages')),
        ('NOTIFICATIONS', _('Notifications')),
        ('SESSIONS', _('Sessions')),
        ('TRANSACTIONS', _('Transactions')),
        ('REPORTS', _('Reports')),
    ]
    
    export_type = forms.ChoiceField(
        choices=EXPORT_TYPES,
        required=True,
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
    
    format = forms.ChoiceField(
        choices=[
            ('csv', _('CSV')),
            ('xlsx', _('Excel')),
            ('json', _('JSON')),
        ],
        initial='csv',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    include_deleted = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError(_('Start date cannot be after end date'))
        
        return cleaned_data


class UserSearchForm(forms.Form):
    """Form for searching and filtering users"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by username, email, or name')
        })
    )
    
    user_type = forms.ChoiceField(
        choices=[
            ('', _('All Users')),
            ('tutor', _('Tutors')),
            ('student', _('Students')),
            ('admin', _('Admins')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', _('All Status')),
            ('active', _('Active')),
            ('inactive', _('Inactive')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_joined_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_joined_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class RequirementSearchForm(forms.Form):
    """Form for searching and filtering requirements"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by title or description')
        })
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', _('All Status')),
            ('OPEN', _('Open')),
            ('IN_PROGRESS', _('In Progress')),
            ('COMPLETED', _('Completed')),
            ('CANCELLED', _('Cancelled')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    subject = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter subject')
        })
    )
    
    budget_min = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Minimum budget')
        })
    )
    
    budget_max = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Maximum budget')
        })
    )
    
    created_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    created_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        budget_min = cleaned_data.get('budget_min')
        budget_max = cleaned_data.get('budget_max')
        
        if budget_min and budget_max and budget_min > budget_max:
            raise ValidationError(_('Minimum budget cannot be greater than maximum budget'))
        
        return cleaned_data


class PaymentSearchForm(forms.Form):
    """Form for searching and filtering payments"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by transaction ID or user')
        })
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', _('All Status')),
            ('PENDING', _('Pending')),
            ('COMPLETED', _('Completed')),
            ('FAILED', _('Failed')),
            ('REFUNDED', _('Refunded')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    payment_method = forms.ChoiceField(
        choices=[
            ('', _('All Methods')),
            ('STRIPE', _('Stripe')),
            ('PAYPAL', _('PayPal')),
            ('BANK_TRANSFER', _('Bank Transfer')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    amount_min = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Minimum amount')
        })
    )
    
    amount_max = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Maximum amount')
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
    
    def clean(self):
        cleaned_data = super().clean()
        amount_min = cleaned_data.get('amount_min')
        amount_max = cleaned_data.get('amount_max')
        
        if amount_min and amount_max and amount_min > amount_max:
            raise ValidationError(_('Minimum amount cannot be greater than maximum amount'))
        
        return cleaned_data


class AdminRoleForm(forms.ModelForm):
    """Form for managing admin roles"""
    
    class Meta:
        model = AdminRole
        fields = ['name', 'description', 'permissions', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'permissions': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add placeholders
        self.fields['name'].widget.attrs.update({
            'placeholder': _('Enter role name')
        })
        self.fields['description'].widget.attrs.update({
            'placeholder': _('Enter role description')
        })
        self.fields['permissions'].widget.attrs.update({
            'placeholder': _('Enter permissions in JSON format')
        })
        
        # Add help text for permissions field
        self.fields['permissions'].help_text = _(
            'Enter permissions in JSON format. Example: {"user_management": true, "payment_management": false}'
        )
    
    def clean_permissions(self):
        """Validate permissions JSON"""
        permissions = self.cleaned_data['permissions']
        
        if permissions:
            import json
            try:
                json.loads(permissions)
            except json.JSONDecodeError:
                raise ValidationError(_('Invalid JSON format for permissions'))
        
        return permissions


class MessageSearchForm(forms.Form):
    """Form for searching and filtering messages"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by content or sender')
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
    
    has_attachments = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError(_('Start date cannot be after end date'))
        
        return cleaned_data