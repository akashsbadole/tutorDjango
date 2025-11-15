"""
Unit tests for paymentsdetails app models.
"""
import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from tests.factories import (
    UserFactory, TutorUserFactory, StudentUserFactory,
    PaymentFactory, EscrowTransactionFactory, CommissionRateFactory
)
from tests.utils.helpers import TestMixin, DateTimeTestMixin


class PaymentModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for Payment model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.payer = UserFactory.create()
        self.payee = UserFactory.create()
        
    def test_payment_creation(self):
        """Test payment model creation."""
        payment = PaymentFactory.create(
            payer=self.payer,
            payee=self.payee
        )
        self.assertTrue(isinstance(payment, PaymentFactory._meta.model))
        self.assertEqual(payment.payer, self.payer)
        self.assertEqual(payment.payee, self.payee)
        self.assertEqual(payment.currency, 'USD')
        
    def test_payment_string_representation(self):
        """Test payment string representation."""
        payment = PaymentFactory.create(
            payer=self.payer,
            payee=self.payee,
            amount=Decimal('100.00')
        )
        expected = f"Payment of $100.00 from {self.payer.username} to {self.payee.username}"
        self.assertEqual(str(payment), expected)
        
    def test_payment_amount_validation(self):
        """Test amount field validation."""
        payment = PaymentFactory.build(
            payer=self.payer,
            payee=self.payee
        )
        
        # Test negative amount
        payment.amount = Decimal('-10.00')
        with self.assertRaises(ValidationError):
            payment.full_clean()
            
        # Test zero amount
        payment.amount = Decimal('0.00')
        with self.assertRaises(ValidationError):
            payment.full_clean()
            
    def test_payment_currency_validation(self):
        """Test currency field validation."""
        payment = PaymentFactory.build(
            payer=self.payer,
            payee=self.payee
        )
        
        # Test invalid currency
        payment.currency = 'INVALID'
        with self.assertRaises(ValidationError):
            payment.full_clean()
            
    def test_payment_method_choices(self):
        """Test payment method field choices."""
        payment = PaymentFactory.build(
            payer=self.payer,
            payee=self.payee
        )
        
        valid_methods = ['PAYPAL', 'STRIPE', 'BANK_TRANSFER']
        for method in valid_methods:
            payment.payment_method = method
            payment.full_clean()  # Should not raise
            
        # Test invalid method
        payment.payment_method = 'INVALID'
        with self.assertRaises(ValidationError):
            payment.full_clean()
            
    def test_payment_status_choices(self):
        """Test status field choices."""
        payment = PaymentFactory.build(
            payer=self.payer,
            payee=self.payee
        )
        
        valid_statuses = ['PENDING', 'COMPLETED', 'FAILED', 'REFUNDED']
        for status in valid_statuses:
            payment.status = status
            payment.full_clean()  # Should not raise
            
        # Test invalid status
        payment.status = 'INVALID'
        with self.assertRaises(ValidationError):
            payment.full_clean()
            
    def test_payment_payer_relationship(self):
        """Test payment-payer relationship."""
        payment = PaymentFactory.create(payer=self.payer)
        
        # Test reverse relationship
        self.assertIn(payment, self.payer.payments_made.all())
        
    def test_payment_payee_relationship(self):
        """Test payment-payee relationship."""
        payment = PaymentFactory.create(payee=self.payee)
        
        # Test reverse relationship
        self.assertIn(payment, self.payee.payments_received.all())


class EscrowTransactionModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for EscrowTransaction model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.payment = PaymentFactory.create()
        
    def test_escrow_transaction_creation(self):
        """Test escrow transaction model creation."""
        escrow = EscrowTransactionFactory.create(payment=self.payment)
        self.assertTrue(isinstance(escrow, EscrowTransactionFactory._meta.model))
        self.assertEqual(escrow.payment, self.payment)
        self.assertEqual(escrow.currency, 'USD')
        
    def test_escrow_transaction_string_representation(self):
        """Test escrow transaction string representation."""
        escrow = EscrowTransactionFactory.create(
            payment=self.payment,
            amount=Decimal('100.00'),
            transaction_type='DEPOSIT'
        )
        expected = f"DEPOSIT escrow transaction of $100.00"
        self.assertEqual(str(escrow), expected)
        
    def test_escrow_transaction_amount_validation(self):
        """Test amount field validation."""
        escrow = EscrowTransactionFactory.build(payment=self.payment)
        
        # Test negative amount
        escrow.amount = Decimal('-10.00')
        with self.assertRaises(ValidationError):
            escrow.full_clean()
            
        # Test zero amount
        escrow.amount = Decimal('0.00')
        with self.assertRaises(ValidationError):
            escrow.full_clean()
            
    def test_escrow_transaction_type_choices(self):
        """Test transaction type field choices."""
        escrow = EscrowTransactionFactory.build(payment=self.payment)
        
        valid_types = ['DEPOSIT', 'RELEASE', 'REFUND']
        for trans_type in valid_types:
            escrow.transaction_type = trans_type
            escrow.full_clean()  # Should not raise
            
        # Test invalid type
        escrow.transaction_type = 'INVALID'
        with self.assertRaises(ValidationError):
            escrow.full_clean()
            
    def test_escrow_transaction_status_choices(self):
        """Test status field choices."""
        escrow = EscrowTransactionFactory.build(payment=self.payment)
        
        valid_statuses = ['PENDING', 'COMPLETED', 'FAILED']
        for status in valid_statuses:
            escrow.status = status
            escrow.full_clean()  # Should not raise
            
        # Test invalid status
        escrow.status = 'INVALID'
        with self.assertRaises(ValidationError):
            escrow.full_clean()
            
    def test_escrow_transaction_payment_relationship(self):
        """Test escrow transaction-payment relationship."""
        escrow = EscrowTransactionFactory.create(payment=self.payment)
        
        # Test reverse relationship
        self.assertIn(escrow, self.payment.escrow_transactions.all())


class CommissionRateModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for CommissionRate model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_commission_rate_creation(self):
        """Test commission rate model creation."""
        commission = CommissionRateFactory.create()
        self.assertTrue(isinstance(commission, CommissionRateFactory._meta.model))
        self.assertTrue(commission.is_active)
        
    def test_commission_rate_string_representation(self):
        """Test commission rate string representation."""
        commission = CommissionRateFactory.create(
            user_type='TUTOR',
            rate_percentage=Decimal('10.50')
        )
        expected = f"TUTOR commission rate: 10.50%"
        self.assertEqual(str(commission), expected)
        
    def test_commission_rate_user_type_choices(self):
        """Test user type field choices."""
        commission = CommissionRateFactory.build()
        
        valid_types = ['TUTOR', 'STUDENT', 'PLATFORM']
        for user_type in valid_types:
            commission.user_type = user_type
            commission.full_clean()  # Should not raise
            
        # Test invalid type
        commission.user_type = 'INVALID'
        with self.assertRaises(ValidationError):
            commission.full_clean()
            
    def test_commission_rate_percentage_validation(self):
        """Test rate percentage field validation."""
        commission = CommissionRateFactory.build()
        
        # Test negative rate
        commission.rate_percentage = Decimal('-1.00')
        with self.assertRaises(ValidationError):
            commission.full_clean()
            
        # Test zero rate
        commission.rate_percentage = Decimal('0.00')
        with self.assertRaises(ValidationError):
            commission.full_clean()
            
        # Test rate over 100%
        commission.rate_percentage = Decimal('101.00')
        with self.assertRaises(ValidationError):
            commission.full_clean()
            
    def test_commission_rate_effective_from_validation(self):
        """Test effective from date validation."""
        commission = CommissionRateFactory.build()
        
        # Test future date
        commission.effective_from = self.create_future_date(days=1)
        with self.assertRaises(ValidationError):
            commission.full_clean()
            
    def test_commission_rate_is_active_default(self):
        """Test is_active defaults to True."""
        commission = CommissionRateFactory.build()
        self.assertTrue(commission.is_active)


class PaymentQuerySetTest(TestCase, TestMixin):
    """Test cases for Payment model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_for_user_queryset(self):
        """Test for_user queryset method."""
        # Create payments for user as payer and payee
        payment_made = PaymentFactory.create(payer=self.user)
        payment_received = PaymentFactory.create(payee=self.user)
        other_payment = PaymentFactory.create()  # For different users
        
        # Test as payer
        user_payments = Payment.objects.for_user(self.user)
        self.assertEqual(user_payments.count(), 2)
        self.assertIn(payment_made, user_payments)
        self.assertIn(payment_received, user_payments)
        self.assertNotIn(other_payment, user_payments)
        
    def test_completed_queryset(self):
        """Test completed queryset method."""
        # Create payments with different statuses
        completed = PaymentFactory.create(status='COMPLETED')
        pending = PaymentFactory.create(status='PENDING')
        failed = PaymentFactory.create(status='FAILED')
        
        completed_payments = Payment.objects.completed()
        self.assertEqual(completed_payments.count(), 1)
        self.assertIn(completed, completed_payments)
        self.assertNotIn(pending, completed_payments)
        self.assertNotIn(failed, completed_payments)
        
    def test_pending_queryset(self):
        """Test pending queryset method."""
        # Create payments with different statuses
        completed = PaymentFactory.create(status='COMPLETED')
        pending = PaymentFactory.create(status='PENDING')
        failed = PaymentFactory.create(status='FAILED')
        
        pending_payments = Payment.objects.pending()
        self.assertEqual(pending_payments.count(), 1)
        self.assertIn(pending, pending_payments)
        self.assertNotIn(completed, pending_payments)
        self.assertNotIn(failed, pending_payments)
        
    def test_failed_queryset(self):
        """Test failed queryset method."""
        # Create payments with different statuses
        completed = PaymentFactory.create(status='COMPLETED')
        pending = PaymentFactory.create(status='PENDING')
        failed = PaymentFactory.create(status='FAILED')
        
        failed_payments = Payment.objects.failed()
        self.assertEqual(failed_payments.count(), 1)
        self.assertIn(failed, failed_payments)
        self.assertNotIn(completed, failed_payments)
        self.assertNotIn(pending, failed_payments)
        
    def test_refunded_queryset(self):
        """Test refunded queryset method."""
        # Create payments with different statuses
        completed = PaymentFactory.create(status='COMPLETED')
        refunded = PaymentFactory.create(status='REFUNDED')
        failed = PaymentFactory.create(status='FAILED')
        
        refunded_payments = Payment.objects.refunded()
        self.assertEqual(refunded_payments.count(), 1)
        self.assertIn(refunded, refunded_payments)
        self.assertNotIn(completed, refunded_payments)
        self.assertNotIn(failed, refunded_payments)
        
    def test_by_date_range_queryset(self):
        """Test by_date_range queryset method."""
        # Create payments with different dates
        old_payment = PaymentFactory.create(
            created_at=self.create_past_date(days=10)
        )
        recent_payment = PaymentFactory.create(
            created_at=self.create_past_date(days=2)
        )
        future_payment = PaymentFactory.create(
            created_at=self.create_future_date(days=5)
        )
        
        # Test date range (last 7 days)
        start_date = self.create_past_date(days=7)
        end_date = timezone.now()
        range_payments = Payment.objects.by_date_range(start_date, end_date)
        self.assertEqual(range_payments.count(), 2)
        self.assertIn(recent_payment, range_payments)
        self.assertNotIn(old_payment, range_payments)
        self.assertNotIn(future_payment, range_payments)


class EscrowTransactionQuerySetTest(TestCase, TestMixin):
    """Test cases for EscrowTransaction model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.payment = PaymentFactory.create()
        
    def test_deposits_queryset(self):
        """Test deposits queryset method."""
        # Create transactions with different types
        deposit = EscrowTransactionFactory.create(
            payment=self.payment,
            transaction_type='DEPOSIT'
        )
        release = EscrowTransactionFactory.create(
            payment=self.payment,
            transaction_type='RELEASE'
        )
        refund = EscrowTransactionFactory.create(
            payment=self.payment,
            transaction_type='REFUND'
        )
        
        deposits = EscrowTransaction.objects.deposits()
        self.assertEqual(deposits.count(), 1)
        self.assertIn(deposit, deposits)
        self.assertNotIn(release, deposits)
        self.assertNotIn(refund, deposits)
        
    def test_releases_queryset(self):
        """Test releases queryset method."""
        # Create transactions with different types
        deposit = EscrowTransactionFactory.create(
            payment=self.payment,
            transaction_type='DEPOSIT'
        )
        release = EscrowTransactionFactory.create(
            payment=self.payment,
            transaction_type='RELEASE'
        )
        refund = EscrowTransactionFactory.create(
            payment=self.payment,
            transaction_type='REFUND'
        )
        
        releases = EscrowTransaction.objects.releases()
        self.assertEqual(releases.count(), 1)
        self.assertIn(release, releases)
        self.assertNotIn(deposit, releases)
        self.assertNotIn(refund, releases)
        
    def test_refunds_queryset(self):
        """Test refunds queryset method."""
        # Create transactions with different types
        deposit = EscrowTransactionFactory.create(
            payment=self.payment,
            transaction_type='DEPOSIT'
        )
        release = EscrowTransactionFactory.create(
            payment=self.payment,
            transaction_type='RELEASE'
        )
        refund = EscrowTransactionFactory.create(
            payment=self.payment,
            transaction_type='REFUND'
        )
        
        refunds = EscrowTransaction.objects.refunds()
        self.assertEqual(refunds.count(), 1)
        self.assertIn(refund, refunds)
        self.assertNotIn(deposit, refunds)
        self.assertNotIn(release, refunds)
        
    def test_pending_queryset(self):
        """Test pending queryset method."""
        # Create transactions with different statuses
        pending = EscrowTransactionFactory.create(
            payment=self.payment,
            status='PENDING'
        )
        completed = EscrowTransactionFactory.create(
            payment=self.payment,
            status='COMPLETED'
        )
        failed = EscrowTransactionFactory.create(
            payment=self.payment,
            status='FAILED'
        )
        
        pending_transactions = EscrowTransaction.objects.pending()
        self.assertEqual(pending_transactions.count(), 1)
        self.assertIn(pending, pending_transactions)
        self.assertNotIn(completed, pending_transactions)
        self.assertNotIn(failed, pending_transactions)


class CommissionRateQuerySetTest(TestCase, TestMixin):
    """Test cases for CommissionRate model custom querysets."""
    
    def test_active_queryset(self):
        """Test active queryset method."""
        # Create commission rates with different active status
        active = CommissionRateFactory.create(is_active=True)
        inactive = CommissionRateFactory.create(is_active=False)
        
        active_rates = CommissionRate.objects.active()
        self.assertEqual(active_rates.count(), 1)
        self.assertIn(active, active_rates)
        self.assertNotIn(inactive, active_rates)
        
    def test_for_user_type_queryset(self):
        """Test for_user_type queryset method."""
        # Create commission rates for different user types
        tutor_rate = CommissionRateFactory.create(user_type='TUTOR')
        student_rate = CommissionRateFactory.create(user_type='STUDENT')
        platform_rate = CommissionRateFactory.create(user_type='PLATFORM')
        
        # Test filtering by TUTOR
        tutor_rates = CommissionRate.objects.for_user_type('TUTOR')
        self.assertEqual(tutor_rates.count(), 1)
        self.assertIn(tutor_rate, tutor_rates)
        self.assertNotIn(student_rate, tutor_rates)
        self.assertNotIn(platform_rate, tutor_rates)
        
    def test_current_queryset(self):
        """Test current queryset method."""
        # Create commission rates with different effective dates
        past_rate = CommissionRateFactory.create(
            effective_from=self.create_past_date(days=10)
        )
        current_rate = CommissionRateFactory.create(
            effective_from=self.create_past_date(days=1)
        )
        future_rate = CommissionRateFactory.create(
            effective_from=self.create_future_date(days=5)
        )
        
        # Test current rates (effective before or on today)
        current_rates = CommissionRate.objects.current()
        self.assertEqual(current_rates.count(), 2)
        self.assertIn(past_rate, current_rates)
        self.assertIn(current_rate, current_rates)
        self.assertNotIn(future_rate, current_rates)


class PaymentSignalTest(TestCase, TestMixin):
    """Test cases for Payment model signals."""
    
    def test_payment_created_signal(self):
        """Test payment creation signal."""
        # This would test that payment creation triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_payment_status_change_signal(self):
        """Test payment status change signal."""
        # This would test that status changes trigger
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic


class EscrowTransactionSignalTest(TestCase, TestMixin):
    """Test cases for EscrowTransaction model signals."""
    
    def test_escrow_transaction_created_signal(self):
        """Test escrow transaction creation signal."""
        # This would test that transaction creation triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_escrow_transaction_status_change_signal(self):
        """Test escrow transaction status change signal."""
        # This would test that status changes trigger
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic