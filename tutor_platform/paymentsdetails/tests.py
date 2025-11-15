"""
Tests for payment models and utilities.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from .models import (
    Payment, EscrowAccount, Transaction, PaymentMethod,
    Commission, Refund, Payout
)
from .utils import (
    calculate_commission, process_escrow_payment, release_escrow_funds,
    create_payout, process_refund, get_user_balance_summary,
    validate_payment_method, calculate_processing_fees
)

User = get_user_model()


class PaymentModelTest(TestCase):
    """Test Payment model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.student = User.objects.create_user(
            username='student',
            email='student@example.com',
            user_type='STUDENT',
            password='testpass123'
        )
        self.tutor = User.objects.create_user(
            username='tutor',
            email='tutor@example.com',
            user_type='TUTOR',
            password='testpass123'
        )
    
    def test_payment_creation(self):
        """Test payment creation."""
        payment = Payment.objects.create(
            payer=self.student,
            payee=self.tutor,
            amount=Decimal('100.00'),
            payment_type=Payment.PaymentType.SESSION_PAYMENT,
            description='Test payment'
        )
        
        self.assertEqual(payment.payer, self.student)
        self.assertEqual(payment.payee, self.tutor)
        self.assertEqual(payment.amount, Decimal('100.00'))
        self.assertEqual(payment.status, Payment.PaymentStatus.PENDING)
    
    def test_payment_str_representation(self):
        """Test payment string representation."""
        payment = Payment.objects.create(
            payer=self.student,
            payee=self.tutor,
            amount=Decimal('100.00'),
            payment_type=Payment.PaymentType.SESSION_PAYMENT
        )
        
        expected = f"Payment {payment.id} - 100.00 USD from {self.student.get_full_name()} to {self.tutor.get_full_name()}"
        self.assertEqual(str(payment), expected)
    
    def test_mark_completed(self):
        """Test marking payment as completed."""
        payment = Payment.objects.create(
            payer=self.student,
            payee=self.tutor,
            amount=Decimal('100.00'),
            payment_type=Payment.PaymentType.SESSION_PAYMENT
        )
        
        # Mark as completed
        payment.mark_completed()
        
        # Refresh from database
        payment.refresh_from_db()
        
        self.assertEqual(payment.status, Payment.PaymentStatus.COMPLETED)
        self.assertIsNotNone(payment.completed_at)
        
        # Check transaction was created
        self.assertTrue(
            Transaction.objects.filter(
                user=self.tutor,
                payment=payment,
                transaction_type=Transaction.TransactionType.PAYMENT_RECEIVED
            ).exists()
        )


class EscrowAccountModelTest(TestCase):
    """Test EscrowAccount model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            user_type='STUDENT',
            password='testpass123'
        )
        self.escrow = EscrowAccount.objects.create(
            user=self.user,
            currency='USD'
        )
    
    def test_escrow_creation(self):
        """Test escrow account creation."""
        self.assertEqual(self.escrow.user, self.user)
        self.assertEqual(self.escrow.currency, 'USD')
        self.assertEqual(self.escrow.current_balance, Decimal('0.00'))
    
    def test_add_funds(self):
        """Test adding funds to escrow."""
        self.escrow.add_funds(Decimal('100.00'))
        
        # Refresh from database
        self.escrow.refresh_from_db()
        
        self.assertEqual(self.escrow.current_balance, Decimal('100.00'))
        self.assertEqual(self.escrow.total_deposited, Decimal('100.00'))
        
        # Check transaction was created
        self.assertTrue(
            Transaction.objects.filter(
                user=self.user,
                transaction_type=Transaction.TransactionType.DEPOSIT,
                amount=Decimal('100.00')
            ).exists()
        )
    
    def test_withdraw_funds(self):
        """Test withdrawing funds from escrow."""
        # First add funds
        self.escrow.add_funds(Decimal('100.00'))
        
        # Then withdraw
        self.escrow.withdraw_funds(Decimal('50.00'))
        
        # Refresh from database
        self.escrow.refresh_from_db()
        
        self.assertEqual(self.escrow.current_balance, Decimal('50.00'))
        self.assertEqual(self.escrow.total_withdrawn, Decimal('50.00'))
    
    def test_insufficient_balance(self):
        """Test withdrawing with insufficient balance."""
        with self.assertRaises(Exception):
            self.escrow.withdraw_funds(Decimal('100.00'))


class PaymentMethodModelTest(TestCase):
    """Test PaymentMethod model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            user_type='STUDENT',
            password='testpass123'
        )
    
    def test_payment_method_creation(self):
        """Test payment method creation."""
        method = PaymentMethod.objects.create(
            user=self.user,
            method_type=PaymentMethod.MethodType.STRIPE,
            display_name='Visa ending in 1234',
            is_default=True,
            method_details={
                'card_last4': '1234',
                'card_brand': 'visa'
            }
        )
        
        self.assertEqual(method.user, self.user)
        self.assertEqual(method.method_type, PaymentMethod.MethodType.STRIPE)
        self.assertTrue(method.is_default)
    
    def test_single_default_method(self):
        """Test only one default method per user."""
        method1 = PaymentMethod.objects.create(
            user=self.user,
            method_type=PaymentMethod.MethodType.STRIPE,
            is_default=True
        )
        
        method2 = PaymentMethod.objects.create(
            user=self.user,
            method_type=PaymentMethod.MethodType.PAYPAL,
            is_default=True
        )
        
        # Refresh from database
        method1.refresh_from_db()
        method2.refresh_from_db()
        
        # Only method2 should be default
        self.assertFalse(method1.is_default)
        self.assertTrue(method2.is_default)


class CommissionModelTest(TestCase):
    """Test Commission model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.student = User.objects.create_user(
            username='student',
            email='student@example.com',
            user_type='STUDENT',
            password='testpass123'
        )
        self.tutor = User.objects.create_user(
            username='tutor',
            email='tutor@example.com',
            user_type='TUTOR',
            password='testpass123'
        )
        self.payment = Payment.objects.create(
            payer=self.student,
            payee=self.tutor,
            amount=Decimal('100.00'),
            payment_type=Payment.PaymentType.SESSION_PAYMENT
        )
    
    def test_commission_creation(self):
        """Test commission creation."""
        commission = Commission.objects.create(
            payment=self.payment,
            commission_type=Commission.CommissionType.PLATFORM_FEE,
            commission_amount=Decimal('10.00'),
            currency='USD',
            commission_rate=Decimal('0.10'),
            calculated_on_amount=Decimal('100.00')
        )
        
        self.assertEqual(commission.payment, self.payment)
        self.assertEqual(commission.commission_amount, Decimal('10.00'))
        self.assertEqual(commission.commission_rate, Decimal('0.10'))
        self.assertFalse(commission.is_collected)
    
    def test_mark_collected(self):
        """Test marking commission as collected."""
        commission = Commission.objects.create(
            payment=self.payment,
            commission_type=Commission.CommissionType.PLATFORM_FEE,
            commission_amount=Decimal('10.00'),
            currency='USD',
            commission_rate=Decimal('0.10'),
            calculated_on_amount=Decimal('100.00')
        )
        
        # Mark as collected
        commission.mark_collected()
        
        # Refresh from database
        commission.refresh_from_db()
        
        self.assertTrue(commission.is_collected)
        self.assertIsNotNone(commission.collected_at)
        
        # Check transaction was created
        self.assertTrue(
            Transaction.objects.filter(
                user=self.student,
                payment=self.payment,
                transaction_type=Transaction.TransactionType.COMMISSION_DEDUCTED
            ).exists()
        )


class RefundModelTest(TestCase):
    """Test Refund model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.student = User.objects.create_user(
            username='student',
            email='student@example.com',
            user_type='STUDENT',
            password='testpass123'
        )
        self.tutor = User.objects.create_user(
            username='tutor',
            email='tutor@example.com',
            user_type='TUTOR',
            password='testpass123'
        )
        self.payment = Payment.objects.create(
            payer=self.student,
            payee=self.tutor,
            amount=Decimal('100.00'),
            payment_type=Payment.PaymentType.SESSION_PAYMENT,
            status=Payment.PaymentStatus.COMPLETED
        )
    
    def test_refund_creation(self):
        """Test refund creation."""
        refund = Refund.objects.create(
            payment=self.payment,
            amount=Decimal('50.00'),
            currency='USD',
            reason='Service not as described'
        )
        
        self.assertEqual(refund.payment, self.payment)
        self.assertEqual(refund.amount, Decimal('50.00'))
        self.assertEqual(refund.status, Refund.RefundStatus.PENDING)
    
    def test_refund_workflow(self):
        """Test complete refund workflow."""
        refund = Refund.objects.create(
            payment=self.payment,
            amount=Decimal('50.00'),
            currency='USD',
            reason='Service not as described'
        )
        
        # Approve
        refund.approve()
        self.assertEqual(refund.status, Refund.RefundStatus.APPROVED)
        
        # Process
        refund.process()
        self.assertEqual(refund.status, Refund.RefundStatus.PROCESSED)
        
        # Complete
        refund.complete()
        self.assertEqual(refund.status, Refund.RefundStatus.COMPLETED)
        
        # Check payment status updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.PaymentStatus.PARTIALLY_REFUNDED)


class PayoutModelTest(TestCase):
    """Test Payout model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.tutor = User.objects.create_user(
            username='tutor',
            email='tutor@example.com',
            user_type='TUTOR',
            password='testpass123'
        )
        self.escrow = EscrowAccount.objects.create(
            user=self.tutor,
            current_balance=Decimal('200.00'),
            currency='USD'
        )
    
    def test_payout_creation(self):
        """Test payout creation."""
        payout = Payout.objects.create(
            tutor=self.tutor,
            total_amount=Decimal('100.00'),
            currency='USD',
            processing_fees=Decimal('5.00'),
            net_amount=Decimal('95.00')
        )
        
        self.assertEqual(payout.tutor, self.tutor)
        self.assertEqual(payout.total_amount, Decimal('100.00'))
        self.assertEqual(payout.net_amount, Decimal('95.00'))
        self.assertEqual(payout.status, Payout.PayoutStatus.PENDING)
    
    def test_payout_workflow(self):
        """Test complete payout workflow."""
        payout = Payout.objects.create(
            tutor=self.tutor,
            total_amount=Decimal('100.00'),
            currency='USD',
            processing_fees=Decimal('5.00')
        )
        
        # Process
        payout.process()
        self.assertEqual(payout.status, Payout.PayoutStatus.PROCESSING)
        
        # Complete
        payout.complete()
        self.assertEqual(payout.status, Payout.PayoutStatus.COMPLETED)
        
        # Check transaction was created
        self.assertTrue(
            Transaction.objects.filter(
                user=self.tutor,
                transaction_type=Transaction.TransactionType.PAYOUT_PROCESSED,
                amount=Decimal('95.00')
            ).exists()
        )


class PaymentUtilsTest(TestCase):
    """Test payment utility functions."""
    
    def setUp(self):
        """Set up test data."""
        self.student = User.objects.create_user(
            username='student',
            email='student@example.com',
            user_type='STUDENT',
            password='testpass123'
        )
        self.tutor = User.objects.create_user(
            username='tutor',
            email='tutor@example.com',
            user_type='TUTOR',
            password='testpass123'
        )
    
    def test_calculate_commission(self):
        """Test commission calculation."""
        amount = Decimal('100.00')
        rate = Decimal('0.10')
        
        commission = calculate_commission(amount, rate)
        self.assertEqual(commission, Decimal('10.00'))
    
    def test_process_escrow_payment(self):
        """Test escrow payment processing."""
        payment, escrow = process_escrow_payment(
            payer=self.student,
            payee=self.tutor,
            amount=Decimal('100.00')
        )
        
        self.assertEqual(payment.payment_type, Payment.PaymentType.ESCROW_DEPOSIT)
        self.assertEqual(payment.status, Payment.PaymentStatus.PENDING)
        
        # Check funds were held
        escrow.refresh_from_db()
        self.assertEqual(escrow.pending_balance, Decimal('100.00'))
    
    def test_release_escrow_funds(self):
        """Test escrow fund release."""
        # First create payment
        payment, escrow = process_escrow_payment(
            payer=self.student,
            payee=self.tutor,
            amount=Decimal('100.00')
        )
        
        # Release funds
        commission, updated_payment = release_escrow_funds(payment)
        
        # Check commission was created
        self.assertEqual(commission.commission_amount, Decimal('10.00'))
        
        # Check payment was completed
        self.assertEqual(updated_payment.status, Payment.PaymentStatus.COMPLETED)
    
    def test_get_user_balance_summary(self):
        """Test balance summary calculation."""
        # Create escrow account
        escrow = EscrowAccount.objects.create(
            user=self.tutor,
            current_balance=Decimal('100.00'),
            total_deposited=Decimal('200.00'),
            total_withdrawn=Decimal('100.00'),
            currency='USD'
        )
        
        # Create completed payment
        payment = Payment.objects.create(
            payer=self.student,
            payee=self.tutor,
            amount=Decimal('50.00'),
            status=Payment.PaymentStatus.COMPLETED
        )
        
        # Get summary
        summary = get_user_balance_summary(self.tutor)
        
        self.assertEqual(summary['current_balance'], Decimal('100.00'))
        self.assertEqual(summary['total_deposited'], Decimal('200.00'))
        self.assertEqual(summary['total_withdrawn'], Decimal('100.00'))
        self.assertEqual(summary['total_earned'], Decimal('50.00'))
    
    def test_calculate_processing_fees(self):
        """Test processing fee calculation."""
        amount = Decimal('100.00')
        
        # Default fee structure
        fees = calculate_processing_fees(amount)
        
        # Should be $0.30 + 2.9% = $3.20
        self.assertEqual(fees, Decimal('3.20'))
        
        # Test with max fee
        fee_structure = {
            'flat_fee': Decimal('0.30'),
            'percentage_fee': Decimal('0.05'),
            'max_fee': Decimal('5.00')
        }
        fees = calculate_processing_fees(amount, fee_structure)
        
        # 5% of $100 is $5.00, which equals max
        self.assertEqual(fees, Decimal('5.00'))
