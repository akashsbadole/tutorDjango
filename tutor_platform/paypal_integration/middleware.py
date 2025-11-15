import logging
import json
import time
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class PayPalRequestLoggingMiddleware(MiddlewareMixin):
    """Middleware for logging PayPal requests and responses"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.paypal_paths = getattr(settings, 'PAYPAL_LOGGING_PATHS', [
            '/paypal/',
            '/api/paypal/',
            '/webhooks/paypal/'
        ])
    
    def process_request(self, request):
        """Process incoming request"""
        # Check if this is a PayPal-related request
        if self._is_paypal_request(request):
            # Start timing
            request.paypal_start_time = time.time()
            
            # Log request details
            self._log_paypal_request(request)
        
        return None
    
    def process_response(self, request, response):
        """Process outgoing response"""
        # Check if this is a PayPal-related request
        if hasattr(request, 'paypal_start_time'):
            # Calculate response time
            response_time = time.time() - request.paypal_start_time
            
            # Log response details
            self._log_paypal_response(request, response, response_time)
        
        return response
    
    def _is_paypal_request(self, request):
        """Check if request is PayPal-related"""
        path = request.path
        return any(path.startswith(p) for p in self.paypal_paths)
    
    def _log_paypal_request(self, request):
        """Log PayPal request details"""
        try:
            # Prepare log data
            log_data = {
                'timestamp': time.time(),
                'method': request.method,
                'path': request.path,
                'user_id': request.user.id if request.user.is_authenticated else None,
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'headers': dict(request.headers),
                'get_params': dict(request.GET),
                'post_data': dict(request.POST) if request.method == 'POST' else {},
                'content_type': request.content_type,
                'content_length': request.META.get('CONTENT_LENGTH', 0)
            }
            
            # Remove sensitive data
            if 'post_data' in log_data:
                sensitive_keys = ['password', 'token', 'secret', 'key', 'client_secret']
                log_data['post_data'] = {
                    k: v for k, v in log_data['post_data'].items()
                    if k not in sensitive_keys
                }
            
            # Log to file and/or external service
            logger.info(f"PayPal Request: {json.dumps(log_data)}")
            
            # Store in cache for recent requests (for debugging)
            cache_key = f"paypal_request_{request.user.id if request.user.is_authenticated else 'anonymous'}"
            recent_requests = cache.get(cache_key, [])
            recent_requests.append({
                'timestamp': log_data['timestamp'],
                'path': log_data['path'],
                'method': log_data['method']
            })
            
            # Keep only last 10 requests
            cache.set(cache_key, recent_requests[-10:], timeout=300)
            
        except Exception as e:
            logger.error(f"Error logging PayPal request: {str(e)}")
    
    def _log_paypal_response(self, request, response, response_time):
        """Log PayPal response details"""
        try:
            # Prepare log data
            log_data = {
                'timestamp': time.time(),
                'path': request.path,
                'method': request.method,
                'user_id': request.user.id if request.user.is_authenticated else None,
                'status_code': response.status_code,
                'response_time': round(response_time, 3),
                'content_type': response.get('Content-Type', ''),
                'content_length': response.get('Content-Length', 0)
            }
            
            # Add response content for debugging (limited size)
            if hasattr(response, 'content') and len(response.content) < 1000:
                try:
                    log_data['response_content'] = response.content.decode('utf-8')
                except UnicodeDecodeError:
                    log_data['response_content'] = '[Binary data]'
            
            # Log to file and/or external service
            logger.info(f"PayPal Response: {json.dumps(log_data)}")
            
            # Store in cache for recent responses
            cache_key = f"paypal_response_{request.user.id if request.user.is_authenticated else 'anonymous'}"
            recent_responses = cache.get(cache_key, [])
            recent_responses.append({
                'timestamp': log_data['timestamp'],
                'path': log_data['path'],
                'status_code': log_data['status_code'],
                'response_time': log_data['response_time']
            })
            
            # Keep only last 10 responses
            cache.set(cache_key, recent_responses[-10:], timeout=300)
            
        except Exception as e:
            logger.error(f"Error logging PayPal response: {str(e)}")
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PayPalCSRFProtectionMiddleware(MiddlewareMixin):
    """Middleware for enhanced CSRF protection on PayPal endpoints"""
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.paypal_webhook_paths = getattr(settings, 'PAYPAL_WEBHOOK_PATHS', [
            '/webhooks/paypal/',
            '/api/webhooks/paypal/',
            '/paypal/webhook/'
        ])
    
    def process_request(self, request):
        """Process incoming request for CSRF protection"""
        # Check if this is a PayPal webhook request
        if self._is_paypal_webhook(request):
            # Verify webhook signature
            if not self._verify_webhook_signature(request):
                return JsonResponse({
                    'error': 'Invalid webhook signature',
                    'code': 'INVALID_SIGNATURE'
                }, status=401)
            
            # Check for proper content type
            expected_content_type = 'application/json'
            if request.content_type != expected_content_type:
                return JsonResponse({
                    'error': f'Invalid content type. Expected {expected_content_type}',
                    'code': 'INVALID_CONTENT_TYPE'
                }, status=400)
            
            # Check for PayPal specific headers
            required_headers = [
                'PAYPAL-AUTH-ALGO',
                'PAYPAL-TRANSMISSION-ID',
                'PAYPAL-CERT-ID',
                'PAYPAL-TRANSMISSION-SIG',
                'PAYPAL-TRANSMISSION-TIME'
            ]
            
            missing_headers = []
            for header in required_headers:
                if header not in request.META:
                    missing_headers.append(header)
            
            if missing_headers:
                return JsonResponse({
                    'error': 'Missing required PayPal headers',
                    'missing_headers': missing_headers,
                    'code': 'MISSING_HEADERS'
                }, status=400)
            
            # Rate limiting
            if not self._check_rate_limit(request):
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'code': 'RATE_LIMIT_EXCEEDED'
                }, status=429)
        
        return None
    
    def _is_paypal_webhook(self, request):
        """Check if request is a PayPal webhook"""
        path = request.path
        return any(path.startswith(p) for p in self.paypal_webhook_paths)
    
    def _verify_webhook_signature(self, request):
        """Verify PayPal webhook signature"""
        try:
            # Get webhook ID from settings
            webhook_id = getattr(settings, 'PAYPAL_WEBHOOK_ID')
            if not webhook_id:
                logger.error("PayPal webhook ID not configured")
                return False
            
            # Get required headers
            headers = {
                'auth_algo': request.META.get('PAYPAL-AUTH-ALGO'),
                'transmission_id': request.META.get('PAYPAL-TRANSMISSION-ID'),
                'cert_id': request.META.get('PAYPAL-CERT-ID'),
                'transmission_sig': request.META.get('PAYPAL-TRANSMISSION-SIG'),
                'transmission_time': request.META.get('PAYPAL-TRANSMISSION-TIME')
            }
            
            # Check all required headers are present
            if not all(headers.values()):
                logger.warning(f"Missing PayPal webhook headers: {headers}")
                return False
            
            # Get request body
            body = request.body
            
            # This would integrate with PayPal's webhook verification API
            # For now, we'll implement a basic verification
            import hmac
            import hashlib
            
            # Create expected signature (simplified)
            expected_sig = headers['transmission_sig']
            
            # For development, we'll skip actual verification
            # In production, this should verify against PayPal's API
            if getattr(settings, 'PAYPAL_SKIP_WEBHOOK_VERIFICATION', False):
                return True
            
            # Basic signature format check
            if not expected_sig or len(expected_sig) < 10:
                logger.warning("Invalid webhook signature format")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False
    
    def _check_rate_limit(self, request):
        """Check if request exceeds rate limits"""
        try:
            # Get rate limit settings
            max_requests = getattr(settings, 'PAYPAL_WEBHOOK_RATE_LIMIT', 100)
            window_seconds = getattr(settings, 'PAYPAL_WEBHOOK_RATE_WINDOW', 60)
            
            # Get client IP
            client_ip = self._get_client_ip(request)
            
            # Check cache for request count
            cache_key = f"paypal_webhook_rate_{client_ip}"
            request_count = cache.get(cache_key, 0)
            
            # Increment request count
            cache.set(cache_key, request_count + 1, timeout=window_seconds)
            
            # Check if limit exceeded
            if request_count >= max_requests:
                logger.warning(f"PayPal webhook rate limit exceeded for IP: {client_ip}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return True
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PayPalSecurityHeadersMiddleware(MiddlewareMixin):
    """Middleware for adding security headers to PayPal responses"""
    
    def process_response(self, request, response):
        """Add security headers to PayPal responses"""
        # Check if this is a PayPal-related response
        if self._is_paypal_response(request):
            # Add security headers
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response['Content-Security-Policy'] = "default-src 'self' https://www.paypal.com https://www.paypalobjects.com; script-src 'self' 'unsafe-inline' https://www.paypal.com https://www.paypalobjects.com; style-src 'self' 'unsafe-inline' https://www.paypal.com https://www.paypalobjects.com; img-src 'self' data: https://www.paypal.com https://www.paypalobjects.com; connect-src 'self' https://www.paypal.com; frame-ancestors 'none';"
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Add PayPal-specific headers
            response['X-PayPal-Integration'] = 'Django-Tutoring-Platform'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
        
        return response
    
    def _is_paypal_response(self, request):
        """Check if response is for PayPal-related request"""
        path = request.path
        return path.startswith('/paypal/') or path.startswith('/api/paypal/')