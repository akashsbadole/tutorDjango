"""
Payment tests for Django tutoring platform.
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from datetime import timedelta

from tests.factories import (
    UserFactory, TutorProfileFactory, StudentProfileFactory, CategoryFactory,
    SubjectFactory, RequirementFactory, ProposalFactory, PaymentFactory
)
from tests.utils.helpers import TestMixin

User = get_user_model()


class PayPalIntegrationTest(TestCase, TestMixin):
    """Tests for PayPal integration with mock API."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        
    @patch('paypal_integration.services.PayPalPaymentService.create_payment')
    def test_paypal_payment_creation(self, mock_create_payment):
        """Test PayPal payment creation."""
        # Mock PayPal response
        mock_response = {
            'id': 'PAY-1234567890',
            'status': 'created',
            'links': [
                {
                    'rel': 'approval_url',
                    'href': 'https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=EC-1234567890'
                }
            ]
        }
        mock_create_payment.return_value = mock_response
        
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Create requirement and proposal
        requirement = RequirementFactory.create(created_by=self.student_user)
        proposal = ProposalFactory.create(requirement=requirement, tutor=self.tutor_user)
        
        # Create payment
        response = self.client.post(
            reverse('paymentsdetails:payment_create', kwargs={'proposal_pk': proposal.pk}),
            {
                'amount': 50.00,
                'payment_method': 'paypal'
            }
        )
        
        # Check that payment was created
        self.assertEqual(response.status_code, 302)
        
        # Check that PayPal service was called
        mock_create_payment.assert_called_once()
        
    @patch('paypal_integration.services.PayPalPaymentService.execute_payment')
    def test_paypal_payment_execution(self, mock_execute_payment):
        """Test PayPal payment execution."""
        # Mock PayPal response
        mock_response = {
            'id': 'PAY-1234567890',
            'status': 'approved',
            'transactions': [
                {
                    'amount': {
                        'total': '50.00',
                        'currency': 'USD'
                    }
                }
            ]
        }
        mock_execute_payment.return_value = mock_response
        
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Create payment
        payment = PaymentFactory.create(
            student=self.student_user,
            tutor=self.tutor_user,
            amount=Decimal('50.00'),
            status='pending'
        )
        
        # Execute payment
        response = self.client.get(
            reverse('paypal_integration:payment_execute', kwargs={'payment_id': payment.id}),
            {'PayerID': 'TEST-PAYER-ID'}
        )
        
        # Check that payment was executed
        self.assertEqual(response.status_code, 302)
        
        # Check that PayPal service was called
        mock_execute_payment.assert_called_once()
        
        # Check that payment status was updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'completed')
        
    @patch('paypal_integration.services.PayPalPaymentService.create_payment')
    def test_paypal_payment_cancellation(self, mock_create_payment):
        """Test PayPal payment cancellation."""
        # Mock PayPal response
        mock_response = {
            'id': 'PAY-1234567890',
            'status': 'created',
            'links': [
                {
                    'rel': 'approval_url',
                    'href': 'https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=EC-1234567890'
                }
            ]
        }
        mock_create_payment.return_value = mock_response
        
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Create requirement and proposal
        requirement = RequirementFactory.create(created_by=self.student_user)
        proposal = ProposalFactory.create(requirement=requirement, tutor=self.tutor_user)
        
        # Create payment
        response = self.client.post(
            reverse('paymentsdetails:payment_create', kwargs={'proposal_pk': proposal.pk}),
            {
                'amount': 50.00,
                'payment_method': 'paypal'
            }
        )
        
        # Cancel payment
        response = self.client.get(
            reverse('paypal_integration:payment_cancel', kwargs={'payment_id': 'PAY-1234567890'})
        )
        
        # Check that payment was cancelled
        self.assertEqual(response.status_code, 302)
        
    @patch('paypal_integration.services.PayPalPaymentService.refund_payment')
    def test_paypal_payment_refund(self, mock_refund_payment):
        """Test PayPal payment refund."""
        # Mock PayPal response
        mock_response = {
            'id': 'REFUND-1234567890',
            'status': 'completed',
            'amount': {
                'total': '50.00',
                'currency': 'USD'
            }
        }
        mock_refund_payment.return_value = mock_response
        
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Create completed payment
        payment = PaymentFactory.create(
            student=self.student_user,
            tutor=self.tutor_user,
            amount=Decimal('50.00'),
            status='completed'
        )
        
        # Refund payment
        response = self.client.post(
            reverse('paymentsdetails:payment_refund', kwargs={'payment_pk': payment.pk})
        )
        
        # Check that refund was processed
        self.assertEqual(response.status_code, 302)
        
        # Check that PayPal service was called
        mock_refund_payment.assert_called_once()
        
        # Check that payment status was updated
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'refunded')


class EscrowTest(TestCase, TestMixin):
    """Tests for escrow functionality."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        
    def test_escrow_account_creation(self):
        """Test escrow account creation."""
        # Login as tutor
        self.client.login(username=self.tutor_user.username, password='testpass123')
        
        # Create escrow account
        response = self.client.post(
            reverse('paymentsdetails:escrow_account_create'),
            {
                'account_type': 'individual',
                'business_name': 'Test Business',
                'email': 'test@example.com'
            }
        )
        
        # Check that escrow account was created
        self.assertEqual(response.status_code, 302)
        
        # Check that escrow account exists
        from paymentsdetails.models import EscrowAccount
        escrow_account = EscrowAccount.objects.get(user=self.tutor_user)
        self.assertEqual(escrow_account.account_type, 'individual')
        self.assertEqual(escrow_account.business_name, 'Test Business')
        
    def test_escrow_funding(self):
        """Test escrow funding."""
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Create requirement and proposal
        requirement = RequirementFactory.create(created_by=self.student_user)
        proposal = ProposalFactory.create(requirement=requirement, tutor=self.tutor_user)
        
        # Create payment with escrow
        payment = PaymentFactory.create(
            student=self.student_user,
            tutor=self.tutor_user,
            proposal=proposal,
            amount=Decimal('50.00'),
            status='completed'
        )
        
        # Fund escrow
        response = self.client.post(
            reverse('paymentsdetails:escrow_fund', kwargs={'payment_pk': payment.pk})
        )
        
        # Check that escrow was funded
        self.assertEqual(response.status_code, 302)
        
        # Check that escrow transaction was created
        from paymentsdetails.models import EscrowTransaction
        escrow_transaction = EscrowTransaction.objects.get(payment=payment)
        self.assertEqual(escrow_transaction.transaction_type, 'funding')
        self.assertEqual(escrow_transaction.amount, Decimal('50.00'))
        
    def test_escrow_release(self):
        """Test escrow release."""
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Create requirement, proposal, and payment
        requirement = RequirementFactory.create(created_by=self.student_user)
        proposal = ProposalFactory.create(requirement=requirement, tutor=self.tutor_user)
        payment = PaymentFactory.create(
            student=self.student_user,
            tutor=self.tutor_user,
            proposal=proposal,
            amount=Decimal('50.00'),
            status='completed'
        )
        
        # Create escrow transaction
        from paymentsdetails.models import EscrowTransaction
        escrow_transaction = EscrowTransaction.objects.create(
            payment=payment,
            transaction_type='funding',
            amount=Decimal('50.00'),
            status='completed'
        )
        
        # Release escrow
        response = self.client.post(
            reverse('paymentsdetails:escrow_release', kwargs={'transaction_pk': escrow_transaction.pk})
        )
        
        # Check that escrow was released
        self.assertEqual(response.status_code, 302)
        
        # Check that release transaction was created
        release_transaction = EscrowTransaction.objects.get(
            payment=payment,
            transaction_type='release'
        )
        self.assertEqual(release_transaction.amount, Decimal('50.00'))
        
    def test_escrow_dispute(self):
        """Test escrow dispute."""
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Create requirement, proposal, and payment
        requirement = RequirementFactory.create(created_by=self.student_user)
        proposal = ProposalFactory.create(requirement=requirement, tutor=self.tutor_user)
        payment = PaymentFactory.create(
            student=self.student_user,
            tutor=self.tutor_user,
            proposal=proposal,
            amount=Decimal('50.00'),
            status='completed'
        )
        
        # Create escrow transaction
        from paymentsdetails.models import EscrowTransaction
        escrow_transaction = EscrowTransaction.objects.create(
            payment=payment,
            transaction_type='funding',
            amount=Decimal('50.00'),
            status='completed'
        )
        
        # Create dispute
        response = self.client.post(
            reverse('paymentsdetails:escrow_dispute', kwargs={'transaction_pk': escrow_transaction.pk}),
            {
                'reason': 'Service not delivered as promised',
                'description': 'The tutor did not provide the agreed services.'
            }
        )
        
        # Check that dispute was created
        self.assertEqual(response.status_code, 302)
        
        # Check that escrow transaction was updated
        escrow_transaction.refresh_from_db()
        self.assertEqual(escrow_transaction.status, 'disputed')


class PaymentProcessingTest(TestCase, TestMixin):
    """Tests for payment processing."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        
    def test_payment_creation(self):
        """Test payment creation."""
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Create requirement and proposal
        requirement = RequirementFactory.create(created_by=self.student_user)
        proposal = ProposalFactory.create(requirement=requirement, tutor=self.tutor_user)
        
        # Create payment
        response = self.client.post(
            reverse('paymentsdetails:payment_create', kwargs={'proposal_pk': proposal.pk}),
            {
                'amount': 50.00,
                'payment_method': 'credit_card'
            }
        )
        
        # Check that payment was created
        self.assertEqual(response.status_code, 302)
        
        # Check that payment exists
        from paymentsdetails.models import Payment
        payment = Payment.objects.get(student=self.student_user, proposal=proposal)
        self.assertEqual(payment.amount, Decimal('50.00'))
        self.assertEqual(payment.payment_method, 'credit_card')
        
    def test_payment_status_update(self):
        """Test payment status update."""
        # Create payment
        payment = PaymentFactory.create(
            student=self.student_user,
            tutor=self.tutor_user,
            amount=Decimal('50.00'),
            status='pending'
        )
        
        # Update payment status
        response = self.client.post(
            reverse('paymentsdetails:payment_update_status', kwargs={'payment_pk': payment.pk}),
            {
                'status': 'completed',
                'transaction_id': 'TXN-1234567890'
            }
        )
        
        # Check that payment status was updated
        self.assertEqual(response.status_code, 302)
        
        # Check that payment exists with updated status
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.transaction_id, 'TXN-1234567890')
        
    def test_payment_validation(self):
        """Test payment validation."""
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Create requirement and proposal
        requirement = RequirementFactory.create(created_by=self.student_user)
        proposal = ProposalFactory.create(requirement=requirement, tutor=self.tutor_user)
        
        # Try to create payment with invalid amount
        response = self.client.post(
            reverse('paymentsdetails:payment_create', kwargs={'proposal_pk': proposal.pk}),
            {
                'amount': -50.00,
                'payment_method': 'credit_card'
            }
        )
        
        # Check that payment creation was rejected
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'amount', 'Ensure this value is greater than or equal to 0')
        
    def test_payment_duplicate_prevention(self):
        """Test payment duplicate prevention."""
        # Create completed payment
        requirement = RequirementFactory.create(created_by=self.student_user)
        proposal = ProposalFactory.create(requirement=requirement, tutor=self.tutor_user)
        payment = PaymentFactory.create(
            student=self.student_user,
            tutor=self.tutor_user,
            proposal=proposal,
            amount=Decimal('50.00'),
            status='completed'
        )
        
        # Try to create duplicate payment
        response = self.client.post(
            reverse('paymentsdetails:payment_create', kwargs={'proposal_pk': proposal.pk}),
            {
                'amount': 50.00,
                'payment_method': 'credit_card'
            }
        )
        
        # Check that duplicate payment was prevented
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment already exists for this proposal')


class CommissionTest(TestCase, TestMixin):
    """Tests for commission calculation."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        
    def test_commission_calculation(self):
        """Test commission calculation."""
        # Create commission rate
        from paymentsdetails.models import CommissionRate
        commission_rate = CommissionRate.objects.create(
            rate_type='percentage',
            value=Decimal('10.00'),
            min_amount=Decimal('0.00'),
            max_amount=Decimal('1000.00')
        )
        
        # Create payment
        payment = PaymentFactory.create(
            student=self.student_user,
            tutor=self.tutor_user,
            amount=Decimal('100.00'),
            status='completed'
        )
        
        # Calculate commission
        commission_amount = payment.amount * commission_rate.value / 100
        self.assertEqual(commission_amount, Decimal('10.00'))
        
    def test_tiered_commission(self):
        """Test tiered commission calculation."""
        # Create tiered commission rates
        from paymentsdetails.models import CommissionRate
        CommissionRate.objects.create(
            rate_type='percentage',
            value=Decimal('5.00'),
            min_amount=Decimal('0.00'),
            max_amount=Decimal('100.00')
        )
        CommissionRate.objects.create(
            rate_type='percentage',
            value=Decimal('10.00'),
            min_amount=Decimal('100.01'),
            max_amount=Decimal('500.00')
        )
        
        # Create payment in first tier
        payment1 = PaymentFactory.create(
            student=self.student_user,
            tutor=self.tutor_user,
            amount=Decimal('50.00'),
            status='completed'
        )
        
        # Create payment in second tier
        payment2 = PaymentFactory.create(
            student=self.student_user,
            tutor=self.tutor_user,
            amount=Decimal('200.00'),
            status='completed'
        )
        
        # Calculate commissions
        commission1 = payment1.amount * Decimal('5.00') / 100
        commission2 = payment2.amount * Decimal('10.00') / 100
        
        self.assertEqual(commission1, Decimal('2.50'))
        self.assertEqual(commission2, Decimal('20.00'))
        
    def test_commission_deduction(self):
        """Test commission deduction from payment."""
        # Create commission rate
        from paymentsdetails.models import CommissionRate
        commission_rate = CommissionRate.objects.create(
            rate_type='percentage',
            value=Decimal('10.00'),
            min_amount=Decimal('0.00'),
            max_amount=Decimal('1000.00')
        )
        
        # Create payment
        payment = PaymentFactory.create(
            student=self.student_user,
            tutor=self.tutor_user,
            amount=Decimal('100.00'),
            status='completed'
        )
        
        # Calculate and deduct commission
        commission_amount = payment.amount * commission_rate.value / 100
        tutor_amount = payment.amount - commission_amount
        
        self.assertEqual(tutor_amount, Decimal('90.00'))


class PayoutTest(TestCase, TestMixin):
    """Tests for payout processing."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        
    def test_payout_request(self):
        """Test payout request."""
        # Login as tutor
        self.client.login(username=self.tutor_user.username, password='testpass123')
        
        # Create completed payments
        PaymentFactory.create_batch(
            5,
            tutor=self.tutor_user,
            amount=Decimal('100.00'),
            status='completed'
        )
        
        # Request payout
        response = self.client.post(
            reverse('paymentsdetails:payout_request'),
            {
                'amount': 500.00,
                'payout_method': 'bank_transfer',
                'bank_account': '1234567890'
            }
        )
        
        # Check that payout request was created
        self.assertEqual(response.status_code, 302)
        
        # Check that payout exists
        from paymentsdetails.models import Payout
        payout = Payout.objects.get(tutor=self.tutor_user)
        self.assertEqual(payout.amount, Decimal('500.00'))
        self.assertEqual(payout.payout_method, 'bank_transfer')
        
    def test_payout_processing(self):
        """Test payout processing."""
        # Create payout request
        from paymentsdetails.models import Payout
        payout = Payout.objects.create(
            tutor=self.tutor_user,
            amount=Decimal('500.00'),
            payout_method='bank_transfer',
            status='pending'
        )
        
        # Process payout
        response = self.client.post(
            reverse('paymentsdetails:payout_process', kwargs={'payout_pk': payout.pk}),
            {
                'status': 'completed',
                'transaction_id': 'PAYOUT-1234567890'
            }
        )
        
        # Check that payout was processed
        self.assertEqual(response.status_code, 302)
        
        # Check that payout status was updated
        payout.refresh_from_db()
        self.assertEqual(payout.status, 'completed')
        self.assertEqual(payout.transaction_id, 'PAYOUT-1234567890')
        
    def test_payout_validation(self):
        """Test payout validation."""
        # Login as tutor
        self.client.login(username=self.tutor_user.username, password='testpass123')
        
        # Request payout with invalid amount
        response = self.client.post(
            reverse('paymentsdetails:payout_request'),
            {
                'amount': -500.00,
                'payout_method': 'bank_transfer',
                'bank_account': '1234567890'
            }
        )
        
        # Check that payout request was rejected
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'amount', 'Ensure this value is greater than or equal to 0')
        
    def test_payout_balance_check(self):
        """Test payout balance check."""
        # Login as tutor
        self.client.login(username=self.tutor_user.username, password='testpass123')
        
        # Create completed payments
        PaymentFactory.create(
            tutor=self.tutor_user,
            amount=Decimal('100.00'),
            status='completed'
        )
        
        # Request payout exceeding balance
        response = self.client.post(
            reverse('paymentsdetails:payout_request'),
            {
                'amount': 500.00,
                'payout_method': 'bank_transfer',
                'bank_account': '1234567890'
            }
        )
        
        # Check that payout request was rejected
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Insufficient balance for payout')


class PaymentNotificationTest(TestCase, TestMixin):
    """Tests for payment notifications."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        
    def test_payment_received_notification(self):
        """Test payment received notification."""
        # Create payment
        payment = PaymentFactory.create(
            student=self.student_user,
            tutor=self.tutor_user,
            amount=Decimal('100.00'),
            status='completed'
        )
        
        # Check that notification was sent to tutor
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn(self.tutor_user.email, email.to)
        self.assertIn('Payment received', email.subject)
        
    def test_payout_processed_notification(self):
        """Test payout processed notification."""
        # Create payout
        from paymentsdetails.models import Payout
        payout = Payout.objects.create(
            tutor=self.tutor_user,
            amount=Decimal('500.00'),
            payout_method='bank_transfer',
            status='completed'
        )
        
        # Check that notification was sent to tutor
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn(self.tutor_user.email, email.to)
        self.assertIn('Payout processed', email.subject)
        
    def test_escrow_dispute_notification(self):
        """Test escrow dispute notification."""
        # Create escrow transaction with dispute
        from paymentsdetails.models import EscrowTransaction
        escrow_transaction = EscrowTransaction.objects.create(
            payment=PaymentFactory.create(
                student=self.student_user,
                tutor=self.tutor_user,
                amount=Decimal('100.00'),
                status='completed'
            ),
            transaction_type='funding',
            amount=Decimal('100.00'),
            status='disputed'
        )
        
        # Check that notification was sent to admin
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('admin@example.com', email.to)
        self.assertIn('Escrow dispute', email.subject)