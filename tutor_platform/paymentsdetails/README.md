# Payments Details App

This app handles all financial transactions, escrow management, and payment processing for the tutoring platform.

## Features

### Core Payment System
- **Payment Model**: Tracks all financial transactions between users
- **EscrowAccount**: Manages funds held in escrow for secure transactions
- **Transaction**: Complete audit trail of all financial movements
- **PaymentMethod**: Stores user payment methods (Stripe, PayPal, Bank Transfer, etc.)

### Commission & Refund System
- **Commission**: Tracks platform fees and commissions
- **Refund**: Handles refund processing with approval workflow
- **Payout**: Manages tutor payouts with processing fees

### Key Features

#### Escrow Management
- Secure fund holding for transactions
- Automatic balance tracking
- Hold/release mechanisms for pending transactions
- Multi-currency support

#### Payment Processing
- Multiple payment methods support
- Gateway integration ready
- Transaction ID tracking
- Status workflow management

#### Financial Controls
- Commission calculation and collection
- Refund processing with approval workflow
- Payout processing with fee deduction
- Complete audit trail

## Models Overview

### Payment
Main payment model tracking all financial transactions:
- Links to Award for requirement-based payments
- Supports multiple payment types (ESCROW_DEPOSIT, SESSION_PAYMENT, etc.)
- Complete status workflow (PENDING → PROCESSING → COMPLETED)
- Gateway response storage for integration

### EscrowAccount
One-to-one with User for fund management:
- Current, pending, and total balance tracking
- Fund operations (add, withdraw, hold, release)
- Transaction history integration

### Transaction
Complete audit trail of all financial movements:
- Multiple transaction types (DEPOSIT, WITHDRAWAL, etc.)
- Running balance tracking
- Links to payments and refunds

### PaymentMethod
User payment method storage:
- Multiple provider support (Stripe, PayPal, Bank Transfer)
- Verification and expiration tracking
- Default method management

### Commission
Platform fee tracking:
- Flexible commission types
- Rate and amount tracking
- Collection status management

### Refund
Refund processing with workflow:
- Approval process (PENDING → APPROVED → PROCESSED → COMPLETED)
- Partial refund support
- Transaction reversal handling

### Payout
Tutor payout management:
- Processing fee calculation
- Scheduled payout support
- Status tracking and workflow

## Usage Examples

### Creating an Escrow Payment
```python
from paymentsdetails.utils import process_escrow_payment

# Process $100 payment from student to tutor
payment, escrow = process_escrow_payment(
    payer=student_user,
    payee=tutor_user,
    amount=Decimal('100.00'),
    award=award_object,
    payment_method=payment_method
)
```

### Releasing Funds from Escrow
```python
from paymentsdetails.utils import release_escrow_funds

# Release funds with 10% commission
commission, payment = release_escrow_funds(
    payment=payment_object,
    commission_rate=Decimal('0.10')
)
```

### Creating a Payout
```python
from paymentsdetails.utils import create_payout

# Create $200 payout for tutor
payout = create_payout(
    tutor=tutor_user,
    amount=Decimal('200.00'),
    payment_method=payment_method,
    processing_fees=Decimal('5.00')
)
```

### Processing a Refund
```python
from paymentsdetails.utils import process_refund

# Process $50 refund
refund = process_refund(
    payment=payment_object,
    amount=Decimal('50.00'),
    reason="Student requested refund"
)
```

### Getting User Balance Summary
```python
from paymentsdetails.utils import get_user_balance_summary

# Get complete balance summary
summary = get_user_balance_summary(user=tutor_user)
print(f"Current balance: {summary['current_balance']}")
print(f"Pending balance: {summary['pending_balance']}")
print(f"Total earned: {summary['total_earned']}")
```

## Custom Managers

Each model has a custom manager with useful query methods:

### PaymentManager
```python
# Get pending payments
Payment.objects.pending()

# Get payments for a user
Payment.objects.for_user(user)

# Get payments by type
Payment.objects.of_type(Payment.PaymentType.ESCROW_DEPOSIT)

# Get recent payments
Payment.objects.recent(days=30)
```

### EscrowAccountManager
```python
# Get user's escrow account
EscrowAccount.objects.for_user(user)

# Get accounts with minimum balance
EscrowAccount.objects.with_balance(min_amount=Decimal('100.00'))
```

### TransactionManager
```python
# Get user's transactions
Transaction.objects.for_user(user)

# Get deposits only
Transaction.objects.deposits()

# Calculate total for user
total = Transaction.objects.total_for_user(user, Transaction.TransactionType.DEPOSIT)
```

## Admin Features

The admin interface provides:
- Bulk actions for common operations
- Fieldset organization for clarity
- Status-based filtering
- Search capabilities
- Transaction reference tracking

## Security Features

- All financial operations use database transactions
- Balance validation prevents overdrafts
- Status workflows ensure proper processing
- Complete audit trail with timestamps
- User permission checks for sensitive operations

## Integration Points

### Payment Gateways
- `Payment.gateway_response` stores gateway responses
- `PaymentMethod.method_details` for gateway-specific data
- Transaction ID tracking for reconciliation

### Notifications
- Payment status changes trigger notifications
- Refund processing updates
- Payout completion notifications

### Requirements App
- Payments link to Award objects
- Milestone and session payment support
- Commission calculation based on award amounts

## Configuration

### Commission Rates
Commission rates are configurable per payment:
```python
# 10% platform commission
commission_rate = Decimal('0.10')

# Calculate commission amount
commission_amount = payment.amount * commission_rate
```

### Processing Fees
Flexible fee structure support:
```python
fee_structure = {
    'flat_fee': Decimal('0.30'),
    'percentage_fee': Decimal('0.029'),
    'max_fee': Decimal('10.00')
}
```

## Testing

The app includes comprehensive test coverage for:
- Model validation
- Manager methods
- Utility functions
- Workflow processes
- Edge cases

## Future Enhancements

- Multi-currency conversion
- Advanced reporting
- Automated payout scheduling
- Integration with more payment gateways
- Subscription billing support