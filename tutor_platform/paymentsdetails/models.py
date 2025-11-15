import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, Q
from .managers import (
    PaymentMethodManager, EscrowAccountManager, PaymentManager,
    TransactionManager, CommissionManager, RefundManager, PayoutManager
)
from accounts.models import Subject

User = get_user_model()


class Payment(models.Model):
    """Main payment model for awards"""
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'
        PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED', 'Partially Refunded'
        DISPUTED = 'DISPUTED', 'Disputed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    class PaymentType(models.TextChoices):
        FULL_PAYMENT = 'FULL_PAYMENT', 'Full Payment'
        MILESTONE = 'MILESTONE', 'Milestone'
        SESSION = 'SESSION', 'Session'
        REFUND = 'REFUND', 'Refund'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    award = models.ForeignKey(
        'requirements.Award',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        help_text="Related award if payment is for a specific requirement"
    )
    payer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments_made',
        help_text="User making the payment"
    )
    payee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments_received',
        help_text="User receiving the payment"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Payment currency"
    )
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        help_text="Type of payment"
    )
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        help_text="Current payment status"
    )
    payment_method = models.ForeignKey(
        'PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        help_text="Payment method used"
    )
    paypal_transaction = models.ForeignKey(
        'paypal_integration.PayPalTransaction',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_records',
        help_text="PayPal transaction details if applicable"
    )
    transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Transaction ID from payment gateway"
    )
    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Response data from payment gateway"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Payment description"
    )
    admin_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Administrative notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was completed"
    )
    
    objects = PaymentManager()
    
    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        indexes = [
            models.Index(fields=['award_id']),
            models.Index(fields=['payer_id']),
            models.Index(fields=['payee_id']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['payer_id', 'status']),
            models.Index(fields=['payee_id', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment {self.id} - {self.amount} {self.currency} from {self.payer.get_full_name()} to {self.payee.get_full_name()}"
    
    def clean(self):
        """Validate payment data"""
        if self.amount <= 0:
            raise ValidationError('Payment amount must be positive')
        
        if self.payer == self.payee:
            raise ValidationError('Payer and payee cannot be the same user')
    
    def get_total_amount_with_fees(self):
        """Calculate total amount including platform fees"""
        # Calculate commission based on commission rates
        commission_amount = Decimal('0.00')
        commission_rates = CommissionRate.objects.filter(is_active=True)
        
        for rate in commission_rates:
            if rate.is_applicable(self.payer, self.amount):
                commission_amount = rate.calculate_commission(self.amount)
                break
        
        return self.amount + commission_amount
    
    def can_be_refunded(self):
        """Check if payment can be refunded"""
        return self.status == self.PaymentStatus.COMPLETED
    
    def release_to_tutor(self):
        """Release payment to tutor"""
        if self.status != self.PaymentStatus.COMPLETED:
            raise ValidationError('Payment cannot be released')
        
        # Create transaction record
        Transaction.objects.create(
            user=self.payee,
            transaction_type=Transaction.TransactionType.PAYMENT_RECEIVED,
            amount=self.amount,
            currency=self.currency,
            payment=self,
            description=f"Payment released from {self.payer.get_full_name()}"
        )
    
    def refund_to_student(self, amount=None, reason=""):
        """Refund payment to student"""
        if not self.can_be_refunded():
            raise ValidationError('Payment cannot be refunded')
        
        if amount is None:
            amount = self.amount
        
        if amount > self.amount:
            raise ValidationError('Refund amount cannot exceed payment amount')
        
        if amount == self.amount:
            self.status = self.PaymentStatus.REFUNDED
        else:
            self.status = self.PaymentStatus.PARTIALLY_REFUNDED
        
        self.save()
        
        # Create refund record
        refund = Refund.objects.create(
            payment=self,
            amount=amount,
            currency=self.currency,
            reason=reason,
            status=Refund.RefundStatus.PENDING
        )
        
        return refund
    
    def mark_failed(self, reason=None):
        """Mark payment as failed"""
        self.status = self.PaymentStatus.FAILED
        if reason:
            self.admin_notes = f"Payment failed: {reason}"
        self.save()


class EscrowAccount(models.Model):
    """Escrow account for each user to hold funds"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='escrow_account',
        help_text="User who owns this escrow account"
    )
    current_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Current available balance"
    )
    total_deposited = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total amount ever deposited"
    )
    total_withdrawn = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total amount ever withdrawn"
    )
    pending_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Amount held in pending transactions"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Account currency"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this escrow account is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = EscrowAccountManager()
    
    class Meta:
        verbose_name = 'Escrow Account'
        verbose_name_plural = 'Escrow Accounts'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['currency']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"Escrow Account for {self.user.get_full_name()} - {self.current_balance} {self.currency}"
    
    def add_funds(self, amount):
        """Add funds to escrow account"""
        if amount <= 0:
            raise ValidationError('Amount must be positive')
        
        self.current_balance += amount
        self.total_deposited += amount
        self.save()
        
        # Create transaction record
        Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TransactionType.DEPOSIT,
            amount=amount,
            currency=self.currency,
            running_balance=self.current_balance,
            description=f"Deposited {amount} {self.currency} to escrow"
        )
    
    def withdraw_funds(self, amount):
        """Withdraw funds from escrow account"""
        if amount <= 0:
            raise ValidationError('Amount must be positive')
        
        if amount > self.current_balance:
            raise ValidationError('Insufficient balance')
        
        self.current_balance -= amount
        self.total_withdrawn += amount
        self.save()
        
        # Create transaction record
        Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TransactionType.WITHDRAWAL,
            amount=amount,
            currency=self.currency,
            running_balance=self.current_balance,
            description=f"Withdrew {amount} {self.currency} from escrow"
        )
    
    def hold_funds(self, amount):
        """Hold funds for pending transactions"""
        if amount <= 0:
            raise ValidationError('Amount must be positive')
        
        if amount > self.current_balance:
            raise ValidationError('Insufficient balance to hold')
        
        self.current_balance -= amount
        self.pending_balance += amount
        self.save()
    
    def release_held_funds(self, amount):
        """Release held funds back to available balance"""
        if amount <= 0:
            raise ValidationError('Amount must be positive')
        
        if amount > self.pending_balance:
            raise ValidationError('Cannot release more than held funds')
        
        self.pending_balance -= amount
        self.current_balance += amount
        self.save()


class Transaction(models.Model):
    """Transaction history for all financial movements"""
    
    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Deposit'
        WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal'
        PAYMENT_RECEIVED = 'PAYMENT_RECEIVED', 'Payment Received'
        PAYMENT_SENT = 'PAYMENT_SENT', 'Payment Sent'
        REFUND_ISSUED = 'REFUND_ISSUED', 'Refund IssUED'
        REFUND_RECEIVED = 'REFUND_RECEIVED', 'Refund Received'
        COMMISSION_DEDUCTED = 'COMMISSION_DEDUCTED', 'Commission Deducted'
        PAYOUT_PROCESSED = 'PAYOUT_PROCESSED', 'Payout Processed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text="User this transaction belongs to"
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        help_text="Type of transaction"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Transaction amount"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Transaction currency"
    )
    running_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Balance after this transaction"
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        help_text="Related payment if any"
    )
    refund = models.ForeignKey(
        'Refund',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        help_text="Related refund if any"
    )
    description = models.TextField(
        help_text="Transaction description"
    )
    reference_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="External reference ID"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['reference_id']),
            models.Index(fields=['user_id', 'transaction_type']),
            models.Index(fields=['user_id', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Transaction {self.id} - {self.transaction_type} - {self.amount} {self.currency}"


class PaymentMethod(models.Model):
    """Payment methods stored for users"""
    
    class MethodType(models.TextChoices):
        STRIPE = 'STRIPE', 'Stripe'
        PAYPAL = 'PAYPAL', 'PayPal'
        PAYPAL_BALANCE = 'PAYPAL_BALANCE', 'PayPal Balance'
        PAYPAL_CARD = 'PAYPAL_CARD', 'PayPal Card'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank Transfer'
        CREDIT_CARD = 'CREDIT_CARD', 'Credit Card'
        DEBIT_CARD = 'DEBIT_CARD', 'Debit Card'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_methods',
        help_text="User who owns this payment method"
    )
    method_type = models.CharField(
        max_length=20,
        choices=MethodType.choices,
        help_text="Type of payment method"
    )
    method_details = models.JSONField(
        default=dict,
        help_text="Gateway-specific payment method details"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default payment method"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether this payment method has been verified"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this payment method is active"
    )
    provider_method_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="ID from payment provider"
    )
    display_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Display name for this payment method"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiration date for this payment method"
    )
    
    objects = PaymentMethodManager()
    
    class Meta:
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['method_type']),
            models.Index(fields=['is_default']),
            models.Index(fields=['is_active']),
            models.Index(fields=['user_id', 'is_default']),
            models.Index(fields=['user_id', 'is_active']),
        ]
    
    def __str__(self):
        method_display = next((label for value, label in self.MethodType.choices if value == self.method_type), self.method_type)
        return f"{self.user.get_full_name()}'s {method_display}"
    
    def clean(self):
        """Validate payment method data"""
        if self.is_default and not self.is_active:
            raise ValidationError('Default payment method must be active')
    
    def save(self, *args, **kwargs):
        # Ensure only one default payment method per user
        if self.is_default:
            PaymentMethod.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if payment method is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def can_be_used(self):
        """Check if payment method can be used"""
        return self.is_active and self.is_verified and not self.is_expired()


class Commission(models.Model):
    """Commission tracking for platform fees"""
    
    class CommissionType(models.TextChoices):
        PLATFORM_FEE = 'PLATFORM_FEE', 'Platform Fee'
        PROCESSING_FEE = 'PROCESSING_FEE', 'Processing Fee'
        TRANSACTION_FEE = 'TRANSACTION_FEE', 'Transaction Fee'
        REFUND_FEE = 'REFUND_FEE', 'Refund Fee'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='commissions',
        help_text="Payment this commission is for"
    )
    commission_type = models.CharField(
        max_length=20,
        choices=CommissionType.choices,
        help_text="Type of commission"
    )
    commission_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Commission amount"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Commission currency"
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        help_text="Commission rate as decimal (e.g., 0.15 for 15%)"
    )
    calculated_on_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount commission was calculated on"
    )
    is_collected = models.BooleanField(
        default=False,
        help_text="Whether commission has been collected"
    )
    collected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When commission was collected"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Commission description"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = CommissionManager()
    
    class Meta:
        verbose_name = 'Commission'
        verbose_name_plural = 'Commissions'
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['commission_type']),
            models.Index(fields=['is_collected']),
            models.Index(fields=['created_at']),
            models.Index(fields=['payment_id', 'commission_type']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Commission {self.id} - {self.commission_amount} {self.currency} ({self.commission_rate * 100}%)"
    
    def clean(self):
        """Validate commission data"""
        if self.commission_amount <= 0:
            raise ValidationError('Commission amount must be positive')
        
        if self.commission_rate < 0 or self.commission_rate > 1:
            raise ValidationError('Commission rate must be between 0 and 1')
        
        if self.calculated_on_amount <= 0:
            raise ValidationError('Calculated amount must be positive')
    
    def mark_collected(self):
        """Mark commission as collected"""
        if not self.is_collected:
            self.is_collected = True
            self.collected_at = timezone.now()
            self.save()
            
            # Create transaction record
            commission_type_display = next((label for value, label in self.CommissionType.choices if value == self.commission_type), self.commission_type)
            Transaction.objects.create(
                user=self.payment.payer,
                transaction_type=Transaction.TransactionType.COMMISSION_DEDUCTED,
                amount=self.commission_amount,
                currency=self.currency,
                payment=self.payment,
                description=f"Commission deducted: {self.description or commission_type_display}"
            )


class Refund(models.Model):
    """Refund processing for payments"""
    
    class RefundStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        PROCESSED = 'PROCESSED', 'Processed'
        COMPLETED = 'COMPLETED', 'Completed'
        REJECTED = 'REJECTED', 'Rejected'
        FAILED = 'FAILED', 'Failed'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='refunds',
        help_text="Payment being refunded"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Refund amount"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Refund currency"
    )
    reason = models.TextField(
        help_text="Reason for refund"
    )
    status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
        help_text="Current refund status"
    )
    refund_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refunds',
        help_text="Payment method for refund"
    )
    refund_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Transaction ID for refund"
    )
    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Response from payment gateway"
    )
    admin_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Administrative notes"
    )
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_refunds',
        help_text="Admin who processed this refund"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When refund was processed"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When refund was completed"
    )
    
    class Meta:
        verbose_name = 'Refund'
        verbose_name_plural = 'Refunds'
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['refund_transaction_id']),
            models.Index(fields=['payment_id', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund {self.id} - {self.amount} {self.currency} for Payment {self.payment.id}"
    
    def clean(self):
        """Validate refund data"""
        if self.amount <= 0:
            raise ValidationError('Refund amount must be positive')
        
        if self.payment and self.amount > self.payment.amount:
            raise ValidationError('Refund amount cannot exceed payment amount')
    
    def approve(self, processed_by=None):
        """Approve the refund"""
        if self.status != self.RefundStatus.PENDING:
            raise ValidationError('Only pending refunds can be approved')
        
        self.status = self.RefundStatus.APPROVED
        self.processed_by = processed_by
        self.processed_at = timezone.now()
        self.save()
    
    def process(self, refund_transaction_id=None, gateway_response=None):
        """Process the refund"""
        if self.status != self.RefundStatus.APPROVED:
            raise ValidationError('Only approved refunds can be processed')
        
        self.status = self.RefundStatus.PROCESSED
        self.refund_transaction_id = refund_transaction_id
        if gateway_response:
            self.gateway_response = gateway_response
        self.save()
    
    def complete(self):
        """Complete the refund"""
        if self.status != self.RefundStatus.PROCESSED:
            raise ValidationError('Only processed refunds can be completed')
        
        self.status = self.RefundStatus.COMPLETED
        self.completed_at = timezone.now()
        self.save()
        
        # Update payment status
        if self.payment.amount == self.amount:
            self.payment.status = Payment.PaymentStatus.REFUNDED
        else:
            self.payment.status = Payment.PaymentStatus.PARTIALLY_REFUNDED
        self.payment.save()
        
        # Create transaction records
        Transaction.objects.create(
            user=self.payment.payer,
            transaction_type=Transaction.TransactionType.REFUND_RECEIVED,
            amount=self.amount,
            currency=self.currency,
            refund=self,
            description=f"Refund received for payment {self.payment.id}"
        )
        
        Transaction.objects.create(
            user=self.payment.payee,
            transaction_type=Transaction.TransactionType.REFUND_ISSUED,
            amount=self.amount,
            currency=self.currency,
            refund=self,
            description=f"Refund issued for payment {self.payment.id}"
        )


class Payout(models.Model):
    """Payout processing for tutors"""
    
    class PayoutStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tutor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payouts',
        limit_choices_to={'user_type': 'TUTOR'},
        help_text="Tutor receiving this payout"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total payout amount"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Payout currency"
    )
    status = models.CharField(
        max_length=20,
        choices=PayoutStatus.choices,
        default=PayoutStatus.PENDING,
        help_text="Current payout status"
    )
    payout_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payouts',
        help_text="Payment method for payout"
    )
    payout_method_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional payout method details"
    )
    processing_fees = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Processing fees deducted"
    )
    net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Net amount after fees"
    )
    scheduled_payout_date = models.DateField(
        null=True,
        blank=True,
        help_text="Scheduled date for payout"
    )
    processed_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payout was processed"
    )
    transaction_reference = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Transaction reference from payment provider"
    )
    gateway_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Response from payment gateway"
    )
    admin_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Administrative notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = PayoutManager()
    
    class Meta:
        verbose_name = 'Payout'
        verbose_name_plural = 'Payouts'
        indexes = [
            models.Index(fields=['tutor_id']),
            models.Index(fields=['status']),
            models.Index(fields=['scheduled_payout_date']),
            models.Index(fields=['created_at']),
            models.Index(fields=['transaction_reference']),
            models.Index(fields=['tutor_id', 'status']),
            models.Index(fields=['status', 'scheduled_payout_date']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payout {self.id} - {self.net_amount} {self.currency} to {self.tutor.get_full_name()}"
    
    def clean(self):
        """Validate payout data"""
        if self.total_amount <= 0:
            raise ValidationError('Total amount must be positive')
        
        if self.net_amount < 0:
            raise ValidationError('Net amount cannot be negative')
        
        if self.processing_fees < 0:
            raise ValidationError('Processing fees cannot be negative')
        
        if self.total_amount < self.processing_fees:
            raise ValidationError('Processing fees cannot exceed total amount')
    
    def save(self, *args, **kwargs):
        # Calculate net amount if not provided
        if not self.net_amount:
            self.net_amount = self.total_amount - self.processing_fees
        super().save(*args, **kwargs)
    
    def process(self, transaction_reference=None, gateway_response=None):
        """Process the payout"""
        if self.status != self.PayoutStatus.PENDING:
            raise ValidationError('Only pending payouts can be processed')
        
        self.status = self.PayoutStatus.PROCESSING
        self.processed_date = timezone.now()
        if transaction_reference:
            self.transaction_reference = transaction_reference
        if gateway_response:
            self.gateway_response = gateway_response
        self.save()
    
    def complete(self):
        """Complete the payout"""
        if self.status != self.PayoutStatus.PROCESSING:
            raise ValidationError('Only processing payouts can be completed')
        
        self.status = self.PayoutStatus.COMPLETED
        self.save()
        
        # Create transaction record
        Transaction.objects.create(
            user=self.tutor,
            transaction_type=Transaction.TransactionType.PAYOUT_PROCESSED,
            amount=self.net_amount,
            currency=self.currency,
            description=f"Payout processed - {self.total_amount} {self.currency} (fees: {self.processing_fees})"
        )
    
    def fail(self, reason=None):
        """Mark payout as failed"""
        self.status = self.PayoutStatus.FAILED
        if reason:
            self.admin_notes = f"Payout failed: {reason}"
        self.save()


class EscrowTransaction(models.Model):
    """Individual escrow transactions"""
    
    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', 'Deposit'
        WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal'
        HOLD = 'HOLD', 'Hold'
        RELEASE = 'RELEASE', 'Release'
        REFUND = 'REFUND', 'Refund'
        FEE = 'FEE', 'Fee'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    escrow_account = models.ForeignKey(
        EscrowAccount,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text="Escrow account this transaction belongs to"
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        help_text="Type of transaction"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Transaction amount"
    )
    fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Transaction fee"
    )
    net_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Net amount after fee"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Transaction currency"
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="External reference"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Transaction description"
    )
    status = models.CharField(
        max_length=20,
        choices=Payment.PaymentStatus.choices,
        default=Payment.PaymentStatus.PENDING,
        help_text="Transaction status"
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escrow_transactions',
        help_text="Payment method used"
    )
    related_award = models.ForeignKey(
        'requirements.Award',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escrow_transactions',
        help_text="Related award if any"
    )
    related_payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escrow_transactions',
        help_text="Related payment if any"
    )
    provider_transaction_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Transaction ID from payment provider"
    )
    failure_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for failure if applicable"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When transaction was processed"
    )
    
    class Meta:
        verbose_name = 'Escrow Transaction'
        verbose_name_plural = 'Escrow Transactions'
        indexes = [
            models.Index(fields=['escrow_account_id']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['provider_transaction_id']),
            models.Index(fields=['escrow_account_id', 'transaction_type']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Escrow Transaction {self.id} - {self.transaction_type} - {self.amount} {self.currency}"
    
    def process(self):
        """Process the transaction"""
        if self.status != Payment.PaymentStatus.PENDING:
            raise ValidationError('Only pending transactions can be processed')
        
        self.status = Payment.PaymentStatus.PROCESSING
        self.processed_at = timezone.now()
        self.save()
    
    def cancel(self):
        """Cancel the transaction"""
        if self.status == Payment.PaymentStatus.COMPLETED:
            raise ValidationError('Cannot cancel completed transaction')
        
        self.status = Payment.PaymentStatus.CANCELLED
        self.save()
    
    def get_status_display(self):
        """Return formatted status"""
        return next((label for value, label in Payment.PaymentStatus.choices if value == self.status), self.status)


class PaymentSplit(models.Model):
    """Split payments for milestones or multiple sessions"""
    
    class SplitStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        RELEASED = 'RELEASED', 'Released'
        REFUNDED = 'REFUNDED', 'Refunded'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='splits',
        help_text="Payment this split belongs to"
    )
    milestone = models.ForeignKey(
        'requirements.Milestone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_splits',
        help_text="Related milestone if any"
    )
    session = models.ForeignKey(
        'requirements.Session',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_splits',
        help_text="Related session if any"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Split amount"
    )
    status = models.CharField(
        max_length=20,
        choices=SplitStatus.choices,
        default=SplitStatus.PENDING,
        help_text="Split status"
    )
    release_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when funds were released"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Payment Split'
        verbose_name_plural = 'Payment Splits'
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['milestone_id']),
            models.Index(fields=['session_id']),
            models.Index(fields=['status']),
            models.Index(fields=['release_date']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment Split {self.id} - {self.amount} {self.payment.currency}"


class CommissionRate(models.Model):
    """Configurable commission rates"""
    
    class RateType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', 'Percentage'
        FIXED = 'FIXED', 'Fixed'
        TIERED = 'TIERED', 'Tiered'
    
    class UserType(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        TUTOR = 'TUTOR', 'Tutor'
        ALL = 'ALL', 'All'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        help_text="Commission rate name"
    )
    rate_type = models.CharField(
        max_length=20,
        choices=RateType.choices,
        help_text="Type of rate"
    )
    rate_value = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        help_text="Rate value"
    )
    min_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Minimum amount for this rate to apply"
    )
    max_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum amount for this rate to apply"
    )
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.ALL,
        help_text="User type this rate applies to"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='commission_rates',
        help_text="Subject this rate applies to"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this rate is active"
    )
    effective_from = models.DateField(
        help_text="Date when rate becomes effective"
    )
    effective_to = models.DateField(
        null=True,
        blank=True,
        help_text="Date when rate stops being effective"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Commission Rate'
        verbose_name_plural = 'Commission Rates'
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['subject_id']),
            models.Index(fields=['is_active']),
            models.Index(fields=['effective_from']),
            models.Index(fields=['effective_to']),
        ]
        ordering = ['-effective_from']
    
    def __str__(self):
        return f"Commission Rate {self.name} - {self.rate_value}"
    
    def calculate_commission(self, amount):
        """Calculate commission for given amount"""
        if self.rate_type == self.RateType.PERCENTAGE:
            return amount * self.rate_value
        elif self.rate_type == self.RateType.FIXED:
            return self.rate_value
        elif self.rate_type == self.RateType.TIERED:
            # Simplified tiered calculation - in production would be more complex
            return amount * self.rate_value
        return Decimal('0.00')
    
    def is_applicable(self, user, amount, subject=None):
        """Check if rate applies to given user, amount, and subject"""
        # Check user type
        if self.user_type != self.UserType.ALL:
            if not hasattr(user, 'user_type') or user.user_type != self.user_type:
                return False
        
        # Check amount range
        if self.min_amount and amount < self.min_amount:
            return False
        if self.max_amount and amount > self.max_amount:
            return False
        
        # Check subject
        if self.subject and (not subject or subject.pk != self.subject.pk):
            return False
        
        # Check effective date range
        today = timezone.now().date()
        if self.effective_from and today < self.effective_from:
            return False
        if self.effective_to and today > self.effective_to:
            return False
        
        return True


class PayPalAccount(models.Model):
    """PayPal account integration"""
    
    class AccountType(models.TextChoices):
        PERSONAL = 'PERSONAL', 'Personal'
        PREMIER = 'PREMIER', 'Premier'
        BUSINESS = 'BUSINESS', 'Business'
    
    class VerificationStatus(models.TextChoices):
        UNVERIFIED = 'UNVERIFIED', 'Unverified'
        VERIFIED = 'VERIFIED', 'Verified'
        LIMITED = 'LIMITED', 'Limited'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='paypal_accounts',
        help_text="User who owns this PayPal account"
    )
    paypal_email = models.EmailField(
        help_text="PayPal email address"
    )
    paypal_user_id = models.CharField(
        max_length=100,
        help_text="PayPal user ID"
    )
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        help_text="PayPal account type"
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        help_text="Verification status"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Whether this is the primary PayPal account"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this PayPal account is active"
    )
    access_token = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="OAuth access token"
    )
    refresh_token = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="OAuth refresh token"
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When access token expires"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'PayPal Account'
        verbose_name_plural = 'PayPal Accounts'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['paypal_email']),
            models.Index(fields=['is_primary']),
            models.Index(fields=['is_active']),
            models.Index(fields=['user_id', 'is_primary']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PayPal Account {self.paypal_email} for {self.user.get_full_name()}"
    
    def is_token_expired(self):
        """Check if access token is expired"""
        if not self.token_expires_at:
            return True
        return timezone.now() > self.token_expires_at
    
    def refresh_access_token(self):
        """Refresh the access token"""
        # This would integrate with PayPal's OAuth API
        # For now, just mark as expired
        self.access_token = None
        self.token_expires_at = None
        self.save()


class PayPalTransactionDetails(models.Model):
    """PayPal-specific transaction details (legacy model for compatibility)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='paypal_transaction_details',
        help_text="Related payment"
    )
    paypal_transaction_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="PayPal transaction ID"
    )
    paypal_order_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="PayPal order ID"
    )
    paypal_payment_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="PayPal payment ID"
    )
    paypal_payer_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="PayPal payer ID"
    )
    paypal_status = models.CharField(
        max_length=50,
        help_text="PayPal status"
    )
    paypal_intent = models.CharField(
        max_length=20,
        choices=[
            ('SALE', 'Sale'),
            ('AUTHORIZE', 'Authorize'),
            ('ORDER', 'Order')
        ],
        help_text="PayPal intent"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Transaction amount"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Transaction currency"
    )
    fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="PayPal fee amount"
    )
    net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Net amount after fee"
    )
    paypal_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full PayPal response"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'PayPal Transaction Details'
        verbose_name_plural = 'PayPal Transaction Details'
        indexes = [
            models.Index(fields=['payment_id']),
            models.Index(fields=['paypal_transaction_id']),
            models.Index(fields=['paypal_order_id']),
            models.Index(fields=['paypal_payment_id']),
            models.Index(fields=['paypal_status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PayPal Transaction Details {self.paypal_transaction_id} - {self.amount} {self.currency}"


class Invoice(models.Model):
    """Invoice generation and tracking"""
    
    class InvoiceType(models.TextChoices):
        TUITION = 'TUITION', 'Tuition'
        COMMISSION = 'COMMISSION', 'Commission'
        REFUND = 'REFUND', 'Refund'
        CREDIT = 'CREDIT', 'Credit'
    
    class InvoiceStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SENT = 'SENT', 'Sent'
        PAID = 'PAID', 'Paid'
        OVERDUE = 'OVERDUE', 'Overdue'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique invoice number"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='invoices',
        help_text="User this invoice is for"
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice',
        help_text="Related payment if any"
    )
    invoice_type = models.CharField(
        max_length=20,
        choices=InvoiceType.choices,
        help_text="Type of invoice"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Invoice amount"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Tax amount"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total amount including tax"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Invoice currency"
    )
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        help_text="Invoice status"
    )
    issue_date = models.DateField(
        help_text="Invoice issue date"
    )
    due_date = models.DateField(
        help_text="Invoice due date"
    )
    paid_date = models.DateField(
        null=True,
        blank=True,
        help_text="When invoice was paid"
    )
    billing_address = models.TextField(
        blank=True,
        null=True,
        help_text="Billing address"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Invoice notes"
    )
    terms = models.TextField(
        blank=True,
        null=True,
        help_text="Invoice terms and conditions"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['payment_id']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['user_id', 'status']),
            models.Index(fields=['status', 'due_date']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.total_amount} {self.currency}"


class InvoiceItem(models.Model):
    """Line items for invoices"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Invoice this item belongs to"
    )
    description = models.CharField(
        max_length=255,
        help_text="Item description"
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Item quantity"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Unit price"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total amount (quantity × unit price)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Invoice Item'
        verbose_name_plural = 'Invoice Items'
        indexes = [
            models.Index(fields=['invoice_id']),
        ]
        ordering = ['created_at']
    
    def __str__(self):
        return f"Invoice Item {self.id} - {self.description}"


class FinancialSummary(models.Model):
    """Periodic financial summaries"""
    
    class PeriodType(models.TextChoices):
        DAILY = 'DAILY', 'Daily'
        WEEKLY = 'WEEKLY', 'Weekly'
        MONTHLY = 'MONTHLY', 'Monthly'
        YEARLY = 'YEARLY', 'Yearly'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period_type = models.CharField(
        max_length=20,
        choices=PeriodType.choices,
        help_text="Type of period"
    )
    period_start = models.DateField(
        help_text="Start date of period"
    )
    period_end = models.DateField(
        help_text="End date of period"
    )
    total_payments = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total payments in period"
    )
    total_commissions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total commissions in period"
    )
    total_refunds = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total refunds in period"
    )
    net_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Net revenue (payments - commissions - refunds)"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Summary currency"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Financial Summary'
        verbose_name_plural = 'Financial Summaries'
        indexes = [
            models.Index(fields=['period_type']),
            models.Index(fields=['period_start']),
            models.Index(fields=['period_end']),
            models.Index(fields=['currency']),
            models.Index(fields=['period_type', 'period_start']),
        ]
        ordering = ['-period_start']
    
    def __str__(self):
        return f"Financial Summary {self.period_type} {self.period_start} to {self.period_end}"
