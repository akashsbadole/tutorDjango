# Payments Details Models Design

## 1. Payment Method Models

### PaymentMethod
- Store user payment methods
- Fields:
  - id: BigAutoField (primary key)
  - user: ForeignKey(User, related_name='payment_methods')
  - method_type: CharField (choices: CREDIT_CARD, DEBIT_CARD, PAYPAL, BANK_ACCOUNT, default=CREDIT_CARD)
  - provider: CharField (choices: STRIPE, PAYPAL, SQUARE, MANUAL, default=STRIPE)
  - provider_method_id: CharField (max_length=255) - ID from payment provider
  - is_default: BooleanField (default=False)
  - card_last4: CharField (max_length=4, blank=True, null=True)
  - card_brand: CharField (max_length=50, blank=True, null=True)
  - card_exp_month: PositiveIntegerField (null=True, blank=True)
  - card_exp_year: PositiveIntegerField (null=True, blank=True)
  - bank_name: CharField (max_length=100, blank=True, null=True)
  - bank_account_last4: CharField (max_length=4, blank=True, null=True)
  - paypal_email: EmailField (blank=True, null=True)
  - is_verified: BooleanField (default=False)
  - is_active: BooleanField (default=True)
  - metadata: JSONField (default=dict) - Additional provider-specific data
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)
  - expires_at: DateTimeField (null=True, blank=True)

- Methods:
  - get_display_name() - Return user-friendly payment method name
  - is_expired() - Check if payment method is expired
  - can_be_used() - Check if payment method is valid and active

## 2. Escrow Models

### EscrowAccount
- Main escrow account model
- Fields:
  - id: BigAutoField (primary key)
  - user: ForeignKey(User, related_name='escrow_accounts')
  - account_type: CharField (choices: STUDENT, TUTOR, PLATFORM)
  - balance: DecimalField (max_digits=12, decimal_places=2, default=0)
  - available_balance: DecimalField (max_digits=12, decimal_places=2, default=0)
  - pending_balance: DecimalField (max_digits=12, decimal_places=2, default=0)
  - currency: CharField (default='USD')
  - is_active: BooleanField (default=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - get_total_balance() - Calculate total balance
  - add_funds(amount) - Add funds to escrow
  - release_funds(amount) - Release funds from escrow
  - hold_funds(amount) - Hold funds in pending state

### EscrowTransaction
- Individual escrow transactions
- Fields:
  - id: BigAutoField (primary key)
  - escrow_account: ForeignKey(EscrowAccount, related_name='transactions')
  - transaction_type: CharField (choices: DEPOSIT, WITHDRAWAL, HOLD, RELEASE, REFUND, FEE)
  - amount: DecimalField (max_digits=12, decimal_places=2)
  - fee: DecimalField (max_digits=10, decimal_places=2, default=0)
  - net_amount: DecimalField (max_digits=12, decimal_places=2)
  - currency: CharField (default='USD')
  - reference_id: CharField (max_length=100, blank=True, null=True) - External reference
  - description: CharField (max_length=255, blank=True, null=True)
  - status: CharField (choices: PENDING, COMPLETED, FAILED, CANCELLED, default=PENDING)
  - payment_method: ForeignKey(PaymentMethod, null=True, blank=True)
  - related_award: ForeignKey('requirements.Award', null=True, blank=True)
  - related_payment: ForeignKey('Payment', null=True, blank=True)
  - provider_transaction_id: CharField (max_length=255, blank=True, null=True)
  - failure_reason: TextField (blank=True, null=True)
  - metadata: JSONField (default=dict)
  - created_at: DateTimeField (auto_now_add)
  - processed_at: DateTimeField (null=True, blank=True)

- Methods:
  - process() - Process the transaction
  - cancel() - Cancel the transaction
  - get_status_display() - Return formatted status

## 3. Payment Models

### Payment
- Main payment model for awards
- Fields:
  - id: BigAutoField (primary key)
  - award: ForeignKey('requirements.Award', related_name='payments')
  - student: ForeignKey(User, related_name='payments_made')
  - tutor: ForeignKey(User, related_name='payments_received')
  - amount: DecimalField (max_digits=10, decimal_places=2)
  - currency: CharField (default='USD')
  - payment_type: CharField (choices: FULL_PAYMENT, MILESTONE, SESSION, REFUND)
  - status: CharField (choices: PENDING, PROCESSING, COMPLETED, FAILED, REFUNDED, DISPUTED, default=PENDING)
  - due_date: DateField()
  - paid_date: DateField (null=True, blank=True)
  - payment_method: ForeignKey(PaymentMethod, null=True, blank=True)
  - escrow_transaction: ForeignKey(EscrowTransaction, null=True, blank=True)
  - invoice_number: CharField (max_length=50, unique=True)
  - description: TextField(blank=True, null=True)
  - student_notes: TextField(blank=True, null=True)
  - tutor_notes: TextField(blank=True, null=True)
  - admin_notes: TextField(blank=True, null=True)
  - is_released: BooleanField (default=False)
  - release_date: DateField (null=True, blank=True)
  - refund_amount: DecimalField (max_digits=10, decimal_places=2, null=True, blank=True)
  - refund_reason: TextField(blank=True, null=True)
  - refund_date: DateField (null=True, blank=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - get_total_amount_with_fees() - Calculate total including platform fees
  - can_be_refunded() - Check if payment can be refunded
  - release_to_tutor() - Release payment to tutor
  - refund_to_student() - Refund payment to student

### PaymentSplit
- Split payments for milestones or multiple sessions
- Fields:
  - id: BigAutoField (primary key)
  - payment: ForeignKey(Payment, related_name='splits')
  - milestone: ForeignKey('requirements.Milestone', null=True, blank=True)
  - session: ForeignKey('requirements.Session', null=True, blank=True)
  - amount: DecimalField (max_digits=10, decimal_places=2)
  - status: CharField (choices: PENDING, RELEASED, REFUNDED, default=PENDING)
  - release_date: DateField (null=True, blank=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

## 4. Commission and Fee Models

### Commission
- Platform commission tracking
- Fields:
  - id: BigAutoField (primary key)
  - payment: ForeignKey(Payment, related_name='commissions')
  - commission_type: CharField (choices: PLATFORM, TRANSACTION, REFUND, PENALTY)
  - commission_rate: DecimalField (max_digits=5, decimal_places=4) - e.g., 0.15 for 15%
  - commission_amount: DecimalField (max_digits=10, decimal_places=2)
  - currency: CharField (default='USD')
  - description: CharField (max_length=255, blank=True, null=True)
  - is_collected: BooleanField (default=False)
  - collected_date: DateField (null=True, blank=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

### CommissionRate
- Configurable commission rates
- Fields:
  - id: BigAutoField (primary key)
  - name: CharField (max_length=100)
  - rate_type: CharField (choices: PERCENTAGE, FIXED, TIERED)
  - rate_value: DecimalField (max_digits=5, decimal_places=4)
  - min_amount: DecimalField (max_digits=10, decimal_places=2, null=True, blank=True)
  - max_amount: DecimalField (max_digits=10, decimal_places=2, null=True, blank=True)
  - user_type: CharField (choices: STUDENT, TUTOR, ALL, default=ALL)
  - subject: ForeignKey('accounts.Subject', null=True, blank=True)
  - is_active: BooleanField (default=True)
  - effective_from: DateField()
  - effective_to: DateField (null=True, blank=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - calculate_commission(amount) - Calculate commission for given amount
  - is_applicable(user, amount, subject) - Check if rate applies

## 5. PayPal Integration Models

### PayPalAccount
- PayPal account integration
- Fields:
  - id: BigAutoField (primary key)
  - user: ForeignKey(User, related_name='paypal_accounts')
  - paypal_email: EmailField()
  - paypal_user_id: CharField (max_length=100)
  - account_type: CharField (choices: PERSONAL, PREMIER, BUSINESS)
  - verification_status: CharField (choices: UNVERIFIED, VERIFIED, LIMITED)
  - is_primary: BooleanField (default=False)
  - is_active: BooleanField (default=True)
  - access_token: CharField (max_length=500, blank=True, null=True)
  - refresh_token: CharField (max_length=500, blank=True, null=True)
  - token_expires_at: DateTimeField (null=True, blank=True)
  - metadata: JSONField (default=dict)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

- Methods:
  - is_token_expired() - Check if access token is expired
  - refresh_access_token() - Refresh the access token

### PayPalTransaction
- PayPal-specific transaction details
- Fields:
  - id: BigAutoField (primary key)
  - payment: ForeignKey(Payment, related_name='paypal_transactions')
  - paypal_transaction_id: CharField (max_length=100, unique=True)
  - paypal_order_id: CharField (max_length=100, blank=True, null=True)
  - paypal_payment_id: CharField (max_length=100, blank=True, null=True)
  - paypal_payer_id: CharField (max_length=100, blank=True, null=True)
  - paypal_status: CharField (max_length=50)
  - paypal_intent: CharField (choices: SALE, AUTHORIZE, ORDER)
  - amount: DecimalField (max_digits=10, decimal_places=2)
  - currency: CharField (default='USD')
  - fee_amount: DecimalField (max_digits=10, decimal_places=2, default=0)
  - net_amount: DecimalField (max_digits=10, decimal_places=2)
  - paypal_response: JSONField (default=dict)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

## 6. Invoice and Billing Models

### Invoice
- Invoice generation and tracking
- Fields:
  - id: BigAutoField (primary key)
  - invoice_number: CharField (max_length=50, unique=True)
  - user: ForeignKey(User, related_name='invoices')
  - payment: ForeignKey(Payment, related_name='invoice', null=True, blank=True)
  - invoice_type: CharField (choices: TUITION, COMMISSION, REFUND, CREDIT)
  - amount: DecimalField (max_digits=10, decimal_places=2)
  - tax_amount: DecimalField (max_digits=10, decimal_places=2, default=0)
  - total_amount: DecimalField (max_digits=10, decimal_places=2)
  - currency: CharField (default='USD')
  - status: CharField (choices: DRAFT, SENT, PAID, OVERDUE, CANCELLED, default=DRAFT)
  - issue_date: DateField()
  - due_date: DateField()
  - paid_date: DateField (null=True, blank=True)
  - billing_address: TextField(blank=True, null=True)
  - notes: TextField(blank=True, null=True)
  - terms: TextField(blank=True, null=True)
  - created_at: DateTimeField (auto_now_add)
  - updated_at: DateTimeField (auto_now)

### InvoiceItem
- Line items for invoices
- Fields:
  - id: BigAutoField (primary key)
  - invoice: ForeignKey(Invoice, related_name='items')
  - description: CharField (max_length=255)
  - quantity: DecimalField (max_digits=10, decimal_places=2)
  - unit_price: DecimalField (max_digits=10, decimal_places=2)
  - amount: DecimalField (max_digits=10, decimal_places=2)
  - created_at: DateTimeField (auto_now_add)

## 7. Financial Reports and Analytics

### FinancialSummary
- Periodic financial summaries
- Fields:
  - id: BigAutoField (primary key)
  - period_type: CharField (choices: DAILY, WEEKLY, MONTHLY, YEARLY)
  - period_start: DateField()
  - period_end: DateField()
  - total_payments: DecimalField (max_digits=12, decimal_places=2, default=0)
  - total_commissions: DecimalField (max_digits=12, decimal_places=2, default=0)
  - total_refunds: DecimalField (max_digits=12, decimal_places=2, default=0)
  - net_revenue: DecimalField (max_digits=12, decimal_places=2, default=0)
  - currency: CharField (default='USD')
  - created_at: DateTimeField (auto_now_add)

## 8. Database Indexes for Performance

- PaymentMethod:
  - Index on user_id
  - Index on method_type
  - Index on provider
  - Index on is_default
  - Index on is_active
  - Composite index on (user_id, is_active)

- EscrowAccount:
  - Index on user_id
  - Index on account_type
  - Index on is_active
  - Composite index on (user_id, account_type)

- EscrowTransaction:
  - Index on escrow_account_id
  - Index on transaction_type
  - Index on status
  - Index on created_at
  - Index on provider_transaction_id
  - Composite index on (escrow_account_id, transaction_type)
  - Composite index on (status, created_at)

- Payment:
  - Index on award_id
  - Index on student_id
  - Index on tutor_id
  - Index on status
  - Index on due_date
  - Index on invoice_number
  - Composite index on (student_id, status)
  - Composite index on (tutor_id, status)
  - Composite index on (status, due_date)

- Commission:
  - Index on payment_id
  - Index on commission_type
  - Index on is_collected
  - Composite index on (payment_id, commission_type)

- PayPalAccount:
  - Index on user_id
  - Index on paypal_email
  - Index on is_primary
  - Index on is_active
  - Composite index on (user_id, is_primary)

- Invoice:
  - Index on user_id
  - Index on payment_id
  - Index on invoice_number
  - Index on status
  - Index on due_date
  - Composite index on (user_id, status)
  - Composite index on (status, due_date)

## 9. Constraints and Validation Rules

- PaymentMethod:
  - Provider method ID must be unique per provider
  - Only one default payment method per user
  - Card expiration must be in the future

- EscrowAccount:
  - Balance values must be non-negative
  - Unique constraint on (user, account_type)

- EscrowTransaction:
  - Amount must be positive
  - Net amount must be amount minus fee
  - Status must be valid choice

- Payment:
  - Amount must be positive
  - Due date must be in the future
  - Invoice number must be unique
  - Refund amount cannot exceed payment amount

- Commission:
  - Commission rate must be between 0 and 1
  - Commission amount must be positive

- PayPalAccount:
  - PayPal email must be unique
  - Only one primary PayPal account per user

- Invoice:
  - Invoice number must be unique
  - Total amount must equal amount plus tax
  - Due date must be after issue date

- InvoiceItem:
  - Quantity must be positive
  - Unit price must be positive
  - Amount must equal quantity times unit price