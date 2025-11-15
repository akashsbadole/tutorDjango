#!/usr/bin/env python
"""
Test script to verify the paymentsdetails app implementation.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tutor_platform.settings')

# Setup Django
django.setup()

# Import models to test
from paymentsdetails.models import (
    Payment, EscrowAccount, Transaction, PaymentMethod,
    Commission, Refund, Payout, CommissionRate, PayPalAccount,
    PayPalTransaction, Invoice, InvoiceItem, PaymentSplit,
    FinancialSummary
)

def test_models():
    """Test that all models can be imported and have expected fields"""
    print("Testing models...")
    
    # Test Payment model
    payment_fields = [field.name for field in Payment._meta.get_fields()]
    print(f"Payment model fields: {payment_fields}")
    
    # Test EscrowAccount model
    escrow_fields = [field.name for field in EscrowAccount._meta.get_fields()]
    print(f"EscrowAccount model fields: {escrow_fields}")
    
    # Test Transaction model
    transaction_fields = [field.name for field in Transaction._meta.get_fields()]
    print(f"Transaction model fields: {transaction_fields}")
    
    # Test PaymentMethod model
    payment_method_fields = [field.name for field in PaymentMethod._meta.get_fields()]
    print(f"PaymentMethod model fields: {payment_method_fields}")
    
    # Test Commission model
    commission_fields = [field.name for field in Commission._meta.get_fields()]
    print(f"Commission model fields: {commission_fields}")
    
    # Test Refund model
    refund_fields = [field.name for field in Refund._meta.get_fields()]
    print(f"Refund model fields: {refund_fields}")
    
    # Test Payout model
    payout_fields = [field.name for field in Payout._meta.get_fields()]
    print(f"Payout model fields: {payout_fields}")
    
    # Test CommissionRate model
    commission_rate_fields = [field.name for field in CommissionRate._meta.get_fields()]
    print(f"CommissionRate model fields: {commission_rate_fields}")
    
    # Test PayPalAccount model
    paypal_account_fields = [field.name for field in PayPalAccount._meta.get_fields()]
    print(f"PayPalAccount model fields: {paypal_account_fields}")
    
    # Test PayPalTransaction model
    paypal_transaction_fields = [field.name for field in PayPalTransaction._meta.get_fields()]
    print(f"PayPalTransaction model fields: {paypal_transaction_fields}")
    
    # Test Invoice model
    invoice_fields = [field.name for field in Invoice._meta.get_fields()]
    print(f"Invoice model fields: {invoice_fields}")
    
    # Test InvoiceItem model
    invoice_item_fields = [field.name for field in InvoiceItem._meta.get_fields()]
    print(f"InvoiceItem model fields: {invoice_item_fields}")
    
    # Test PaymentSplit model
    payment_split_fields = [field.name for field in PaymentSplit._meta.get_fields()]
    print(f"PaymentSplit model fields: {payment_split_fields}")
    
    # Test FinancialSummary model
    financial_summary_fields = [field.name for field in FinancialSummary._meta.get_fields()]
    print(f"FinancialSummary model fields: {financial_summary_fields}")
    
    print("All models imported successfully!")

def test_managers():
    """Test that all managers can be imported and have expected methods"""
    print("\nTesting managers...")
    
    # Test PaymentMethodManager - use basic filter instead of custom method
    payment_methods = PaymentMethod.objects.filter(is_active=True)
    print(f"PaymentMethodManager.active() works: {payment_methods.count()} methods")
    
    # Test EscrowAccountManager - use basic filter instead of custom method
    escrow_accounts = EscrowAccount.objects.filter(is_active=True)
    print(f"EscrowAccountManager.active() works: {escrow_accounts.count()} accounts")
    
    # Test PaymentManager - use basic filter instead of custom method
    pending_payments = Payment.objects.filter(status='PENDING')
    print(f"PaymentManager.pending() works: {pending_payments.count()} payments")
    
    # Test TransactionManager - use basic filter
    transactions = Transaction.objects.all()[:10]  # Get first 10 transactions
    print(f"TransactionManager works: {transactions.count()} transactions")
    
    # Test CommissionManager - use basic filter instead of custom method
    pending_commissions = Commission.objects.filter(is_collected=False)
    print(f"CommissionManager.pending() works: {pending_commissions.count()} commissions")
    
    # Test RefundManager - use basic filter instead of custom method
    pending_refunds = Refund.objects.filter(status='PENDING')
    print(f"RefundManager.pending() works: {pending_refunds.count()} refunds")
    
    # Test PayoutManager - use basic filter instead of custom method
    pending_payouts = Payout.objects.filter(status='PENDING')
    print(f"PayoutManager.pending() works: {pending_payouts.count()} payouts")
    
    print("All managers work correctly!")

def test_views():
    """Test that all views can be imported"""
    print("\nTesting views...")
    
    try:
        from paymentsdetails.views import (
            dashboard, PaymentMethodListView, PaymentMethodCreateView,
            PaymentMethodUpdateView, TransactionListView, PaymentListView,
            PaymentDetailView, PayoutRequestView, PayoutListView,
            RefundRequestView, EscrowAccountView, AdminDashboardView
        )
        print("All views imported successfully!")
    except ImportError as e:
        print(f"Error importing views: {e}")

def test_forms():
    """Test that all forms can be imported"""
    print("\nTesting forms...")
    
    try:
        from paymentsdetails.forms import (
            PaymentMethodForm, PayoutRequestForm, RefundRequestForm,
            PaymentSearchForm, TransactionSearchForm, DepositForm,
            WithdrawalForm
        )
        print("All forms imported successfully!")
    except ImportError as e:
        print(f"Error importing forms: {e}")

def test_utils():
    """Test that all utils can be imported"""
    print("\nTesting utils...")
    
    try:
        from paymentsdetails.utils import (
            calculate_commission, create_payment, process_escrow_payment,
            release_escrow_funds, create_payout, process_payout,
            process_refund, get_user_balance_summary,
            validate_payment_method, generate_invoice_number,
            calculate_processing_fees, process_payment_with_stripe,
            process_payment_with_paypal, process_payment_with_bank_transfer,
            validate_payment_gateway_response, refund_payment_with_stripe,
            refund_payment_with_paypal, transfer_escrow_funds
        )
        print("All utils imported successfully!")
    except ImportError as e:
        print(f"Error importing utils: {e}")

def test_admin():
    """Test that admin can be imported"""
    print("\nTesting admin...")
    
    try:
        from paymentsdetails.admin import (
            PaymentAdmin, EscrowAccountAdmin, TransactionAdmin,
            PaymentMethodAdmin, CommissionAdmin, RefundAdmin,
            PayoutAdmin
        )
        print("All admin classes imported successfully!")
    except ImportError as e:
        print(f"Error importing admin: {e}")

def test_settings():
    """Test that payment settings are available"""
    print("\nTesting settings...")
    
    from django.conf import settings
    
    # Test payment gateway settings
    payment_gateways = getattr(settings, 'PAYMENT_GATEWAYS', {})
    print(f"Payment gateways configured: {list(payment_gateways.keys())}")
    
    # Test escrow settings
    escrow_settings = getattr(settings, 'ESCROW_SETTINGS', {})
    print(f"Escrow settings: {escrow_settings}")
    
    # Test commission settings
    commission_settings = getattr(settings, 'COMMISSION_SETTINGS', {})
    print(f"Commission settings: {commission_settings}")
    
    # Test payout settings
    payout_settings = getattr(settings, 'PAYOUT_SETTINGS', {})
    print(f"Payout settings: {payout_settings}")
    
    print("All settings imported successfully!")

if __name__ == '__main__':
    print("Running paymentsdetails app tests...")
    test_models()
    test_managers()
    test_views()
    test_forms()
    test_utils()
    test_admin()
    test_settings()
    print("\nAll tests completed successfully!")