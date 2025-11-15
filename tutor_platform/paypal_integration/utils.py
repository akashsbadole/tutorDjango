import json
import logging
import hashlib
import hmac
import requests
from decimal import Decimal
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


class PayPalAPIError(Exception):
    """Custom exception for PayPal API errors"""
    pass


class PayPalClient:
    """PayPal API client for making HTTP requests"""
    
    def __init__(self, sandbox=None, access_token=None):
        self.sandbox = sandbox if sandbox is not None else getattr(settings, 'PAYPAL_SANDBOX', True)
        self.access_token = access_token
        self.base_url = self._get_base_url()
        self.timeout = getattr(settings, 'PAYPAL_TIMEOUT', 30)
    
    def _get_base_url(self):
        """Get PayPal API base URL based on sandbox mode"""
        if self.sandbox:
            return 'https://api-m.sandbox.paypal.com'
        return 'https://api-m.paypal.com'
    
    def _get_headers(self):
        """Get headers for API requests"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Language': 'en_US',
        }
        
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        return headers
    
    def _handle_response(self, response):
        """Handle API response and errors"""
        try:
            response_data = response.json()
        except ValueError:
            response_data = {}
        
        if response.status_code >= 400:
            error_message = response_data.get('message', 'Unknown PayPal API error')
            error_details = response_data.get('details', [])
            
            if error_details:
                error_message += f": {', '.join([detail.get('issue', '') for detail in error_details])}"
            
            logger.error(f"PayPal API error: {response.status_code} - {error_message}")
            raise PayPalAPIError(error_message, response.status_code, response_data)
        
        return response_data
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make HTTP request to PayPal API"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            return self._handle_response(response)
        except requests.exceptions.RequestException as e:
            logger.error(f"PayPal API request failed: {str(e)}")
            raise PayPalAPIError(f"Request failed: {str(e)}")
    
    def get_access_token(self):
        """Get OAuth access token from PayPal"""
        client_id = getattr(settings, 'PAYPAL_CLIENT_ID')
        client_secret = getattr(settings, 'PAYPAL_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ImproperlyConfigured("PayPal client ID and secret must be configured")
        
        endpoint = '/v1/oauth2/token'
        data = {
            'grant_type': 'client_credentials'
        }
        
        # Use basic auth for token request
        auth = (client_id, client_secret)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.post(
                url=f"{self.base_url}{endpoint}",
                data=data,
                headers=headers,
                auth=auth,
                timeout=self.timeout
            )
            
            response_data = self._handle_response(response)
            self.access_token = response_data['access_token']
            return self.access_token
            
        except Exception as e:
            logger.error(f"Failed to get PayPal access token: {str(e)}")
            raise PayPalAPIError(f"Authentication failed: {str(e)}")
    
    def get(self, endpoint, params=None):
        """Make GET request to PayPal API"""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint, data=None):
        """Make POST request to PayPal API"""
        return self._make_request('POST', endpoint, data=data)
    
    def patch(self, endpoint, data=None):
        """Make PATCH request to PayPal API"""
        return self._make_request('PATCH', endpoint, data=data)
    
    def delete(self, endpoint):
        """Make DELETE request to PayPal API"""
        return self._make_request('DELETE', endpoint)


def verify_webhook_signature(payload, headers):
    """Verify PayPal webhook signature"""
    try:
        # Get webhook ID from settings
        webhook_id = getattr(settings, 'PAYPAL_WEBHOOK_ID')
        if not webhook_id:
            logger.error("PayPal webhook ID not configured")
            return False
        
        # Get required headers
        auth_algo = headers.get('PAYPAL-AUTH-ALGO')
        transmission_id = headers.get('PAYPAL-TRANSMISSION-ID')
        cert_id = headers.get('PAYPAL-CERT-ID')
        transmission_sig = headers.get('PAYPAL-TRANSMISSION-SIG')
        transmission_time = headers.get('PAYPAL-TRANSMISSION-TIME')
        
        if not all([auth_algo, transmission_id, cert_id, transmission_sig, transmission_time]):
            logger.error("Missing required webhook headers")
            return False
        
        # Get access token for verification
        client = PayPalClient()
        access_token = client.get_access_token()
        
        # Prepare verification payload
        verification_data = {
            'auth_algo': auth_algo,
            'cert_id': cert_id,
            'transmission_id': transmission_id,
            'transmission_sig': transmission_sig,
            'transmission_time': transmission_time,
            'webhook_id': webhook_id,
            'webhook_event': payload
        }
        
        # Verify with PayPal
        response = client.post('/v1/notifications/verify-webhook-signature', verification_data)
        
        return response.get('verification_status') == 'SUCCESS'
        
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {str(e)}")
        return False


def process_paypal_response(response_data):
    """Process and normalize PayPal API response"""
    try:
        if not response_data:
            return None
        
        # Extract common fields
        processed = {
            'id': response_data.get('id'),
            'status': response_data.get('status'),
            'intent': response_data.get('intent'),
            'amount': None,
            'currency': None,
            'fee_amount': Decimal('0.00'),
            'net_amount': None,
            'response': response_data
        }
        
        # Extract amount information
        if 'amount' in response_data:
            amount_info = response_data['amount']
            processed['amount'] = Decimal(str(amount_info.get('value', '0')))
            processed['currency'] = amount_info.get('currency', 'USD')
        
        # Extract fee information
        if 'transaction_fee' in response_data:
            fee_info = response_data['transaction_fee']
            processed['fee_amount'] = Decimal(str(fee_info.get('value', '0')))
        
        # Calculate net amount
        if processed['amount']:
            processed['net_amount'] = processed['amount'] - processed['fee_amount']
        
        # Extract payer information
        if 'payer' in response_data:
            payer_info = response_data['payer']
            processed['payer_id'] = payer_info.get('payer_id')
            processed['payer_email'] = payer_info.get('email_address')
        
        # Extract purchase unit information for orders
        if 'purchase_units' in response_data:
            purchase_units = response_data['purchase_units']
            if purchase_units:
                unit = purchase_units[0]
                if 'amount' in unit:
                    amount_info = unit['amount']
                    processed['amount'] = Decimal(str(amount_info.get('value', '0')))
                    processed['currency'] = amount_info.get('currency', 'USD')
                
                if 'reference_id' in unit:
                    processed['reference_id'] = unit['reference_id']
        
        return processed
        
    except Exception as e:
        logger.error(f"Error processing PayPal response: {str(e)}")
        return None


def calculate_paypal_fees(amount, currency='USD', transaction_type='payment'):
    """Calculate PayPal fees based on transaction type and amount"""
    try:
        # PayPal fee structure (example rates - should be configured in settings)
        fee_config = getattr(settings, 'PAYPAL_FEE_CONFIG', {
            'domestic': {
                'percentage': 0.029,  # 2.9%
                'fixed': Decimal('0.30')  # $0.30
            },
            'international': {
                'percentage': 0.044,  # 4.4%
                'fixed': Decimal('0.30')  # $0.30
            },
            'payout': {
                'domestic': {
                    'percentage': 0.02,  # 2%
                    'fixed': Decimal('0.25')  # $0.25
                },
                'international': {
                    'percentage': 0.02,  # 2%
                    'fixed': Decimal('4.99')  # $4.99
                }
            }
        })
        
        # Determine if transaction is international (simplified logic)
        is_international = currency != 'USD'
        
        if transaction_type == 'payout':
            config = fee_config['payout']['international' if is_international else 'domestic']
        else:
            config = fee_config['international' if is_international else 'domestic']
        
        # Calculate percentage fee
        percentage_fee = amount * Decimal(str(config['percentage']))
        
        # Calculate total fee
        total_fee = percentage_fee + config['fixed']
        
        # Ensure fee doesn't exceed amount
        total_fee = min(total_fee, amount)
        
        return {
            'percentage_fee': percentage_fee,
            'fixed_fee': config['fixed'],
            'total_fee': total_fee,
            'net_amount': amount - total_fee
        }
        
    except Exception as e:
        logger.error(f"Error calculating PayPal fees: {str(e)}")
        return {
            'percentage_fee': Decimal('0.00'),
            'fixed_fee': Decimal('0.00'),
            'total_fee': Decimal('0.00'),
            'net_amount': amount
        }


def format_paypal_amount(amount, currency='USD'):
    """Format amount for PayPal API"""
    return {
        'currency_code': currency,
        'value': str(round(amount, 2))
    }


def parse_paypal_date(date_string):
    """Parse PayPal date string to datetime object"""
    try:
        # PayPal uses ISO 8601 format
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        logger.error(f"Error parsing PayPal date: {date_string}")
        return timezone.now()


def sanitize_paypal_webhook_payload(payload):
    """Sanitize webhook payload for storage"""
    try:
        if not isinstance(payload, dict):
            return {}
        
        # Remove sensitive information
        sanitized = {}
        
        # Copy safe fields
        safe_fields = [
            'id', 'event_type', 'resource_type', 'event_version',
            'create_time', 'resource', 'summary', 'status'
        ]
        
        for field in safe_fields:
            if field in payload:
                sanitized[field] = payload[field]
        
        # Sanitize resource data
        if 'resource' in payload:
            resource = payload['resource']
            if isinstance(resource, dict):
                # Remove sensitive fields from resource
                sensitive_fields = [
                    'payer_info', 'shipping_address', 'billing_address',
                    'credit_card', 'bank_account', 'funding_instruments'
                ]
                
                sanitized_resource = {}
                for key, value in resource.items():
                    if key not in sensitive_fields:
                        sanitized_resource[key] = value
                
                sanitized['resource'] = sanitized_resource
        
        return sanitized
        
    except Exception as e:
        logger.error(f"Error sanitizing webhook payload: {str(e)}")
        return {}


def validate_paypal_currency(currency):
    """Validate PayPal currency code"""
    supported_currencies = getattr(settings, 'PAYPAL_SUPPORTED_CURRENCIES', [
        'USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'CHF', 'SEK', 'NOK', 'DKK'
    ])
    
    return currency.upper() in supported_currencies


def get_paypal_error_message(error_data):
    """Extract user-friendly error message from PayPal error response"""
    try:
        if not isinstance(error_data, dict):
            return "Unknown PayPal error"
        
        # Check for message field
        if 'message' in error_data:
            message = error_data['message']
            
            # Check for details
            if 'details' in error_data:
                details = error_data['details']
                if isinstance(details, list) and details:
                    # Get first detail issue
                    first_detail = details[0]
                    if 'issue' in first_detail:
                        return f"{message}: {first_detail['issue']}"
            
            return message
        
        # Check for error field
        if 'error' in error_data:
            error = error_data['error']
            if isinstance(error, str):
                return error
            elif isinstance(error, dict) and 'message' in error:
                return error['message']
        
        # Check for name field
        if 'name' in error_data:
            return error_data['name']
        
        return "Unknown PayPal error"
        
    except Exception as e:
        logger.error(f"Error parsing PayPal error message: {str(e)}")
        return "Unknown PayPal error"


def create_paypal_request_id():
    """Create unique request ID for PayPal API calls"""
    import uuid
    return str(uuid.uuid4())


def log_paypal_api_request(method, endpoint, data=None, response=None, error=None):
    """Log PayPal API requests and responses"""
    try:
        log_data = {
            'timestamp': timezone.now().isoformat(),
            'method': method,
            'endpoint': endpoint,
            'request_id': create_paypal_request_id()
        }
        
        if data:
            # Sanitize sensitive data
            sanitized_data = data.copy()
            sensitive_keys = ['client_secret', 'access_token', 'refresh_token']
            for key in sensitive_keys:
                if key in sanitized_data:
                    sanitized_data[key] = '***REDACTED***'
            log_data['request_data'] = sanitized_data
        
        if response:
            log_data['response_status'] = 'success'
            log_data['response_data'] = response
        
        if error:
            log_data['response_status'] = 'error'
            log_data['error'] = str(error)
        
        logger.info(f"PayPal API Request: {json.dumps(log_data)}")
        
    except Exception as e:
        logger.error(f"Error logging PayPal API request: {str(e)}")


def retry_paypal_request(func, max_retries=3, backoff_factor=1):
    """Decorator for retrying PayPal API requests"""
    def wrapper(*args, **kwargs):
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except PayPalAPIError as e:
                last_exception = e
                
                # Don't retry on authentication errors
                if e.status_code in [401, 403]:
                    break
                
                # Don't retry on the last attempt
                if attempt == max_retries:
                    break
                
                # Calculate backoff delay
                delay = backoff_factor * (2 ** attempt)
                logger.warning(f"PayPal API request failed, retrying in {delay}s: {str(e)}")
                
                import time
                time.sleep(delay)
        
        raise last_exception
    
    return wrapper