# PayPal Integration for Django Tutoring Platform

This Django app provides comprehensive PayPal integration for the tutoring platform, including payment processing, subscriptions, payouts, refunds, and dispute management.

## Features

- **Payment Processing**: Complete PayPal checkout integration with order creation and capture
- **Subscription Management**: Support for recurring payments and subscription plans
- **Payout Processing**: Tutor withdrawal functionality via PayPal
- **Refund Management**: Full and partial refund processing
- **Dispute Resolution**: Handle PayPal disputes with evidence submission
- **Webhook Processing**: Secure webhook handling with signature verification
- **Account Management**: PayPal account linking and verification
- **Admin Interface**: Comprehensive admin interface for managing PayPal data

## Installation

1. Add the app to your Django project:
   ```python
   INSTALLED_APPS = [
       # ... other apps
       'paypal_integration',
   ]
   ```

2. Include the URL configuration:
   ```python
   urlpatterns = [
       # ... other URLs
       path('paypal/', include('paypal_integration.urls', namespace='paypal_integration')),
   ]
   ```

3. Add the middleware:
   ```python
   MIDDLEWARE = [
       # ... other middleware
       'paypal_integration.middleware.PayPalRequestLoggingMiddleware',
       'paypal_integration.middleware.PayPalCSRFProtectionMiddleware',
       'paypal_integration.middleware.PayPalSecurityHeadersMiddleware',
   ]
   ```

4. Configure PayPal settings (see Configuration section below)

## Configuration

Add the following settings to your `settings.py`:

```python
# PayPal Integration Configuration
PAYPAL_CONFIG = {
    # API Configuration
    'CLIENT_ID': 'YOUR_PAYPAL_CLIENT_ID',
    'CLIENT_SECRET': 'YOUR_PAYPAL_CLIENT_SECRET',
    'MODE': 'sandbox',  # or 'live'
    
    # API Endpoints
    'SANDBOX_API_URL': 'https://api-m.sandbox.paypal.com',
    'LIVE_API_URL': 'https://api-m.paypal.com',
    'SANDBOX_WEB_URL': 'https://www.sandbox.paypal.com',
    'LIVE_WEB_URL': 'https://www.paypal.com',
    
    # Webhook Configuration
    'WEBHOOK_URL': '/paypal/webhook/',
    'WEBHOOK_ID': 'YOUR_PAYPAL_WEBHOOK_ID',
    
    # Security Settings
    'SKIP_WEBHOOK_VERIFICATION': False,  # Set to True for development only
    'WEBHOOK_TIMEOUT': 30,
    'API_TIMEOUT': 60,
    'MAX_RETRIES': 3,
    
    # Rate Limiting
    'WEBHOOK_RATE_LIMIT': 100,
    'WEBHOOK_RATE_WINDOW': 60,
    
    # Logging Configuration
    'LOG_REQUESTS': True,
    'LOG_RESPONSES': True,
    'LOG_WEBHOOKS': True,
    
    # Currency Configuration
    'SUPPORTED_CURRENCIES': [
        'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'CNY', 
        'INR', 'MXN', 'BRL', 'CHF', 'SEK', 'NOK', 'DKK'
    ],
    'DEFAULT_CURRENCY': 'USD',
    
    # Fee Configuration
    'DOMESTIC_FEE_RATE': 0.029,  # 2.9% for domestic transactions
    'INTERNATIONAL_FEE_RATE': 0.039,  # 3.9% for international transactions
    'FIXED_FEE': 0.30,  # Fixed fee in USD
    'CURRENCY_CONVERSION_FEE': 0.04,  # 4% for currency conversion
    
    # Subscription Configuration
    'SUBSCRIPTION_ENABLED': True,
    'SUBSCRIPTION_PLANS': {
        'BASIC': {
            'name': 'Basic Tutor Plan',
            'description': 'Access to basic tutoring features',
            'price': '9.99',
            'currency': 'USD',
            'interval': 'MONTH',
            'interval_count': 1,
        },
        'PREMIUM': {
            'name': 'Premium Tutor Plan',
            'description': 'Access to all tutoring features',
            'price': '19.99',
            'currency': 'USD',
            'interval': 'MONTH',
            'interval_count': 1,
        },
        'ENTERPRISE': {
            'name': 'Enterprise Tutor Plan',
            'description': 'Advanced features for institutions',
            'price': '49.99',
            'currency': 'USD',
            'interval': 'MONTH',
            'interval_count': 1,
        },
    },
    
    # Payout Configuration
    'PAYOUT_ENABLED': True,
    'PAYOUT_MIN_AMOUNT': 1.00,
    'PAYOUT_MAX_AMOUNT': 10000.00,
    'PAYOUT_FEE_RATE': 0.025,  # 2.5% payout fee
    'PAYOUT_FIXED_FEE': 0.25,  # Fixed payout fee
    'PAYOUT_BATCH_SIZE': 100,
    
    # Refund Configuration
    'REFUND_ENABLED': True,
    'REFUND_PERIOD_DAYS': 180,
    'PARTIAL_REFUND_ENABLED': True,
    'REFUND_FEE_RATE': 0.00,
    
    # Dispute Configuration
    'DISPUTE_ENABLED': True,
    'DISPUTE_RESPONSE_DAYS': 20,
    'DISPUTE_EVIDENCE_TYPES': [
        'PROOF_OF_FULFILLMENT',
        'PROOF_OF_SERVICE',
        'TRACKING_NUMBER',
        'REFUND_ACKNOWLEDGMENT',
        'CORRESPONDENCE_WITH_BUYER',
    ],
}
```

## Usage

### Payment Processing

```python
from paypal_integration.views import PayPalPaymentView
from paypal_integration.services import PayPalPaymentService

# Create a payment
payment_service = PayPalPaymentService()
order = payment_service.create_order(
    amount=Decimal('100.00'),
    currency='USD',
    description='Tutoring session payment',
    return_url='https://yoursite.com/paypal/success/',
    cancel_url='https://yoursite.com/paypal/cancel/',
    paypal_account=paypal_account
)

# Capture the payment
result = payment_service.capture_payment(
    order_id=order['id'],
    payer_id='PAYER_ID_FROM_RETURN',
    paypal_account=paypal_account
)
```

### Subscription Management

```python
from paypal_integration.services import PayPalPaymentService

# Create a subscription
service = PayPalPaymentService()
subscription = service.create_subscription(
    plan_id='BASIC_PLAN_ID',
    paypal_account=paypal_account,
    return_url='https://yoursite.com/paypal/subscription/success/',
    cancel_url='https://yoursite.com/paypal/subscription/cancel/'
)

# Cancel a subscription
service.cancel_subscription(
    subscription_id='SUBSCRIPTION_ID',
    paypal_account=paypal_account
)
```

### Payout Processing

```python
from paypal_integration.services import PayPalPaymentService

# Process a payout
service = PayPalPaymentService()
payout = service.create_payout(
    amount=Decimal('500.00'),
    currency='USD',
    paypal_account=paypal_account,
    recipient_email='tutor@example.com',
    note='Monthly earnings payout'
)
```

### Webhook Handling

Webhooks are automatically processed by the `PayPalWebhookView`. The following events are supported:

- `PAYMENT.SALE.COMPLETED`
- `PAYMENT.SALE.FAILED`
- `PAYMENT.SALE.REFUNDED`
- `BILLING.SUBSCRIPTION.CREATED`
- `BILLING.SUBSCRIPTION.CANCELLED`
- `DISPUTE.CREATED`
- `DISPUTE.RESOLVED`
- And more...

### Management Commands

#### Sync PayPal Transactions

```bash
python manage.py sync_paypal_transactions
```

This command syncs transactions from PayPal API to local database.

#### Process Webhooks

```bash
python manage.py process_paypal_webhooks
```

This command processes any pending webhook events.

#### Verify PayPal Accounts

```bash
python manage.py verify_paypal_accounts
```

This command verifies all PayPal accounts and refreshes expired tokens.

## Models

### PayPalAccount

Stores PayPal account information and OAuth tokens for API access.

### PayPalTransaction

Tracks all PayPal transactions with status, fees, and response data.

### PayPalWebhook

Logs all webhook events for audit and processing.

### PayPalSubscription

Manages recurring payment subscriptions.

### PayPalRefund

Handles refund transactions and their status.

### PayPalDispute

Tracks PayPal disputes and resolution status.

## Security

- All webhook requests are verified using PayPal's signature verification
- CSRF protection is implemented for all PayPal callbacks
- Rate limiting prevents abuse of webhook endpoints
- Sensitive data is encrypted at rest
- API requests use HTTPS with certificate pinning

## Testing

### Sandbox Mode

For testing, set `PAYPAL_CONFIG['MODE'] = 'sandbox'` in your settings. This will use PayPal's sandbox environment.

### Test Webhooks

Use the test webhook endpoint to simulate webhook events:

```bash
python manage.py process_paypal_webhooks --test
```

## Monitoring

### Logging

All PayPal requests, responses, and webhook events are logged. Configure logging in your Django settings:

```python
LOGGING = {
    'loggers': {
        'paypal_integration': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### Metrics

Track PayPal integration performance with the following metrics:

- API request latency
- Webhook processing time
- Transaction success rate
- Error rates by type

## Troubleshooting

### Common Issues

1. **Webhook Verification Fails**
   - Check webhook ID is correctly configured
   - Verify webhook URL is accessible from PayPal
   - Ensure SSL certificate is valid

2. **Payment Fails**
   - Check API credentials (client ID and secret)
   - Verify account has proper permissions
   - Check currency is supported

3. **Subscription Issues**
   - Verify plan exists in PayPal
   - Check webhook events are properly configured
   - Ensure subscription is not already cancelled

### Debug Mode

Enable debug mode by setting:

```python
PAYPAL_CONFIG['DEBUG'] = True
```

This will log detailed request/response data.

## API Reference

### PayPalPaymentService

- `create_order(amount, currency, description, return_url, cancel_url, paypal_account)`
- `capture_payment(order_id, payer_id, paypal_account)`
- `create_refund(transaction_id, amount, reason, paypal_account)`
- `create_subscription(plan_id, paypal_account, return_url, cancel_url)`
- `cancel_subscription(subscription_id, paypal_account)`
- `create_payout(amount, currency, paypal_account, recipient_email, note)`

### PayPalWebhookService

- `process_webhook(webhook)`
- `verify_webhook(payload, headers)`

### PayPalAPIService

- `make_request(method, endpoint, data=None, params=None)`
- `get_access_token(paypal_account)`
- `refresh_access_token(paypal_account)`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License.