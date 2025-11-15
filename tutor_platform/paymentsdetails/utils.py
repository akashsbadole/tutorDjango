"""
Utility functions for payment processing and financial calculations.
"""

from decimal import Decimal
from django.utils import timezone
from django.db import transaction, models
from .models import (
    Payment, EscrowAccount, Transaction, PaymentMethod,
    Commission, Refund, Payout
)
from notifications.models import Notification


def calculate_commission(amount, rate):
    """
    Calculate commission amount based on rate.
    
    Args:
        amount (Decimal): Base amount
        rate (Decimal): Commission rate (e.g., 0.15 for 15%)
    
    Returns:
        Decimal: Commission amount
    """
    return amount * rate


def create_payment(
    payer, payee, amount, payment_type, award=None,
    payment_method=None, description="", currency="USD"
):
    """
    Create a new payment with proper validation.
    
    Args:
        payer: User making payment
        payee: User receiving payment
        amount (Decimal): Payment amount
        payment_type: Payment.PaymentType
        award: Optional related award
        payment_method: Optional payment method
        description (str): Payment description
        currency (str): Currency code
    
    Returns:
        Payment: Created payment instance
    """
    payment = Payment.objects.create(
        award=award,
        payer=payer,
        payee=payee,
        amount=amount,
        currency=currency,
        payment_type=payment_type,
        payment_method=payment_method,
        description=description
    )
    
    return payment


def process_escrow_payment(payer, payee, amount, award=None, payment_method=None):
    """
    Process an escrow payment from payer to payee.
    
    Args:
        payer: User making payment
        payee: User receiving payment
        amount (Decimal): Payment amount
        award: Optional related award
        payment_method: Payment method to use
    
    Returns:
        tuple: (Payment, EscrowAccount) created instances
    """
    with transaction.atomic():
        # Create payment
        payment = create_payment(
            payer=payer,
            payee=payee,
            amount=amount,
            payment_type=Payment.PaymentType.ESCROW_DEPOSIT,
            award=award,
            payment_method=payment_method,
            description=f"Escrow deposit for {award.title if award else 'payment'}"
        )
        
        # Get or create escrow account for payer
        escrow_account, created = EscrowAccount.objects.get_or_create(
            user=payer,
            defaults={'currency': payment.currency}
        )
        
        # Hold funds in escrow
        escrow_account.hold_funds(amount)
        
        return payment, escrow_account


def release_escrow_funds(payment, commission_rate=Decimal('0.10')):
    """
    Release funds from escrow to payee after deducting commission.
    
    Args:
        payment: Payment to release
        commission_rate (Decimal): Commission rate (default 10%)
    
    Returns:
        tuple: (Commission, Transaction) created instances
    """
    with transaction.atomic():
        # Calculate commission
        commission_amount = calculate_commission(payment.amount, commission_rate)
        net_amount = payment.amount - commission_amount
        
        # Create commission record
        commission = Commission.objects.create(
            payment=payment,
            commission_type=Commission.CommissionType.PLATFORM_FEE,
            commission_amount=commission_amount,
            currency=payment.currency,
            commission_rate=commission_rate,
            calculated_on_amount=payment.amount,
            description=f"Platform commission for payment {payment.id}"
        )
        
        # Mark commission as collected
        commission.mark_collected()
        
        # Get escrow account for payer
        escrow_account = payment.payer.escrow_account
        
        # Release held funds
        escrow_account.release_held_funds(payment.amount)
        
        # Withdraw from payer's escrow
        escrow_account.withdraw_funds(payment.amount)
        
        # Get or create escrow account for payee and add net amount
        payee_escrow, created = EscrowAccount.objects.get_or_create(
            user=payment.payee,
            defaults={'currency': payment.currency}
        )
        payee_escrow.add_funds(net_amount)
        
        # Mark payment as completed
        payment.mark_completed()
        
        return commission, payment


def create_payout(tutor, amount, payment_method=None, processing_fees=Decimal('0.00')):
    """
    Create a payout for a tutor.
    
    Args:
        tutor: User receiving payout
        amount (Decimal): Total payout amount
        payment_method: Payment method for payout
        processing_fees (Decimal): Processing fees to deduct
    
    Returns:
        Payout: Created payout instance
    """
    # Get tutor's escrow account
    escrow_account = tutor.escrow_account
    
    if not escrow_account or escrow_account.current_balance < amount:
        raise ValueError("Insufficient balance for payout")
    
    with transaction.atomic():
        # Create payout
        payout = Payout.objects.create(
            tutor=tutor,
            total_amount=amount,
            currency=escrow_account.currency,
            payout_method=payment_method,
            processing_fees=processing_fees,
            scheduled_payout_date=timezone.now().date()
        )
        
        # Hold funds in escrow
        escrow_account.hold_funds(amount)
        
        return payout


def process_payout(payout, transaction_reference=None):
    """
    Process a payout and release funds.
    
    Args:
        payout: Payout to process
        transaction_reference (str): Transaction reference from payment provider
    
    Returns:
        Transaction: Created transaction record
    """
    with transaction.atomic():
        # Process payout
        payout.process(transaction_reference=transaction_reference)
        
        # Get tutor's escrow account
        escrow_account = payout.tutor.escrow_account
        
        # Release held funds
        escrow_account.release_held_funds(payout.total_amount)
        
        # Withdraw net amount from escrow
        escrow_account.withdraw_funds(payout.net_amount)
        
        # Complete payout
        payout.complete()
        
        return payout.transactions.last()


def process_refund(payment, amount=None, reason="", refund_method=None):
    """
    Process a refund for a payment.
    
    Args:
        payment: Payment to refund
        amount (Decimal): Refund amount (None for full refund)
        reason (str): Reason for refund
        refund_method: Payment method for refund
    
    Returns:
        Refund: Created refund instance
    """
    with transaction.atomic():
        # Create refund
        refund = payment.process_refund(amount=amount, reason=reason)
        refund.refund_method = refund_method
        refund.save()
        
        # Get escrow accounts
        payer_escrow = payment.payer.escrow_account
        payee_escrow = payment.payee.escrow_account
        
        # If payment was completed, reverse the transaction
        if payment.status == Payment.PaymentStatus.COMPLETED:
            # Refund from payee's escrow
            if payee_escrow and payee_escrow.current_balance >= refund.amount:
                payee_escrow.withdraw_funds(refund.amount)
               
                # Add back to payer's escrow
                if payer_escrow:
                    payer_escrow.add_funds(refund.amount)
        
        # Mark refund as completed
        refund.complete()
        
        return refund


def get_user_balance_summary(user):
    """
    Get balance summary for a user.
    
    Args:
        user: User to get summary for
    
    Returns:
        dict: Balance summary with various metrics
    """
    escrow_account = getattr(user, 'escrow_account', None)
    
    summary = {
        'current_balance': Decimal('0.00'),
        'pending_balance': Decimal('0.00'),
        'total_deposited': Decimal('0.00'),
        'total_withdrawn': Decimal('0.00'),
        'total_earned': Decimal('0.00'),
        'total_spent': Decimal('0.00'),
        'pending_payouts': Decimal('0.00'),
    }
    
    if escrow_account:
        summary.update({
            'current_balance': escrow_account.current_balance,
            'pending_balance': escrow_account.pending_balance,
            'total_deposited': escrow_account.total_deposited,
            'total_withdrawn': escrow_account.total_withdrawn,
        })
    
    # Calculate totals from payments
    payments_received = Payment.objects.filter(payee=user, status=Payment.PaymentStatus.COMPLETED)
    payments_made = Payment.objects.filter(payer=user, status=Payment.PaymentStatus.COMPLETED)
    
    summary['total_earned'] = payments_received.aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0.00')
    
    summary['total_spent'] = payments_made.aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0.00')
    
    # Calculate pending payouts
    pending_payouts = Payout.objects.filter(tutor=user, status=Payout.PayoutStatus.PENDING)
    summary['pending_payouts'] = pending_payouts.aggregate(
        total=models.Sum('net_amount')
    )['total'] or Decimal('0.00')
    
    return summary


def validate_payment_method(user, payment_method_id):
    """
    Validate that a payment method belongs to a user and is usable.
    
    Args:
        user: User to validate against
        payment_method_id: ID of payment method to validate
    
    Returns:
        PaymentMethod or None: Valid payment method or None
    """
    try:
        payment_method = PaymentMethod.objects.get(
            id=payment_method_id,
            user=user
        )
        
        if payment_method.can_be_used():
            return payment_method
    except PaymentMethod.DoesNotExist:
        pass
    
    return None


def generate_invoice_number():
    """
    Generate a unique invoice number.
    
    Returns:
        str: Unique invoice number
    """
    timestamp = timezone.now().strftime('%Y%m%d')
    # Get count of payments today
    count_today = Payment.objects.filter(
        created_at__date=timezone.now().date()
    ).count()
    
    return f"INV-{timestamp}-{count_today + 1:04d}"


def calculate_processing_fees(amount, fee_structure=None):
    """
    Calculate processing fees based on amount and fee structure.
    
    Args:
        amount (Decimal): Base amount
        fee_structure (dict): Fee structure configuration
    
    Returns:
        Decimal: Processing fees
    """
    if not fee_structure:
        # Default fee structure
        fee_structure = {
            'flat_fee': Decimal('0.30'),  # $0.30 flat fee
            'percentage_fee': Decimal('0.029'),  # 2.9% percentage
            'max_fee': Decimal('10.00'),  # Maximum $10 fee
        }
    
    flat_fee = fee_structure.get('flat_fee', Decimal('0.00'))
    percentage_fee = amount * fee_structure.get('percentage_fee', Decimal('0.00'))
    total_fee = flat_fee + percentage_fee
    
    max_fee = fee_structure.get('max_fee')
    if max_fee and total_fee > max_fee:
        total_fee = max_fee
    
    return total_fee


def process_payment_with_stripe(payment_method, amount, description=""):
    """
    Process a payment using Stripe.
    
    Args:
        payment_method: PaymentMethod instance with Stripe details
        amount (Decimal): Amount to charge
        description (str): Payment description
    
    Returns:
        dict: Result with success status and transaction details
    """
    try:
        import stripe
        
        # Set Stripe API key (in production, use environment variables)
        stripe.api_key = 'sk_test_...'  # Replace with your actual Stripe key
        
        # Get payment method details
        method_details = payment_method.method_details
        
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency='usd',
            payment_method=payment_method.provider_method_id,
            confirmation_method='manual',
            description=description,
            metadata={
                'payment_method_id': str(payment_method.id),
                'user_id': str(payment_method.user.id)
            }
        )
        
        return {
            'success': True,
            'transaction_id': intent.id,
            'client_secret': intent.client_secret,
            'status': intent.status,
            'response': intent
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'transaction_id': None
        }


def process_payment_with_paypal(payment_method, amount, description=""):
    """
    Process a payment using PayPal.
    
    Args:
        payment_method: PaymentMethod instance with PayPal details
        amount (Decimal): Amount to charge
        description (str): Payment description
    
    Returns:
        dict: Result with success status and transaction details
    """
    try:
        import paypalrestsdk
        
        # Set PayPal API credentials (in production, use environment variables)
        paypalrestsdk.configure({
            'mode': 'sandbox',  # or 'live'
            'client_id': 'YOUR_PAYPAL_CLIENT_ID',
            'client_secret': 'YOUR_PAYPAL_CLIENT_SECRET'
        })
        
        # Create payment
        payment = paypalrestsdk.Payment({
            'intent': 'sale',
            'payer': {
                'payment_method': 'paypal'
            },
            'transactions': [{
                'amount': {
                    'total': str(amount),
                    'currency': 'USD'
                },
                'description': description
            }],
            'redirect_urls': {
                'return_url': 'https://your-site.com/payments/return/',
                'cancel_url': 'https://your-site.com/payments/cancel/'
            }
        })
        
        if payment.create():
            return {
                'success': True,
                'transaction_id': payment.id,
                'approval_url': payment.links[0].href,
                'status': payment.state,
                'response': payment.to_dict()
            }
        else:
            return {
                'success': False,
                'error': payment.error,
                'transaction_id': None
            }
           
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'transaction_id': None
        }


def process_payment_with_bank_transfer(payment_method, amount, description=""):
    """
    Process a payment using bank transfer (initiate transfer request).
    
    Args:
        payment_method: PaymentMethod instance with bank details
        amount (Decimal): Amount to transfer
        description (str): Transfer description
    
    Returns:
        dict: Result with success status and transaction details
    """
    try:
        # For bank transfers, we typically create a pending payment
        # and provide instructions to the user
        
        method_details = payment_method.method_details
        
        # Generate a unique reference number
        reference = generate_invoice_number()
        
        return {
            'success': True,
            'transaction_id': reference,
            'status': 'PENDING',
            'instructions': {
                'bank_name': method_details.get('bank_name'),
                'account_number': method_details.get('account_number'),
                'routing_number': method_details.get('routing_number'),
                'account_holder': method_details.get('account_holder'),
                'reference': reference,
                'amount': str(amount),
                'message': f'Transfer {amount} to account ending in {method_details.get("account_number")[-4:]} with reference {reference}'
            },
            'response': {
                'reference': reference,
                'initiated_at': timezone.now().isoformat()
            }
        }
           
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'transaction_id': None
        }


def validate_payment_gateway_response(gateway, response_data):
    """
    Validate payment gateway response for authenticity.
    
    Args:
        gateway (str): Payment gateway name (stripe, paypal)
        response_data (dict): Response data from gateway
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if gateway == 'stripe':
        try:
            import stripe
           
            # Verify Stripe signature
            sig_header = response_data.get('stripe_signature')
            if not sig_header:
                return False, "Missing Stripe signature"
           
            webhook_secret = 'whsec_...'  # Replace with your actual webhook secret
            payload = response_data.get('payload', '')
           
            # This is a simplified verification
            # In production, use Stripe's SDK for proper verification
            return True, ""
           
        except Exception as e:
            return False, f"Stripe validation error: {str(e)}"
    
    elif gateway == 'paypal':
        try:
            # Verify PayPal webhook ID
            webhook_id = response_data.get('id')
            if not webhook_id:
                return False, "Missing PayPal webhook ID"
           
            # In production, use PayPal's SDK to verify webhook
            # This is a simplified validation
            return True, ""
           
        except Exception as e:
            return False, f"PayPal validation error: {str(e)}"
    
    return False, f"Unknown payment gateway: {gateway}"


def refund_payment_with_stripe(payment, amount, reason=""):
    """
    Process a refund using Stripe.
    
    Args:
        payment: Payment instance to refund
        amount (Decimal): Amount to refund
        reason (str): Reason for refund
    
    Returns:
        dict: Result with success status and refund details
    """
    try:
        import stripe
        
        stripe.api_key = 'sk_test_...'  # Replace with your actual Stripe key
        
        # Create refund
        refund = stripe.Refund.create(
            payment_intent=payment.transaction_id,
            amount=int(amount * 100),  # Convert to cents
            reason='requested_by_customer',  # Stripe requires specific reason values
            metadata={
                'payment_id': str(payment.id),
                'refunded_by': 'system',
                'custom_reason': reason
            }
        )
        
        return {
            'success': True,
            'refund_id': refund.id,
            'status': refund.status,
            'amount': refund.amount / 100,  # Convert from cents
            'response': refund
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'refund_id': None
        }


def refund_payment_with_paypal(payment, amount, reason=""):
    """
    Process a refund using PayPal.
    
    Args:
        payment: Payment instance to refund
        amount (Decimal): Amount to refund
        reason (str): Reason for refund
    
    Returns:
        dict: Result with success status and refund details
    """
    try:
        import paypalrestsdk
        
        # Configure PayPal
        paypalrestsdk.configure({
            'mode': 'sandbox',  # or 'live'
            'client_id': 'YOUR_PAYPAL_CLIENT_ID',
            'client_secret': 'YOUR_PAYPAL_CLIENT_SECRET'
        })
        
        # Get sale ID from payment
        sale_id = payment.transaction_id
        
        # Create refund
        refund = paypalrestsdk.Refund({
            'amount': {
                'total': str(amount),
                'currency': 'USD'
            },
            'sale_id': sale_id,
            'reason': reason
        })
        
        if refund.create():
            return {
                'success': True,
                'refund_id': refund.id,
                'status': refund.state,
                'amount': refund.amount.total,
                'response': refund.to_dict()
            }
        else:
            return {
                'success': False,
                'error': refund.error,
                'refund_id': None
            }
           
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'refund_id': None
        }


def transfer_escrow_funds(from_user, to_user, amount, description=""):
    """
    Transfer funds from one user's escrow to another.
    
    Args:
        from_user: User transferring funds
        to_user: User receiving funds
        amount (Decimal): Amount to transfer
        description (str): Transfer description
    
    Returns:
        tuple: (success, transaction)
    """
    try:
        with transaction.atomic():
            # Get escrow accounts
            from_escrow = from_user.escrow_account
            to_escrow = to_user.escrow_account
               
            # Check if from_escrow exists and has sufficient funds
            if not from_escrow or from_escrow.current_balance < amount:
                return False, "Insufficient balance"
               
            # Create to_escrow if it doesn't exist
            if not to_escrow:
                to_escrow = EscrowAccount.objects.create(
                    user=to_user,
                    currency='USD'
                )
               
            # Transfer funds
            from_escrow.withdraw_funds(amount)
            to_escrow.add_funds(amount)
               
            # Create transaction records
            from_transaction = Transaction.objects.create(
                user=from_user,
                transaction_type=Transaction.TransactionType.PAYMENT_SENT,
                amount=amount,
                currency=from_escrow.currency,
                running_balance=from_escrow.current_balance,
                description=f"Transfer to {to_user.get_full_name()}: {description}"
            )
               
            to_transaction = Transaction.objects.create(
                user=to_user,
                transaction_type=Transaction.TransactionType.PAYMENT_RECEIVED,
                amount=amount,
                currency=to_escrow.currency,
                running_balance=to_escrow.current_balance,
                description=f"Transfer from {from_user.get_full_name()}: {description}"
            )
               
            # Send notifications
            try:
                from notifications.utils import create_notification
                create_notification(
                    recipient=from_user,
                    title="Transfer Sent",
                    content=f"You have transferred {amount} to {to_user.get_full_name()}",
                    notification_type=Notification.Type.SYSTEM
                )
               
                create_notification(
                    recipient=to_user,
                    title="Transfer Received",
                    content=f"You have received {amount} from {from_user.get_full_name()}",
                    notification_type=Notification.Type.SYSTEM
                )
            except Exception:
                # Ignore notification errors
                pass
               
            return True, to_transaction
               
    except Exception as e:
        return False, str(e)