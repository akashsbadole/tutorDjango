"""
Forms for payment processing and financial management.
"""

from decimal import Decimal
from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Payment, PaymentMethod, Payout, Refund, Transaction
)
from .utils import calculate_processing_fees


class PaymentMethodForm(forms.ModelForm):
    """Form for adding/updating payment methods."""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'method_type', 'display_name', 'is_default'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['method_type'].widget = forms.Select(
            choices=PaymentMethod.MethodType.choices
        )
        
        # Add gateway-specific fields based on method type
        if self.instance and self.instance.pk:
            method_type = self.instance.method_type
        else:
            method_type = self.data.get('method_type') if self.data else None
        
        self.add_gateway_fields(method_type)
    
    def add_gateway_fields(self, method_type):
        """Add gateway-specific fields based on payment method type."""
        # Remove any existing gateway fields
        for field_name in list(self.fields.keys()):
            if field_name.startswith('gateway_'):
                self.fields.pop(field_name, None)
        
        if not method_type:
            return
        
        if method_type == PaymentMethod.MethodType.STRIPE:
            self.fields['gateway_stripe_token'] = forms.CharField(
                label='Stripe Token',
                widget=forms.HiddenInput(),
                required=False
            )
            self.fields['gateway_card_last4'] = forms.CharField(
                label='Last 4 Digits',
                max_length=4,
                required=True,
                widget=forms.TextInput(attrs={'placeholder': '1234'})
            )
            self.fields['gateway_card_brand'] = forms.ChoiceField(
                label='Card Brand',
                choices=[
                    ('visa', 'Visa'),
                    ('mastercard', 'Mastercard'),
                    ('amex', 'American Express'),
                    ('discover', 'Discover')
                ],
                required=True
            )
            self.fields['gateway_card_exp_month'] = forms.IntegerField(
                label='Expiry Month',
                min_value=1,
                max_value=12,
                required=True
            )
            self.fields['gateway_card_exp_year'] = forms.IntegerField(
                label='Expiry Year',
                min_value=2023,
                max_value=2050,
                required=True
            )
        
        elif method_type == PaymentMethod.MethodType.PAYPAL:
            self.fields['gateway_paypal_email'] = forms.EmailField(
                label='PayPal Email',
                required=True
            )
            
        elif method_type == PaymentMethod.MethodType.PAYPAL_BALANCE:
            self.fields['gateway_paypal_account_id'] = forms.CharField(
                label='PayPal Account ID',
                max_length=100,
                required=True,
                widget=forms.TextInput(attrs={'readonly': True})
            )
            
        elif method_type == PaymentMethod.MethodType.PAYPAL_CARD:
            self.fields['gateway_card_last4'] = forms.CharField(
                label='Last 4 Digits',
                max_length=4,
                required=True,
                widget=forms.TextInput(attrs={'placeholder': '1234'})
            )
            self.fields['gateway_card_brand'] = forms.ChoiceField(
                label='Card Brand',
                choices=[
                    ('visa', 'Visa'),
                    ('mastercard', 'Mastercard'),
                    ('amex', 'American Express'),
                    ('discover', 'Discover')
                ],
                required=True
            )
            self.fields['gateway_paypal_card_id'] = forms.CharField(
                label='PayPal Card ID',
                max_length=100,
                required=True,
                widget=forms.HiddenInput()
            )
        
        elif method_type == PaymentMethod.MethodType.BANK_TRANSFER:
            self.fields['gateway_bank_name'] = forms.CharField(
                label='Bank Name',
                max_length=100,
                required=True
            )
            self.fields['gateway_account_number'] = forms.CharField(
                label='Account Number',
                max_length=50,
                required=True,
                widget=forms.PasswordInput(render_value=True)
            )
            self.fields['gateway_routing_number'] = forms.CharField(
                label='Routing Number',
                max_length=50,
                required=True
            )
            self.fields['gateway_account_holder'] = forms.CharField(
                label='Account Holder Name',
                max_length=100,
                required=True
            )
    
    def clean(self):
        cleaned_data = super().clean()
        method_type = cleaned_data.get('method_type')
        
        # Validate gateway-specific fields
        if method_type == PaymentMethod.MethodType.STRIPE:
            card_last4 = cleaned_data.get('gateway_card_last4')
            if not card_last4 or len(card_last4) != 4:
                raise ValidationError({
                    'gateway_card_last4': 'Please enter the last 4 digits of your card.'
                })
        
        elif method_type == PaymentMethod.MethodType.PAYPAL:
            paypal_email = cleaned_data.get('gateway_paypal_email')
            if not paypal_email:
                raise ValidationError({
                    'gateway_paypal_email': 'Please enter your PayPal email address.'
                })
                
        elif method_type == PaymentMethod.MethodType.PAYPAL_BALANCE:
            paypal_account_id = cleaned_data.get('gateway_paypal_account_id')
            if not paypal_account_id:
                raise ValidationError({
                    'gateway_paypal_account_id': 'PayPal account ID is required.'
                })
                
        elif method_type == PaymentMethod.MethodType.PAYPAL_CARD:
            card_last4 = cleaned_data.get('gateway_card_last4')
            if not card_last4 or len(card_last4) != 4:
                raise ValidationError({
                    'gateway_card_last4': 'Please enter the last 4 digits of your card.'
                })
        
        elif method_type == PaymentMethod.MethodType.BANK_TRANSFER:
            required_fields = [
                'gateway_bank_name', 'gateway_account_number',
                'gateway_routing_number', 'gateway_account_holder'
            ]
            for field in required_fields:
                if not cleaned_data.get(field):
                    raise ValidationError({
                        field: 'This field is required for bank transfer.'
                    })
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Store gateway-specific data in method_details
        method_details = {}
        method_type = self.cleaned_data.get('method_type')
        
        if method_type == PaymentMethod.MethodType.STRIPE:
            method_details = {
                'card_last4': self.cleaned_data.get('gateway_card_last4'),
                'card_brand': self.cleaned_data.get('gateway_card_brand'),
                'card_exp_month': self.cleaned_data.get('gateway_card_exp_month'),
                'card_exp_year': self.cleaned_data.get('gateway_card_exp_year'),
                'stripe_token': self.cleaned_data.get('gateway_stripe_token'),
            }
        
        elif method_type == PaymentMethod.MethodType.PAYPAL:
            method_details = {
                'paypal_email': self.cleaned_data.get('gateway_paypal_email'),
            }
            
        elif method_type == PaymentMethod.MethodType.PAYPAL_BALANCE:
            method_details = {
                'paypal_account_id': self.cleaned_data.get('gateway_paypal_account_id'),
            }
            
        elif method_type == PaymentMethod.MethodType.PAYPAL_CARD:
            method_details = {
                'card_last4': self.cleaned_data.get('gateway_card_last4'),
                'card_brand': self.cleaned_data.get('gateway_card_brand'),
                'paypal_card_id': self.cleaned_data.get('gateway_paypal_card_id'),
            }
        
        elif method_type == PaymentMethod.MethodType.BANK_TRANSFER:
            method_details = {
                'bank_name': self.cleaned_data.get('gateway_bank_name'),
                'account_number': self.cleaned_data.get('gateway_account_number'),
                'routing_number': self.cleaned_data.get('gateway_routing_number'),
                'account_holder': self.cleaned_data.get('gateway_account_holder'),
            }
        
        instance.method_details = method_details
        
        if commit:
            instance.save()
        return instance


class PayoutRequestForm(forms.Form):
    """Form for requesting a payout."""
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Get user's available payment methods
            payment_methods = PaymentMethod.objects.filter(
                user=self.user,
                is_active=True,
                is_verified=True
            )
            
            # Add payment_method field dynamically
            self.fields['payment_method'] = forms.ModelChoiceField(
                label='Payout Method',
                queryset=payment_methods,
                required=True
            )
            
            # Get user's available balance
            from .utils import get_user_balance_summary
            balance_summary = get_user_balance_summary(self.user)
            available_balance = balance_summary['current_balance']
            
            # Add amount, processing_fees, and net_amount fields dynamically
            self.fields['amount'] = forms.DecimalField(
                label='Payout Amount',
                max_digits=10,
                decimal_places=2,
                min_value=Decimal('1.00'),
                widget=forms.NumberInput(attrs={'step': '0.01'})
            )
            
            self.fields['processing_fees'] = forms.DecimalField(
                label='Processing Fees',
                max_digits=10,
                decimal_places=2,
                initial=Decimal('0.00'),
                widget=forms.NumberInput(attrs={'step': '0.01', 'readonly': True})
            )
            
            self.fields['net_amount'] = forms.DecimalField(
                label='Net Amount',
                max_digits=10,
                decimal_places=2,
                widget=forms.NumberInput(attrs={'step': '0.01', 'readonly': True})
            )
            
            # Set max amount
            self.fields['amount'].widget.attrs.update({
                'max': str(available_balance),
                'data-balance': str(available_balance)
            })
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        
        if not amount or amount <= 0:
            raise ValidationError('Payout amount must be positive.')
        
        # Check available balance
        if self.user:
            from .utils import get_user_balance_summary
            balance_summary = get_user_balance_summary(self.user)
            available_balance = balance_summary['current_balance']
            
            if amount and amount > available_balance:
                raise ValidationError(
                    f'Insufficient balance. Available: {available_balance}'
                )
        
        return amount
    
    def clean_payment_method(self):
        payment_method = self.cleaned_data.get('payment_method')
        
        if not payment_method:
            raise ValidationError('Please select a payout method.')
        
        return payment_method
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount', Decimal('0.00'))
        payment_method = cleaned_data.get('payment_method')
        
        if amount and payment_method:
            # Calculate processing fees based on method
            processing_fees = calculate_processing_fees(amount)
            net_amount = amount - processing_fees
            
            # Update form fields
            self.data = self.data.copy()
            self.data['processing_fees'] = str(processing_fees)
            self.data['net_amount'] = str(net_amount)
            
            # Store calculated values
            cleaned_data['processing_fees'] = processing_fees
            cleaned_data['net_amount'] = net_amount
        
        return cleaned_data


class RefundRequestForm(forms.Form):
    """Form for requesting a refund."""
    
    def __init__(self, *args, **kwargs):
        self.payment = kwargs.pop('payment', None)
        super().__init__(*args, **kwargs)
        
        if self.payment:
            # Set max amount to payment amount
            self.fields['amount'] = forms.DecimalField(
                label='Refund Amount',
                max_digits=10,
                decimal_places=2,
                min_value=Decimal('0.01'),
                widget=forms.NumberInput(attrs={'step': '0.01'})
            )
            
            self.fields['amount'].widget.attrs.update({
                'max': str(self.payment.amount),
                'data-max': str(self.payment.amount)
            })
            
            # Get payer's payment methods
            payment_methods = PaymentMethod.objects.filter(
                user=self.payment.payer,
                is_active=True,
                is_verified=True
            )
            
            # Add refund_method field dynamically
            self.fields['refund_method'] = forms.ModelChoiceField(
                label='Refund Method',
                queryset=payment_methods,
                required=True
            )
    
    amount = forms.DecimalField(
        label='Refund Amount',
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )
    
    reason = forms.ChoiceField(
        label='Refund Reason',
        choices=[
            ('', 'Select a reason'),
            ('service_not_as_described', 'Service not as described'),
            ('tutor_unresponsive', 'Tutor unresponsive'),
            ('technical_issues', 'Technical issues'),
            ('schedule_conflict', 'Schedule conflict'),
            ('other', 'Other')
        ],
        required=True
    )
    
    detailed_reason = forms.CharField(
        label='Detailed Reason',
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        
        if not amount or amount <= 0:
            raise ValidationError('Refund amount must be positive.')
        
        # Check against payment amount
        if self.payment and amount > self.payment.amount:
            raise ValidationError(
                f'Refund amount cannot exceed payment amount of {self.payment.amount}'
            )
        
        return amount
    
    def clean_detailed_reason(self):
        reason = self.cleaned_data.get('reason')
        detailed_reason = self.cleaned_data.get('detailed_reason')
        
        if reason == 'other' and not detailed_reason:
            raise ValidationError(
                'Please provide a detailed reason for "Other".'
            )
        
        return detailed_reason
    
    def clean_refund_method(self):
        refund_method = self.cleaned_data.get('refund_method')
        
        if not refund_method:
            raise ValidationError('Please select a refund method.')
        
        return refund_method
    
    def get_refund_reason(self):
        """Get the complete refund reason."""
        reason = self.cleaned_data.get('reason', '')
        detailed_reason = self.cleaned_data.get('detailed_reason', '')
        
        if reason == 'other' and detailed_reason:
            return detailed_reason
        
        choices_dict = dict(self.fields['reason'].choices)
        return choices_dict.get(reason, reason)


class PaymentSearchForm(forms.Form):
    """Form for searching payments."""
    
    status = forms.ChoiceField(
        label='Status',
        choices=[('', 'All Statuses')] + list(Payment.PaymentStatus.choices),
        required=False
    )
    
    payment_type = forms.ChoiceField(
        label='Payment Type',
        choices=[('', 'All Types')] + list(Payment.PaymentType.choices),
        required=False
    )
    
    date_from = forms.DateField(
        label='From Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    
    date_to = forms.DateField(
        label='To Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    
    amount_min = forms.DecimalField(
        label='Min Amount',
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )
    
    amount_max = forms.DecimalField(
        label='Max Amount',
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate date range
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError('From date cannot be after to date.')
        
        # Validate amount range
        amount_min = cleaned_data.get('amount_min')
        amount_max = cleaned_data.get('amount_max')
        
        if amount_min and amount_max and amount_min > amount_max:
            raise ValidationError('Min amount cannot be greater than max amount.')
        
        return cleaned_data


class TransactionSearchForm(forms.Form):
    """Form for searching transactions."""
    
    transaction_type = forms.ChoiceField(
        label='Transaction Type',
        choices=[('', 'All Types')] + list(Transaction.TransactionType.choices),
        required=False
    )
    
    date_from = forms.DateField(
        label='From Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    
    date_to = forms.DateField(
        label='To Date',
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate date range
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise ValidationError('From date cannot be after to date.')
        
        return cleaned_data


class DepositForm(forms.Form):
    """Form for depositing funds to escrow account."""
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Get user's available payment methods
            payment_methods = PaymentMethod.objects.filter(
                user=self.user,
                is_active=True,
                is_verified=True
            )
            
            # Add payment_method field dynamically
            self.fields['payment_method'] = forms.ModelChoiceField(
                label='Payment Method',
                queryset=payment_methods,
                required=True
            )
    
    amount = forms.DecimalField(
        label='Deposit Amount',
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('1.00'),
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )
    
    description = forms.CharField(
        label='Description',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Optional description for this deposit'})
    )
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        
        if not amount or amount <= 0:
            raise ValidationError('Deposit amount must be positive.')
        
        # Check minimum deposit amount
        if amount < Decimal('1.00'):
            raise ValidationError('Minimum deposit amount is $1.00.')
        
        return amount
    
    def clean_payment_method(self):
        payment_method = self.cleaned_data.get('payment_method')
        
        if not payment_method:
            raise ValidationError('Please select a payment method.')
        
        return payment_method


class WithdrawalForm(forms.Form):
    """Form for withdrawing funds from escrow account."""
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Get user's available balance
            from .utils import get_user_balance_summary
            balance_summary = get_user_balance_summary(self.user)
            available_balance = balance_summary['current_balance']
            
            # Get user's available payment methods
            payment_methods = PaymentMethod.objects.filter(
                user=self.user,
                is_active=True,
                is_verified=True
            )
            
            # Add payment_method field dynamically
            self.fields['payment_method'] = forms.ModelChoiceField(
                label='Withdrawal Method',
                queryset=payment_methods,
                required=True
            )
            
            # Set max amount
            self.fields['amount'].widget.attrs.update({
                'max': str(available_balance),
                'data-balance': str(available_balance)
            })
    
    amount = forms.DecimalField(
        label='Withdrawal Amount',
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('1.00'),
        widget=forms.NumberInput(attrs={'step': '0.01'})
    )
    
    description = forms.CharField(
        label='Description',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Optional description for this withdrawal'})
    )
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        
        if not amount or amount <= 0:
            raise ValidationError('Withdrawal amount must be positive.')
        
        # Check available balance
        if self.user:
            from .utils import get_user_balance_summary
            balance_summary = get_user_balance_summary(self.user)
            available_balance = balance_summary['current_balance']
            
            if amount and amount > available_balance:
                raise ValidationError(
                    f'Insufficient balance. Available: {available_balance}'
                )
        
        return amount
    
    def clean_payment_method(self):
        payment_method = self.cleaned_data.get('payment_method')
        
        if not payment_method:
            raise ValidationError('Please select a withdrawal method.')
        
        return payment_method