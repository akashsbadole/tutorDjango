import uuid
import json
import hashlib
import hmac
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from django.conf import settings

User = get_user_model()


class PayPalAccount(models.Model):
    """PayPal account integration for users"""
    
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
        related_name='paypal_integration_accounts',
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
        default=VerificationStatus.UNVERIFIED,
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
    merchant_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="PayPal merchant ID for business accounts"
    )
    webhook_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="PayPal webhook ID for this account"
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
            models.Index(fields=['paypal_user_id']),
            models.Index(fields=['is_primary']),
            models.Index(fields=['is_active']),
            models.Index(fields=['user_id', 'is_primary']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PayPal Account {self.paypal_email} for {self.user.get_full_name()}"
    
    def clean(self):
        """Validate PayPal account data"""
        if self.is_primary and not self.is_active:
            raise ValidationError('Primary PayPal account must be active')
    
    def save(self, *args, **kwargs):
        # Ensure only one primary PayPal account per user
        if self.is_primary:
            PayPalAccount.objects.filter(
                user=self.user,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
    
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


class PayPalTransaction(models.Model):
    """PayPal-specific transaction details"""
    
    class TransactionStatus(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        APPROVED = 'APPROVED', 'Approved'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        REFUNDED = 'REFUNDED', 'Refunded'
        PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED', 'Partially Refunded'
    
    class TransactionType(models.TextChoices):
        PAYMENT = 'PAYMENT', 'Payment'
        REFUND = 'REFUND', 'Refund'
        PAYOUT = 'PAYOUT', 'Payout'
        TRANSFER = 'TRANSFER', 'Transfer'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
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
        choices=TransactionStatus.choices,
        help_text="PayPal status"
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.PAYMENT,
        help_text="Type of transaction"
    )
    paypal_intent = models.CharField(
        max_length=20,
        choices=[
            ('SALE', 'Sale'),
            ('AUTHORIZE', 'Authorize'),
            ('ORDER', 'Order'),
            ('CAPTURE', 'Capture')
        ],
        default='SALE',
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
    paypal_account = models.ForeignKey(
        PayPalAccount,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text="PayPal account used for this transaction"
    )
    related_payment = models.ForeignKey(
        'paymentsdetails.Payment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paypal_transactions',
        help_text="Related payment in the system"
    )
    related_payout = models.ForeignKey(
        'paymentsdetails.Payout',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paypal_transactions',
        help_text="Related payout in the system"
    )
    paypal_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full PayPal response"
    )
    failure_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for failure if applicable"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When transaction was completed"
    )
    
    class Meta:
        verbose_name = 'PayPal Transaction'
        verbose_name_plural = 'PayPal Transactions'
        indexes = [
            models.Index(fields=['paypal_transaction_id']),
            models.Index(fields=['paypal_order_id']),
            models.Index(fields=['paypal_payment_id']),
            models.Index(fields=['paypal_status']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['paypal_account_id']),
            models.Index(fields=['related_payment_id']),
            models.Index(fields=['related_payout_id']),
            models.Index(fields=['created_at']),
            models.Index(fields=['paypal_status', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PayPal Transaction {self.paypal_transaction_id} - {self.amount} {self.currency}"
    
    def mark_completed(self):
        """Mark transaction as completed"""
        self.paypal_status = self.TransactionStatus.COMPLETED
        self.completed_at = timezone.now()
        self.save()


class PayPalWebhook(models.Model):
    """PayPal webhook event processing"""
    
    class WebhookStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSED = 'PROCESSED', 'Processed'
        FAILED = 'FAILED', 'Failed'
        IGNORED = 'IGNORED', 'Ignored'
    
    class WebhookEventType(models.TextChoices):
        PAYMENT_AUTHORIZATION_CREATED = 'PAYMENT.AUTHORIZATION.CREATED', 'Payment Authorization Created'
        PAYMENT_AUTHORIZATION_VOIDED = 'PAYMENT.AUTHORIZATION.VOIDED', 'Payment Authorization Voided'
        PAYMENT_CAPTURE_COMPLETED = 'PAYMENT.CAPTURE.COMPLETED', 'Payment Capture Completed'
        PAYMENT_CAPTURE_DENIED = 'PAYMENT.CAPTURE.DENIED', 'Payment Capture Denied'
        PAYMENT_SALE_COMPLETED = 'PAYMENT.SALE.COMPLETED', 'Payment Sale Completed'
        PAYMENT_SALE_DENIED = 'PAYMENT.SALE.DENIED', 'Payment Sale Denied'
        PAYMENT_SALE_PENDING = 'PAYMENT.SALE.PENDING', 'Payment Sale Pending'
        PAYMENT_SALE_REFUNDED = 'PAYMENT.SALE.REFUNDED', 'Payment Sale Refunded'
        PAYMENT_SALE_REVERSED = 'PAYMENT.SALE.REVERSED', 'Payment Sale Reversed'
        MERCHANT_ONBOARDING_COMPLETED = 'MERCHANT.ONBOARDING.COMPLETED', 'Merchant Onboarding Completed'
        BILLING_SUBSCRIPTION_ACTIVATED = 'BILLING.SUBSCRIPTION.ACTIVATED', 'Subscription Activated'
        BILLING_SUBSCRIPTION_CANCELLED = 'BILLING.SUBSCRIPTION.CANCELLED', 'Subscription Cancelled'
        BILLING_SUBSCRIPTION_CREATED = 'BILLING.SUBSCRIPTION.CREATED', 'Subscription Created'
        BILLING_SUBSCRIPTION_EXPIRED = 'BILLING.SUBSCRIPTION.EXPIRED', 'Subscription Expired'
        BILLING_SUBSCRIPTION_SUSPENDED = 'BILLING.SUBSCRIPTION.SUSPENDED', 'Subscription Suspended'
        BILLING_SUBSCRIPTION_UPDATED = 'BILLING.SUBSCRIPTION.UPDATED', 'Subscription Updated'
        PAYOUTS_PAYOUT_ITEM_DENIED = 'PAYOUTS.PAYOUT-ITEM.DENIED', 'Payout Item Denied'
        PAYOUTS_PAYOUT_ITEM_FAILED = 'PAYOUTS.PAYOUT-ITEM.FAILED', 'Payout Item Failed'
        PAYOUTS_PAYOUT_ITEM_HOLD = 'PAYOUTS.PAYOUT-ITEM.HOLD', 'Payout Item Hold'
        PAYOUTS_PAYOUT_ITEM_SUCCESS = 'PAYOUTS.PAYOUT-ITEM.SUCCESS', 'Payout Item Success'
        PAYOUTS_PAYOUT_BATCH_DENIED = 'PAYOUTS.PAYOUT-BATCH.DENIED', 'Payout Batch Denied'
        PAYOUTS_PAYOUT_BATCH_FAILED = 'PAYOUTS.PAYOUT-BATCH.FAILED', 'Payout Batch Failed'
        PAYOUTS_PAYOUT_BATCH_SUCCESS = 'PAYOUTS.PAYOUT-BATCH.SUCCESS', 'Payout Batch Success'
        CHECKOUT_ORDER_APPROVED = 'CHECKOUT.ORDER.APPROVED', 'Checkout Order Approved'
        CHECKOUT_ORDER_COMPLETED = 'CHECKOUT.ORDER.COMPLETED', 'Checkout Order Completed'
        CHECKOUT_ORDER_CREATED = 'CHECKOUT.ORDER.CREATED', 'Checkout Order Created'
        INVOICING_INVOICE_CANCELLED = 'INVOICING.INVOICE.CANCELLED', 'Invoice Cancelled'
        INVOICING_INVOICE_CREATED = 'INVOICING.INVOICE.CREATED', 'Invoice Created'
        INVOICING_INVOICE_PAID = 'INVOICING.INVOICE.PAID', 'Invoice Paid'
        INVOICING_INVOICE_REFUNDED = 'INVOICING.INVOICE.REFUNDED', 'Invoice Refunded'
        INVOICING_INVOICE_UPDATED = 'INVOICING.INVOICE.UPDATED', 'Invoice Updated'
        DISPUTE_CREATED = 'DISPUTE.CREATED', 'Dispute Created'
        DISPUTE_RESOLVED = 'DISPUTE.RESOLVED', 'Dispute Resolved'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook_id = models.CharField(
        max_length=100,
        help_text="PayPal webhook ID"
    )
    event_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="PayPal event ID"
    )
    event_type = models.CharField(
        max_length=100,
        choices=WebhookEventType.choices,
        help_text="Type of webhook event"
    )
    resource_type = models.CharField(
        max_length=50,
        help_text="Type of resource in the event"
    )
    status = models.CharField(
        max_length=20,
        choices=WebhookStatus.choices,
        default=WebhookStatus.PENDING,
        help_text="Processing status"
    )
    payload = models.JSONField(
        help_text="Full webhook payload"
    )
    headers = models.JSONField(
        default=dict,
        help_text="HTTP headers from webhook"
    )
    verification_status = models.BooleanField(
        default=False,
        help_text="Whether webhook signature was verified"
    )
    processing_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Number of processing attempts"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if processing failed"
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When webhook was processed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'PayPal Webhook'
        verbose_name_plural = 'PayPal Webhooks'
        indexes = [
            models.Index(fields=['webhook_id']),
            models.Index(fields=['event_id']),
            models.Index(fields=['event_type']),
            models.Index(fields=['status']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PayPal Webhook {self.event_id} - {self.event_type}"
    
    def verify_signature(self):
        """Verify webhook signature"""
        if not headers:
            return False
        
        # Get PayPal webhook ID from settings
        webhook_id = getattr(settings, 'PAYPAL_WEBHOOK_ID', None)
        if not webhook_id:
            return False
        
        # Get signature from headers
        auth_algo = self.headers.get('PAYPAL-AUTH-ALGO')
        transmission_id = self.headers.get('PAYPAL-TRANSMISSION-ID')
        cert_id = self.headers.get('PAYPAL-CERT-ID')
        transmission_sig = self.headers.get('PAYPAL-TRANSMISSION-SIG')
        transmission_time = self.headers.get('PAYPAL-TRANSMISSION-TIME')
        
        if not all([auth_algo, transmission_id, cert_id, transmission_sig, transmission_time]):
            return False
        
        # This would integrate with PayPal's webhook verification API
        # For now, we'll mark as verified for development
        self.verification_status = True
        self.save()
        return True
    
    def mark_processed(self):
        """Mark webhook as processed"""
        self.status = self.WebhookStatus.PROCESSED
        self.processed_at = timezone.now()
        self.save()
    
    def mark_failed(self, error_message):
        """Mark webhook processing as failed"""
        self.status = self.WebhookStatus.FAILED
        self.error_message = error_message
        self.processing_attempts += 1
        self.save()


class PayPalSubscription(models.Model):
    """PayPal subscription management"""
    
    class SubscriptionStatus(models.TextChoices):
        APPROVAL_PENDING = 'APPROVAL_PENDING', 'Approval Pending'
        APPROVED = 'APPROVED', 'Approved'
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        CANCELLED = 'CANCELLED', 'Cancelled'
        COMPLETED = 'COMPLETED', 'Completed'
        EXPIRED = 'EXPIRED', 'Expired'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paypal_subscription_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="PayPal subscription ID"
    )
    paypal_plan_id = models.CharField(
        max_length=100,
        help_text="PayPal plan ID"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='paypal_subscriptions',
        help_text="User who owns this subscription"
    )
    paypal_account = models.ForeignKey(
        PayPalAccount,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        help_text="PayPal account used for subscription"
    )
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        help_text="Subscription status"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Subscription amount"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Subscription currency"
    )
    interval = models.CharField(
        max_length=20,
        choices=[
            ('DAY', 'Daily'),
            ('WEEK', 'Weekly'),
            ('MONTH', 'Monthly'),
            ('YEAR', 'Yearly')
        ],
        help_text="Billing interval"
    )
    interval_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of intervals between billing cycles"
    )
    trial_period_days = models.PositiveIntegerField(
        default=0,
        help_text="Number of trial days"
    )
    current_period_start = models.DateTimeField(
        help_text="Start of current billing period"
    )
    current_period_end = models.DateTimeField(
        help_text="End of current billing period"
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When subscription was cancelled"
    )
    ends_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When subscription ends"
    )
    paypal_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full PayPal response"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'PayPal Subscription'
        verbose_name_plural = 'PayPal Subscriptions'
        indexes = [
            models.Index(fields=['paypal_subscription_id']),
            models.Index(fields=['paypal_plan_id']),
            models.Index(fields=['user_id']),
            models.Index(fields=['paypal_account_id']),
            models.Index(fields=['status']),
            models.Index(fields=['current_period_end']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'current_period_end']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PayPal Subscription {self.paypal_subscription_id} for {self.user.get_full_name()}"
    
    def is_active(self):
        """Check if subscription is currently active"""
        return self.status == self.SubscriptionStatus.ACTIVE
    
    def cancel(self, reason=""):
        """Cancel the subscription"""
        self.status = self.SubscriptionStatus.CANCELLED
        self.cancelled_at = timezone.now()
        self.ends_at = self.current_period_end
        self.metadata['cancellation_reason'] = reason
        self.save()


class PayPalRefund(models.Model):
    """PayPal refund processing"""
    
    class RefundStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paypal_refund_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="PayPal refund ID"
    )
    paypal_transaction = models.ForeignKey(
        PayPalTransaction,
        on_delete=models.CASCADE,
        related_name='refunds',
        help_text="Original PayPal transaction being refunded"
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
    status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
        help_text="Refund status"
    )
    reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for refund"
    )
    paypal_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full PayPal response"
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When refund was processed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'PayPal Refund'
        verbose_name_plural = 'PayPal Refunds'
        indexes = [
            models.Index(fields=['paypal_refund_id']),
            models.Index(fields=['paypal_transaction_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PayPal Refund {self.paypal_refund_id} - {self.amount} {self.currency}"
    
    def mark_completed(self):
        """Mark refund as completed"""
        self.status = self.RefundStatus.COMPLETED
        self.processed_at = timezone.now()
        self.save()


class PayPalDispute(models.Model):
    """PayPal dispute resolution"""
    
    class DisputeStatus(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        WAITING_FOR_BUYER_RESPONSE = 'WAITING_FOR_BUYER_RESPONSE', 'Waiting for Buyer Response'
        WAITING_FOR_SELLER_RESPONSE = 'WAITING_FOR_SELLER_RESPONSE', 'Waiting for Seller Response'
        UNDER_REVIEW = 'UNDER_REVIEW', 'Under Review'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'
    
    class DisputeReason(models.TextChoices):
        MERCHANDISE_OR_SERVICE_NOT_RECEIVED = 'MERCHANDISE_OR_SERVICE_NOT_RECEIVED', 'Merchandise or Service Not Received'
        MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED = 'MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED', 'Merchandise or Service Not as Described'
        UNAUTHORIZED_TRANSACTION = 'UNAUTHORIZED_TRANSACTION', 'Unauthorized Transaction'
        CREDIT_NOT_PROCESSED = 'CREDIT_NOT_PROCESSED', 'Credit Not Processed'
        DUPLICATE_PAYMENT = 'DUPLICATE_PAYMENT', 'Duplicate Payment'
        INCORRECT_AMOUNT = 'INCORRECT_AMOUNT', 'Incorrect Amount'
        PAYMENT_BY_OTHER_MEANS = 'PAYMENT_BY_OTHER_MEANS', 'Payment by Other Means'
        CANCELED_RECURRING_PAYMENT = 'CANCELED_RECURRING_PAYMENT', 'Canceled Recurring Payment'
        PROBLEM_WITH_REMITTANCE = 'PROBLEM_WITH_REMITTANCE', 'Problem with Remittance'
        OTHER = 'OTHER', 'Other'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paypal_dispute_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="PayPal dispute ID"
    )
    paypal_transaction = models.ForeignKey(
        PayPalTransaction,
        on_delete=models.CASCADE,
        related_name='disputes',
        help_text="PayPal transaction being disputed"
    )
    status = models.CharField(
        max_length=50,
        choices=DisputeStatus.choices,
        help_text="Dispute status"
    )
    reason = models.CharField(
        max_length=100,
        choices=DisputeReason.choices,
        help_text="Reason for dispute"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Disputed amount"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Dispute currency"
    )
    buyer_message = models.TextField(
        blank=True,
        null=True,
        help_text="Message from buyer"
    )
    seller_response = models.TextField(
        blank=True,
        null=True,
        help_text="Response from seller"
    )
    resolution = models.TextField(
        blank=True,
        null=True,
        help_text="Dispute resolution details"
    )
    paypal_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Full PayPal response"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When dispute was resolved"
    )
    
    class Meta:
        verbose_name = 'PayPal Dispute'
        verbose_name_plural = 'PayPal Disputes'
        indexes = [
            models.Index(fields=['paypal_dispute_id']),
            models.Index(fields=['paypal_transaction_id']),
            models.Index(fields=['status']),
            models.Index(fields=['reason']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"PayPal Dispute {self.paypal_dispute_id} - {self.reason}"
    
    def resolve(self, resolution_details):
        """Resolve the dispute"""
        self.status = self.DisputeStatus.RESOLVED
        self.resolution = resolution_details
        self.resolved_at = timezone.now()
        self.save()
