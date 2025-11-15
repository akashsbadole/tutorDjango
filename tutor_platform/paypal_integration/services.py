import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import (
    PayPalAccount, PayPalTransaction, PayPalWebhook, 
    PayPalSubscription, PayPalRefund, PayPalDispute
)
from .utils import (
    PayPalClient, PayPalAPIError, process_paypal_response,
    calculate_paypal_fees, format_paypal_amount,
    log_paypal_api_request, retry_paypal_request
)

logger = logging.getLogger(__name__)


class PayPalAPIService:
    """Base service for PayPal API interactions"""
    
    def __init__(self, paypal_account=None):
        self.paypal_account = paypal_account
        self.client = self._get_client()
    
    def _get_client(self):
        """Get PayPal API client"""
        if self.paypal_account and self.paypal_account.access_token:
            # Check if token is expired
            if self.paypal_account.is_token_expired():
                self._refresh_token()
            
            return PayPalClient(
                sandbox=getattr(settings, 'PAYPAL_SANDBOX', True),
                access_token=self.paypal_account.access_token
            )
        else:
            client = PayPalClient(sandbox=getattr(settings, 'PAYPAL_SANDBOX', True))
            access_token = client.get_access_token()
            return client
    
    def _refresh_token(self):
        """Refresh PayPal access token"""
        if not self.paypal_account or not self.paypal_account.refresh_token:
            raise PayPalAPIError("No refresh token available")
        
        # This would implement OAuth token refresh
        # For now, just mark as expired
        self.paypal_account.refresh_access_token()
    
    @retry_paypal_request
    def make_api_call(self, method, endpoint, data=None):
        """Make API call with logging and error handling"""
        try:
            log_paypal_api_request(method, endpoint, data)
            response = self.client._make_request(method, endpoint, data)
            log_paypal_api_request(method, endpoint, data, response=response)
            return response
        except PayPalAPIError as e:
            log_paypal_api_request(method, endpoint, data, error=str(e))
            raise


class PayPalPaymentService(PayPalAPIService):
    """Service for PayPal payment processing"""
    
    def create_order(self, amount, currency, description, return_url, cancel_url, paypal_account):
        """Create PayPal order"""
        self.paypal_account = paypal_account
        self.client = self._get_client()
        
        order_data = {
            'intent': 'CAPTURE',
            'purchase_units': [{
                'reference_id': f"order_{timezone.now().timestamp()}",
                'description': description,
                'amount': format_paypal_amount(amount, currency),
                'custom_id': str(paypal_account.user.id)
            }],
            'application_context': {
                'return_url': return_url,
                'cancel_url': cancel_url,
                'brand_name': getattr(settings, 'SITE_NAME', 'Tutoring Platform'),
                'locale': 'en-US',
                'shipping_preference': 'NO_SHIPPING',
                'user_action': 'PAY_NOW'
            }
        }
        
        try:
            response = self.make_api_call('POST', '/v2/checkout/orders', order_data)
            
            # Extract approval URL
            approval_url = None
            for link in response.get('links', []):
                if link.get('rel') == 'approve':
                    approval_url = link['href']
                    break
            
            return {
                'success': True,
                'order_id': response['id'],
                'approval_url': approval_url,
                'response': response
            }
            
        except PayPalAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e, 'response_data', {})
            }
    
    def capture_payment(self, order_id, payer_id, paypal_account):
        """Capture PayPal payment"""
        self.paypal_account = paypal_account
        self.client = self._get_client()
        
        try:
            # Get order details first
            order_response = self.make_api_call('GET', f'/v2/checkout/orders/{order_id}')
            
            # Capture the payment
            capture_response = self.make_api_call(
                'POST', 
                f'/v2/checkout/orders/{order_id}/capture',
                {}
            )
            
            # Process the response
            processed_response = process_paypal_response(capture_response)
            
            if processed_response:
                # Get purchase unit details
                purchase_units = order_response.get('purchase_units', [])
                if purchase_units:
                    unit = purchase_units[0]
                    amount = Decimal(str(unit['amount']['value']))
                    currency = unit['amount']['currency']
                    
                    # Calculate fees
                    fee_info = calculate_paypal_fees(amount, currency, 'payment')
                    
                    return {
                        'success': True,
                        'transaction_id': processed_response['id'],
                        'amount': amount,
                        'currency': currency,
                        'fee_amount': fee_info['total_fee'],
                        'net_amount': fee_info['net_amount'],
                        'response': capture_response
                    }
            
            return {
                'success': False,
                'error': 'Failed to process payment response',
                'response': capture_response
            }
            
        except PayPalAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e, 'response_data', {})
            }
    
    def create_payout(self, amount, currency, paypal_account, recipient_email, note=''):
        """Create PayPal payout"""
        self.paypal_account = paypal_account
        self.client = self._get_client()
        
        # Calculate fees
        fee_info = calculate_paypal_fees(amount, currency, 'payout')
        
        payout_data = {
            'sender_batch_header': {
                'sender_batch_id': f"payout_{timezone.now().timestamp()}",
                'email_subject': 'Payout from Tutoring Platform',
                'recipient_type': 'EMAIL',
                'amount': {
                    'value': str(amount),
                    'currency': currency
                },
                'note': note,
                'notification_language': 'en-US'
            },
            'items': [{
                'recipient_type': 'EMAIL',
                'receiver': recipient_email,
                'note': note,
                'sender_item_id': f"item_{timezone.now().timestamp()}",
                'amount': {
                    'value': str(amount),
                    'currency': currency
                }
            }]
        }
        
        try:
            response = self.make_api_call('POST', '/v1/payments/payouts', payout_data)
            
            if response.get('batch_header', {}).get('batch_status') == 'PENDING':
                return {
                    'success': True,
                    'payout_id': response['batch_header']['payout_batch_id'],
                    'amount': amount,
                    'currency': currency,
                    'fee_amount': fee_info['total_fee'],
                    'net_amount': fee_info['net_amount'],
                    'response': response
                }
            else:
                return {
                    'success': False,
                    'error': f"Payout status: {response.get('batch_header', {}).get('batch_status')}",
                    'response': response
                }
                
        except PayPalAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e, 'response_data', {})
            }
    
    def create_refund(self, transaction_id, amount, paypal_account, reason=''):
        """Create PayPal refund"""
        self.paypal_account = paypal_account
        self.client = self._get_client()
        
        refund_data = {
            'amount': format_paypal_amount(amount, paypal_account.currency or 'USD'),
            'note_to_payer': reason
        }
        
        try:
            response = self.make_api_call(
                'POST', 
                f'/v2/payments/captures/{transaction_id}/refund',
                refund_data
            )
            
            processed_response = process_paypal_response(response)
            
            if processed_response:
                return {
                    'success': True,
                    'refund_id': processed_response['id'],
                    'amount': amount,
                    'currency': processed_response['currency'],
                    'response': response
                }
            
            return {
                'success': False,
                'error': 'Failed to process refund response',
                'response': response
            }
            
        except PayPalAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e, 'response_data', {})
            }
    
    def create_subscription(self, plan_id, paypal_account, return_url, cancel_url):
        """Create PayPal subscription"""
        self.paypal_account = paypal_account
        self.client = self._get_client()
        
        subscription_data = {
            'plan_id': plan_id,
            'application_context': {
                'brand_name': getattr(settings, 'SITE_NAME', 'Tutoring Platform'),
                'locale': 'en-US',
                'shipping_preference': 'NO_SHIPPING',
                'user_action': 'SUBSCRIBE_NOW',
                'payment_method': {
                    'payer_selected': 'PAYPAL',
                    'payee_preferred': 'IMMEDIATE_PAYMENT_REQUIRED'
                },
                'return_url': return_url,
                'cancel_url': cancel_url
            }
        }
        
        try:
            response = self.make_api_call('POST', '/v1/billing/subscriptions', subscription_data)
            
            # Extract approval URL
            approval_url = None
            for link in response.get('links', []):
                if link.get('rel') == 'approve':
                    approval_url = link['href']
                    break
            
            return {
                'success': True,
                'subscription_id': response['id'],
                'approval_url': approval_url,
                'response': response
            }
            
        except PayPalAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e, 'response_data', {})
            }
    
    def cancel_subscription(self, subscription_id, paypal_account):
        """Cancel PayPal subscription"""
        self.paypal_account = paypal_account
        self.client = self._get_client()
        
        cancel_data = {
            'reason': 'User requested cancellation'
        }
        
        try:
            response = self.make_api_call(
                'POST',
                f'/v1/billing/subscriptions/{subscription_id}/cancel',
                cancel_data
            )
            
            return {
                'success': True,
                'response': response
            }
            
        except PayPalAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e, 'response_data', {})
            }
    
    def get_subscription_details(self, subscription_id, paypal_account):
        """Get PayPal subscription details"""
        self.paypal_account = paypal_account
        self.client = self._get_client()
        
        try:
            response = self.make_api_call('GET', f'/v1/billing/subscriptions/{subscription_id}')
            return {
                'success': True,
                'response': response
            }
            
        except PayPalAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e, 'response_data', {})
            }
    
    def reactivate_subscription(self, subscription_id, paypal_account):
        """Reactivate PayPal subscription"""
        self.paypal_account = paypal_account
        self.client = self._get_client()
        
        reactivate_data = {
            'reason': 'User requested reactivation'
        }
        
        try:
            response = self.make_api_call(
                'POST',
                f'/v1/billing/subscriptions/{subscription_id}/activate',
                reactivate_data
            )
            
            return {
                'success': True,
                'response': response
            }
            
        except PayPalAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e, 'response_data', {})
            }
    
    def escalate_dispute(self, dispute_id, paypal_account):
        """Escalate PayPal dispute"""
        self.paypal_account = paypal_account
        self.client = self._get_client()
        
        escalate_data = {
            'notes': 'Escalating dispute to PayPal for resolution'
        }
        
        try:
            response = self.make_api_call(
                'POST',
                f'/v1/customer/disputes/{dispute_id}/escalate',
                escalate_data
            )
            
            return {
                'success': True,
                'response': response
            }
            
        except PayPalAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e, 'response_data', {})
            }


class PayPalWebhookService(PayPalAPIService):
    """Service for processing PayPal webhooks"""
    
    def __init__(self):
        # Webhook processing doesn't need a specific PayPal account
        super().__init__()
    
    def process_webhook(self, webhook):
        """Process a webhook event"""
        try:
            event_type = webhook.event_type
            payload = webhook.payload
            
            # Route to appropriate handler
            if event_type.startswith('PAYMENT.'):
                return self._process_payment_webhook(webhook, payload)
            elif event_type.startswith('BILLING.SUBSCRIPTION.'):
                return self._process_subscription_webhook(webhook, payload)
            elif event_type.startswith('PAYOUTS.'):
                return self._process_payout_webhook(webhook, payload)
            elif event_type.startswith('DISPUTE.'):
                return self._process_dispute_webhook(webhook, payload)
            else:
                logger.info(f"Unhandled webhook event type: {event_type}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing webhook {webhook.event_id}: {str(e)}")
            return False
    
    def _process_payment_webhook(self, webhook, payload):
        """Process payment-related webhooks"""
        try:
            resource = payload.get('resource', {})
            transaction_id = resource.get('id')
            
            if not transaction_id:
                logger.warning("No transaction ID in payment webhook")
                return False
            
            # Find existing transaction
            try:
                transaction = PayPalTransaction.objects.get(
                    paypal_transaction_id=transaction_id
                )
            except PayPalTransaction.DoesNotExist:
                logger.warning(f"Transaction {transaction_id} not found")
                return False
            
            # Update transaction status
            new_status = resource.get('status')
            if new_status:
                transaction.paypal_status = new_status
                
                if new_status == 'COMPLETED':
                    transaction.mark_completed()
                elif new_status == 'FAILED':
                    transaction.failure_reason = resource.get('status_details', {}).get('reason')
                
                transaction.save()
            
            logger.info(f"Updated transaction {transaction_id} status to {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing payment webhook: {str(e)}")
            return False
    
    def _process_subscription_webhook(self, webhook, payload):
        """Process subscription-related webhooks"""
        try:
            resource = payload.get('resource', {})
            subscription_id = resource.get('id')
            
            if not subscription_id:
                logger.warning("No subscription ID in subscription webhook")
                return False
            
            # Find existing subscription
            try:
                subscription = PayPalSubscription.objects.get(
                    paypal_subscription_id=subscription_id
                )
            except PayPalSubscription.DoesNotExist:
                logger.warning(f"Subscription {subscription_id} not found")
                return False
            
            # Update subscription status
            new_status = resource.get('status')
            if new_status:
                subscription.status = new_status
                
                if new_status == 'CANCELLED':
                    subscription.cancelled_at = timezone.now()
                    subscription.ends_at = resource.get('billing_info', {}).get('next_billing_time')
                elif new_status == 'ACTIVE':
                    subscription.current_period_start = timezone.now()
                    subscription.current_period_end = resource.get('billing_info', {}).get('next_billing_time')
                
                subscription.save()
            
            logger.info(f"Updated subscription {subscription_id} status to {new_status}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing subscription webhook: {str(e)}")
            return False
    
    def _process_payout_webhook(self, webhook, payload):
        """Process payout-related webhooks"""
        try:
            resource = payload.get('resource', {})
            payout_batch_id = resource.get('payout_batch_id')
            
            if not payout_batch_id:
                logger.warning("No payout batch ID in payout webhook")
                return False
            
            # Find related transactions
            transactions = PayPalTransaction.objects.filter(
                paypal_transaction_id__startswith=payout_batch_id,
                transaction_type=PayPalTransaction.TransactionType.PAYOUT
            )
            
            # Update transaction statuses
            payout_status = resource.get('transaction_status')
            for transaction in transactions:
                if payout_status == 'SUCCESS':
                    transaction.paypal_status = 'COMPLETED'
                    transaction.mark_completed()
                elif payout_status == 'FAILED':
                    transaction.paypal_status = 'FAILED'
                    transaction.failure_reason = resource.get('errors', [{}])[0].get('detail')
                
                transaction.save()
            
            logger.info(f"Updated payout transactions for batch {payout_batch_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing payout webhook: {str(e)}")
            return False
    
    def _process_dispute_webhook(self, webhook, payload):
        """Process dispute-related webhooks"""
        try:
            resource = payload.get('resource', {})
            dispute_id = resource.get('dispute_id')
            
            if not dispute_id:
                logger.warning("No dispute ID in dispute webhook")
                return False
            
            # Find or create dispute record
            dispute, created = PayPalDispute.objects.get_or_create(
                paypal_dispute_id=dispute_id,
                defaults={
                    'paypal_transaction': None,  # Would need to link to transaction
                    'status': resource.get('status'),
                    'reason': resource.get('reason'),
                    'amount': Decimal(str(resource.get('dispute_amount', {}).get('value', '0'))),
                    'currency': resource.get('dispute_amount', {}).get('currency', 'USD'),
                    'buyer_message': resource.get('buyer_message', ''),
                }
            )
            
            if not created:
                # Update existing dispute
                dispute.status = resource.get('status')
                dispute.resolution = resource.get('dispute_outcome', {}).get('reason')
                
                if resource.get('status') == 'RESOLVED':
                    dispute.resolved_at = timezone.now()
                
                dispute.save()
            
            logger.info(f"Processed dispute {dispute_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing dispute webhook: {str(e)}")
            return False


class PayPalAccountService(PayPalAPIService):
    """Service for PayPal account management"""
    
    def verify_account(self, paypal_account):
        """Verify PayPal account details"""
        self.paypal_account = paypal_account
        self.client = self._get_client()
        
        try:
            # Get account info
            response = self.make_api_call('GET', '/v1/identity/openidconnect/userinfo?schema=openid')
            
            if response:
                # Update account details
                paypal_account.paypal_user_id = response.get('user_id')
                paypal_account.verification_status = 'VERIFIED'
                paypal_account.metadata.update({
                    'verified_at': timezone.now().isoformat(),
                    'name': response.get('name'),
                    'email': response.get('email')
                })
                paypal_account.save()
                
                return {
                    'success': True,
                    'response': response
                }
            
            return {
                'success': False,
                'error': 'Failed to verify account'
            }
            
        except PayPalAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e, 'response_data', {})
            }
    
    def get_account_balance(self, paypal_account):
        """Get PayPal account balance"""
        self.paypal_account = paypal_account
        self.client = self._get_client()
        
        try:
            response = self.make_api_call('GET', '/v1/reporting/balances')
            
            if response and 'balances' in response:
                balances = []
                for balance in response['balances']:
                    balances.append({
                        'currency': balance['currency'],
                        'available': Decimal(str(balance['available_balance']['value'])),
                        'total': Decimal(str(balance['total_balance']['value'])),
                        'held': Decimal(str(balance['withheld_balance']['value'])),
                    })
                
                return {
                    'success': True,
                    'balances': balances,
                    'response': response
                }
            
            return {
                'success': False,
                'error': 'Failed to get account balance'
            }
            
        except PayPalAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e, 'response_data', {})
            }
    
    def get_transaction_history(self, paypal_account, start_date=None, end_date=None, page=1):
        """Get PayPal transaction history"""
        self.paypal_account = paypal_account
        self.client = self._get_client()
        
        params = {
            'page': page,
            'page_size': 50
        }
        
        if start_date:
            params['start_date'] = start_date.isoformat()
        if end_date:
            params['end_date'] = end_date.isoformat()
        
        try:
            # Build query string
            query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
            endpoint = f'/v1/reporting/transactions?{query_string}'
            response = self.make_api_call('GET', endpoint)
            
            if response and 'transaction_details' in response:
                transactions = []
                for transaction in response['transaction_details']:
                    transactions.append({
                        'transaction_id': transaction.get('transaction_id'),
                        'transaction_date': transaction.get('transaction_updated_date'),
                        'amount': Decimal(str(transaction.get('transaction_amount', {}).get('value', '0'))),
                        'currency': transaction.get('transaction_amount', {}).get('currency'),
                        'type': transaction.get('transaction_event_code'),
                        'status': transaction.get('transaction_status'),
                    })
                
                return {
                    'success': True,
                    'transactions': transactions,
                    'total_pages': response.get('total_pages', 1),
                    'response': response
                }
            
            return {
                'success': False,
                'error': 'Failed to get transaction history'
            }
            
        except PayPalAPIError as e:
            return {
                'success': False,
                'error': str(e),
                'response': getattr(e, 'response_data', {})
            }