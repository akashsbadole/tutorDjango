from django.db import models
from django.db.models import Sum, Q
from django.utils import timezone
from decimal import Decimal


class PaymentMethodManager(models.Manager):
    """Custom manager for PaymentMethod model"""
    
    def active(self):
        """Get active payment methods"""
        return self.filter(is_active=True)
    
    def verified(self):
        """Get verified payment methods"""
        return self.filter(is_verified=True)
    
    def default_for_user(self, user):
        """Get default payment method for a user"""
        return self.filter(user=user, is_default=True, is_active=True).first()
    
    def for_user(self, user):
        """Get all payment methods for a user"""
        return self.filter(user=user, is_active=True)
    
    def usable(self, user):
        """Get usable payment methods (active and verified) for a user"""
        return self.filter(user=user, is_active=True, is_verified=True)


class EscrowAccountManager(models.Manager):
    """Custom manager for EscrowAccount model"""
    
    def for_user(self, user):
        """Get escrow account for a user"""
        return self.filter(user=user).first()
    
    def active(self):
        """Get active escrow accounts"""
        return self.filter(is_active=True)
    
    def with_balance(self, min_amount=0):
        """Get escrow accounts with minimum balance"""
        return self.filter(current_balance__gte=min_amount)


class PaymentManager(models.Manager):
    """Custom manager for Payment model"""
    
    def pending(self):
        """Get pending payments"""
        return self.filter(status=self.model.PaymentStatus.PENDING)
    
    def completed(self):
        """Get completed payments"""
        return self.filter(status=self.model.PaymentStatus.COMPLETED)
    
    def failed(self):
        """Get failed payments"""
        return self.filter(status=self.model.PaymentStatus.FAILED)
    
    def refunded(self):
        """Get refunded payments"""
        return self.filter(status=self.model.PaymentStatus.REFUNDED)
    
    def disputed(self):
        """Get disputed payments"""
        return self.filter(status=self.model.PaymentStatus.DISPUTED)
    
    def for_user(self, user):
        """Get payments for a user (as payer or payee)"""
        return self.filter(Q(payer=user) | Q(payee=user))
    
    def sent_by(self, user):
        """Get payments sent by a user"""
        return self.filter(payer=user)
    
    def received_by(self, user):
        """Get payments received by a user"""
        return self.filter(payee=user)
    
    def for_award(self, award):
        """Get payments for a specific award"""
        return self.filter(award=award)
    
    def of_type(self, payment_type):
        """Get payments of a specific type"""
        return self.filter(payment_type=payment_type)
    
    def recent(self, days=30):
        """Get payments from the last N days"""
        since = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=since)


class TransactionManager(models.Manager):
    """Custom manager for Transaction model"""
    
    def for_user(self, user):
        """Get transactions for a user"""
        return self.filter(user=user)
    
    def of_type(self, transaction_type):
        """Get transactions of a specific type"""
        return self.filter(transaction_type=transaction_type)
    
    def deposits(self):
        """Get deposit transactions"""
        return self.filter(transaction_type=self.model.TransactionType.DEPOSIT)
    
    def withdrawals(self):
        """Get withdrawal transactions"""
        return self.filter(transaction_type=self.model.TransactionType.WITHDRAWAL)
    
    def payments_received(self):
        """Get payment received transactions"""
        return self.filter(transaction_type=self.model.TransactionType.PAYMENT_RECEIVED)
    
    def refunds(self):
        """Get refund transactions"""
        return self.filter(
            transaction_type__in=[
                self.model.TransactionType.REFUND_ISSUED,
                self.model.TransactionType.REFUND_RECEIVED
            ]
        )
    
    def recent(self, days=30):
        """Get transactions from the last N days"""
        since = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=since)
    
    def total_for_user(self, user, transaction_type=None):
        """Calculate total amount for a user, optionally filtered by transaction type"""
        queryset = self.for_user(user)
        if transaction_type:
            queryset = queryset.of_type(transaction_type)
        
        result = queryset.aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')


class CommissionManager(models.Manager):
    """Custom manager for Commission model"""
    
    def pending(self):
        """Get pending commissions (not collected)"""
        return self.filter(is_collected=False)
    
    def collected(self):
        """Get collected commissions"""
        return self.filter(is_collected=True)
    
    def of_type(self, commission_type):
        """Get commissions of a specific type"""
        return self.filter(commission_type=commission_type)
    
    def for_payment(self, payment):
        """Get commissions for a specific payment"""
        return self.filter(payment=payment)
    
    def total_pending(self):
        """Calculate total pending commission amount"""
        result = self.pending().aggregate(total=Sum('commission_amount'))
        return result['total'] or Decimal('0.00')
    
    def total_collected(self):
        """Calculate total collected commission amount"""
        result = self.collected().aggregate(total=Sum('commission_amount'))
        return result['total'] or Decimal('0.00')


class RefundManager(models.Manager):
    """Custom manager for Refund model"""
    
    def pending(self):
        """Get pending refunds"""
        return self.filter(status=self.model.RefundStatus.PENDING)
    
    def approved(self):
        """Get approved refunds"""
        return self.filter(status=self.model.RefundStatus.APPROVED)
    
    def processed(self):
        """Get processed refunds"""
        return self.filter(status=self.model.RefundStatus.PROCESSED)
    
    def completed(self):
        """Get completed refunds"""
        return self.filter(status=self.model.RefundStatus.COMPLETED)
    
    def rejected(self):
        """Get rejected refunds"""
        return self.filter(status=self.model.RefundStatus.REJECTED)
    
    def failed(self):
        """Get failed refunds"""
        return self.filter(status=self.model.RefundStatus.FAILED)
    
    def for_payment(self, payment):
        """Get refunds for a specific payment"""
        return self.filter(payment=payment)
    
    def recent(self, days=30):
        """Get refunds from the last N days"""
        since = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=since)
    
    def total_amount(self, status=None):
        """Calculate total refund amount, optionally filtered by status"""
        queryset = self.all()
        if status:
            queryset = queryset.filter(status=status)
        
        result = queryset.aggregate(total=Sum('amount'))
        return result['total'] or Decimal('0.00')


class PayoutManager(models.Manager):
    """Custom manager for Payout model"""
    
    def pending(self):
        """Get pending payouts"""
        return self.filter(status=self.model.PayoutStatus.PENDING)
    
    def processing(self):
        """Get processing payouts"""
        return self.filter(status=self.model.PayoutStatus.PROCESSING)
    
    def completed(self):
        """Get completed payouts"""
        return self.filter(status=self.model.PayoutStatus.COMPLETED)
    
    def failed(self):
        """Get failed payouts"""
        return self.filter(status=self.model.PayoutStatus.FAILED)
    
    def cancelled(self):
        """Get cancelled payouts"""
        return self.filter(status=self.model.PayoutStatus.CANCELLED)
    
    def for_tutor(self, tutor):
        """Get payouts for a specific tutor"""
        return self.filter(tutor=tutor)
    
    def scheduled_for(self, date):
        """Get payouts scheduled for a specific date"""
        return self.filter(scheduled_payout_date=date)
    
    def recent(self, days=30):
        """Get payouts from the last N days"""
        since = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=since)
    
    def total_pending(self):
        """Calculate total pending payout amount"""
        result = self.pending().aggregate(total=Sum('net_amount'))
        return result['total'] or Decimal('0.00')
    
    def total_for_tutor(self, tutor, status=None):
        """Calculate total payout amount for a tutor, optionally filtered by status"""
        queryset = self.for_tutor(tutor)
        if status:
            queryset = queryset.filter(status=status)
        
        result = queryset.aggregate(total=Sum('net_amount'))
        return result['total'] or Decimal('0.00')