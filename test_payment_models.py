#!/usr/bin/env python
"""
Test script to verify payment models are working correctly.
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.join(os.path.dirname(__file__), 'tutor_platform'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tutor_platform.settings')
django.setup()

from decimal import Decimal
from django.contrib.auth import get_user_model
from paymentsdetails.models import (
    Payment, EscrowAccount, Transaction, PaymentMethod, 
    Commission, Refund, Payout
)

User = get_user_model()

def test_models():
    """Test creating and using payment models"""
    print("Testing payment models...")
    
    # Create test users
    try:
        student = User.objects.get(username='teststudent')
    except User.DoesNotExist:
        student = User.objects.create_user(
            username='teststudent',
            email='student@example.com',
            password='testpass123',
            user_type='STUDENT',
            first_name='Test',
            last_name='Student'
        )
    
    try:
        tutor = User.objects.get(username='testtutor')
    except User.DoesNotExist:
        tutor = User.objects.create_user(
            username='testtutor',
            email='tutor@example.com',
            password='testpass123',
            user_type='TUTOR',
            first_name='Test',
            last_name='Tutor'
        )
    
    print(f"Created test users: {student.get_full_name()} and {tutor.get_full_name()}")
    
    # Create payment method
    payment_method = PaymentMethod.objects.create(
        user=student,
        method_type=PaymentMethod.MethodType.STRIPE,
        method_details={
            'card_last4': '1234',
            'card_brand': 'visa',
            'card_exp_month': 12,
            'card_exp_year': 2025,
        },
        display_name='Visa ending in 1234',
        is_default=True,
        is_verified=True
    )
    print(f"Created payment method: {payment_method}")
    
    # Create escrow account for student
    escrow_account, created = EscrowAccount.objects.get_or_create(
        user=student,
        defaults={'currency': 'USD'}
    )
    print(f"Created escrow account: {escrow_account}")
    
    # Add funds to escrow
    escrow_account.add_funds(Decimal('100.00'))
    print(f"Added funds to escrow. Current balance: {escrow_account.current_balance}")
    
    # Create a payment
    payment = Payment.objects.create(
        payer=student,
        payee=tutor,
        amount=Decimal('50.00'),
        currency='USD',
        payment_type=Payment.PaymentType.SESSION_PAYMENT,
        payment_method=payment_method,
        description='Payment for tutoring session'
    )
    print(f"Created payment: {payment}")
    
    # Mark payment as completed
    payment.mark_completed()
    print(f"Payment completed. Status: {payment.status}")
    
    # Check student's escrow balance after payment
    escrow_account.refresh_from_db()
    print(f"Student's escrow balance after payment: {escrow_account.current_balance}")
    
    # Create a commission
    commission = Commission.objects.create(
        payment=payment,
        commission_type=Commission.CommissionType.PLATFORM_FEE,
        commission_amount=Decimal('2.50'),
        currency='USD',
        commission_rate=Decimal('0.05'),
        calculated_on_amount=Decimal('50.00'),
        description='Platform fee for session payment'
    )
    print(f"Created commission: {commission}")
    
    # Create a payout for tutor
    payout = Payout.objects.create(
        tutor=tutor,
        total_amount=Decimal('47.50'),
        currency='USD',
        payout_method=payment_method,
        processing_fees=Decimal('0.00'),
        net_amount=Decimal('47.50')
    )
    print(f"Created payout: {payout}")
    
    # Process payout
    payout.process(transaction_reference='TX12345')
    payout.complete()
    print(f"Payout processed. Status: {payout.status}")
    
    # Create a refund
    refund = Refund.objects.create(
        payment=payment,
        amount=Decimal('25.00'),
        currency='USD',
        reason='Student requested partial refund',
        refund_method=payment_method
    )
    print(f"Created refund: {refund}")
    
    # Process refund
    refund.approve(processed_by=student)
    refund.process(refund_transaction_id='RF12345')
    refund.complete()
    print(f"Refund processed. Status: {refund.status}")
    
    # Check transactions
    transactions = Transaction.objects.filter(user=student)
    print(f"Student has {transactions.count()} transactions:")
    for transaction in transactions:
        print(f"  - {transaction.transaction_type}: {transaction.amount} {transaction.currency}")
    
    print("\nAll payment models are working correctly!")

if __name__ == '__main__':
    test_models()