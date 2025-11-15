from decimal import Decimal
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import PayPalAccount, PayPalSubscription

User = get_user_model()


class PayPalPaymentForm(forms.Form):
    """Form for initiating PayPal payments"""
    
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount',
            'step': '0.01'
        }),
        help_text=_('Enter the payment amount')
    )
    
    currency = forms.ChoiceField(
        choices=[
            ('USD', 'USD - US Dollar'),
            ('EUR', 'EUR - Euro'),
            ('GBP', 'GBP - British Pound'),
            ('CAD', 'CAD - Canadian Dollar'),
            ('AUD', 'AUD - Australian Dollar'),
        ],
        initial='USD',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text=_('Select payment currency')
    )
    
    description = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Payment description (optional)'
        }),
        help_text=_('Optional description for the payment')
    )
    
    # Hidden fields for payment processing
    award_id = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    payment_type = forms.ChoiceField(
        choices=[
            ('FULL_PAYMENT', 'Full Payment'),
            ('MILESTONE', 'Milestone'),
            ('SESSION', 'Session'),
        ],
        initial='FULL_PAYMENT',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text=_('Type of payment')
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Check if user has PayPal accounts
        if self.user:
            has_paypal_accounts = PayPalAccount.objects.filter(
                user=self.user,
                is_active=True
            ).exists()
            
            if not has_paypal_accounts:
                self.add_error(None, _('You must link a PayPal account before making payments.'))

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise ValidationError(_('Amount must be greater than 0'))
        return amount


class PayPalPayoutForm(forms.Form):
    """Form for tutor withdrawals via PayPal"""
    
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter payout amount',
            'step': '0.01'
        }),
        help_text=_('Enter the amount to withdraw')
    )
    
    currency = forms.ChoiceField(
        choices=[
            ('USD', 'USD - US Dollar'),
            ('EUR', 'EUR - Euro'),
            ('GBP', 'GBP - British Pound'),
            ('CAD', 'CAD - Canadian Dollar'),
            ('AUD', 'AUD - Australian Dollar'),
        ],
        initial='USD',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text=_('Select payout currency')
    )
    
    note = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional note for the payout'
        }),
        help_text=_('Optional note for this payout')
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Check if user is a tutor
        if self.user and hasattr(self.user, 'user_type'):
            if self.user.user_type != 'TUTOR':
                self.add_error(None, _('Only tutors can request payouts.'))
        
        # Check if user has PayPal accounts
        if self.user:
            has_paypal_accounts = PayPalAccount.objects.filter(
                user=self.user,
                is_active=True
            ).exists()
            
            if not has_paypal_accounts:
                self.add_error(None, _('You must link a PayPal account before requesting payouts.'))

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise ValidationError(_('Amount must be greater than 0'))
        return amount


class PayPalSubscriptionForm(forms.Form):
    """Form for creating PayPal subscriptions"""
    
    plan_id = forms.ChoiceField(
        choices=[
            ('P-1ML12345678901234', 'Basic Plan - $9.99/month'),
            ('P-2ML12345678901234', 'Premium Plan - $19.99/month'),
            ('P-3ML12345678901234', 'Professional Plan - $49.99/month'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text=_('Select a subscription plan')
    )
    
    currency = forms.ChoiceField(
        choices=[
            ('USD', 'USD - US Dollar'),
            ('EUR', 'EUR - Euro'),
            ('GBP', 'GBP - British Pound'),
        ],
        initial='USD',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text=_('Select subscription currency')
    )
    
    trial_period_days = forms.IntegerField(
        min_value=0,
        max_value=365,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Trial period in days'
        }),
        help_text=_('Trial period in days (0 for no trial)')
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Check if user has PayPal accounts
        if self.user:
            has_paypal_accounts = PayPalAccount.objects.filter(
                user=self.user,
                is_active=True
            ).exists()
            
            if not has_paypal_accounts:
                self.add_error(None, _('You must link a PayPal account before creating subscriptions.'))

    def clean_trial_period_days(self):
        trial_days = self.cleaned_data.get('trial_period_days')
        if trial_days is not None and trial_days < 0:
            raise ValidationError(_('Trial period cannot be negative'))
        return trial_days


class PayPalAccountForm(forms.ModelForm):
    """Form for linking PayPal accounts"""
    
    class Meta:
        model = PayPalAccount
        fields = [
            'paypal_email',
            'paypal_user_id',
            'account_type',
            'verification_status',
            'is_primary'
        ]
        widgets = {
            'paypal_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your-paypal-email@example.com'
            }),
            'paypal_user_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'PayPal User ID'
            }),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'verification_status': forms.Select(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make verification_status read-only for existing accounts
        if self.instance and self.instance.pk:
            self.fields['verification_status'].widget = forms.Select(
                attrs={'class': 'form-control', 'readonly': 'readonly'}
            )
            self.fields['paypal_user_id'].widget = forms.TextInput(
                attrs={'class': 'form-control', 'readonly': 'readonly'}
            )

    def clean_paypal_email(self):
        email = self.cleaned_data.get('paypal_email')
        
        # Check if email is already linked to another account
        if self.user:
            existing_account = PayPalAccount.objects.filter(
                paypal_email=email,
                user=self.user
            ).exclude(pk=self.instance.pk if self.instance.pk else None).first()
            
            if existing_account:
                raise ValidationError(_('This PayPal email is already linked to your account.'))
        
        return email

    def clean_paypal_user_id(self):
        user_id = self.cleaned_data.get('paypal_user_id')
        
        # Check if user ID is already linked to another account
        if self.user and user_id:
            existing_account = PayPalAccount.objects.filter(
                paypal_user_id=user_id,
                user=self.user
            ).exclude(pk=self.instance.pk if self.instance.pk else None).first()
            
            if existing_account:
                raise ValidationError(_('This PayPal user ID is already linked to your account.'))
        
        return user_id

    def save(self, commit=True):
        account = super().save(commit=False)
        
        if self.user:
            account.user = self.user
        
        if commit:
            account.save()
        
        return account


class PayPalAccountVerificationForm(forms.Form):
    """Form for verifying PayPal accounts"""
    
    verification_code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter verification code'
        }),
        help_text=_('Enter the verification code sent to your PayPal email')
    )
    
    paypal_account_id = forms.CharField(widget=forms.HiddenInput())
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean_verification_code(self):
        code = self.cleaned_data.get('verification_code')
        if not code or len(code) < 6:
            raise ValidationError(_('Invalid verification code'))
        return code


class PayPalRefundForm(forms.Form):
    """Form for processing PayPal refunds"""
    
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Refund amount',
            'step': '0.01'
        }),
        help_text=_('Enter the refund amount')
    )
    
    reason = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for refund'
        }),
        help_text=_('Provide a reason for the refund')
    )
    
    transaction_id = forms.CharField(widget=forms.HiddenInput())
    
    def __init__(self, *args, **kwargs):
        self.max_amount = kwargs.pop('max_amount', None)
        super().__init__(*args, **kwargs)
        
        if self.max_amount:
            self.fields['amount'].widget.attrs['max'] = str(self.max_amount)
            self.fields['amount'].help_text = _(
                f'Enter refund amount (maximum: {self.max_amount})'
            )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        
        if amount is not None and amount <= 0:
            raise ValidationError(_('Amount must be greater than 0'))
        
        if self.max_amount and amount is not None and amount > self.max_amount:
            raise ValidationError(
                _('Refund amount cannot exceed the original transaction amount')
            )
        
        return amount


class PayPalDisputeResponseForm(forms.Form):
    """Form for responding to PayPal disputes"""
    
    response = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Enter your response to the dispute'
        }),
        help_text=_('Provide your response to resolve the dispute')
    )
    
    evidence_files = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        }),
        help_text=_('Upload evidence files to support your response')
    )
    
    dispute_id = forms.CharField(widget=forms.HiddenInput())
    
    def clean_response(self):
        response = self.cleaned_data.get('response')
        if not response or len(response.strip()) < 10:
            raise ValidationError(_('Response must be at least 10 characters long'))
        return response

    def clean_evidence_files(self):
        files = self.cleaned_data.get('evidence_files')
        
        if files:
            # Check file size (max 5MB per file)
            if files.size > 5 * 1024 * 1024:
                raise ValidationError(_('File size cannot exceed 5MB'))
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'application/pdf', 'text/plain']
            if files.content_type not in allowed_types:
                raise ValidationError(
                    _('Only JPEG, PNG, PDF, and text files are allowed')
                )
        
        return files


class PayPalSubscriptionCancelForm(forms.Form):
    """Form for cancelling PayPal subscriptions"""
    
    reason = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for cancellation (optional)'
        }),
        help_text=_('Optional reason for cancelling the subscription')
    )
    
    subscription_id = forms.CharField(widget=forms.HiddenInput())
    
    def clean_reason(self):
        reason = self.cleaned_data.get('reason')
        if reason and len(reason.strip()) < 5:
            raise ValidationError(_('Reason must be at least 5 characters long if provided'))
        return reason