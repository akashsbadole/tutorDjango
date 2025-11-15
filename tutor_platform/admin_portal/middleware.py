"""
Django Tutor Platform Admin Portal Middleware

This module contains middleware for the admin portal including
access logging, session security, and permission validation.
"""

import time
import json
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.shortcuts import redirect

from .models import AdminSession, AdminActivityLog
from .utils import log_admin_activity, check_permission

User = get_user_model()


class AdminAccessLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all admin portal access and actions
    """
    
    def process_request(self, request):
        """Process incoming request for admin portal"""
        # Check if this is an admin portal request
        if request.path.startswith('/admin-panel/'):
            # Log the access attempt
            self._log_admin_access(request)
    
    def process_response(self, request, response):
        """Process response for admin portal"""
        # Check if this is an admin portal request
        if request.path.startswith('/admin-panel/'):
            # Log the response if it's a significant action
            if request.method in ['POST', 'PUT', 'DELETE']:
                self._log_admin_action(request, response)
        
        return response
    
    def _log_admin_access(self, request):
        """Log admin access attempt"""
        if request.user.is_authenticated:
            # Create or update admin session
            self._update_admin_session(request)
            
            # Log access
            log_admin_activity(
                admin=request.user,
                action_type='VIEW',
                action_description=f"Accessed {request.path}",
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                additional_data={
                    'method': request.method,
                    'path': request.path,
                    'query_params': dict(request.GET),
                }
            )
    
    def _log_admin_action(self, request, response):
        """Log admin action"""
        if request.user.is_authenticated and response.status_code < 400:
            # Try to get content type and object ID from the request
            content_type = None
            object_id = None
            
            if hasattr(request, 'resolver_match') and request.resolver_match:
                # Try to extract object ID from URL parameters
                if 'pk' in request.resolver_match.kwargs:
                    object_id = request.resolver_match.kwargs['pk']
                
                # Try to determine content type from URL name
                url_name = request.resolver_match.url_name
                if url_name:
                    app_label = url_name.split('_')[0] if '_' in url_name else None
                    if app_label:
                        try:
                            from django.contrib.contenttypes.models import ContentType
                            content_type = ContentType.objects.filter(
                                app_label=app_label
                            ).first()
                        except:
                            pass
            
            log_admin_activity(
                admin=request.user,
                action_type=self._get_action_type(request.method),
                action_description=f"{request.method} {request.path}",
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                content_type=content_type,
                object_id=object_id,
                additional_data={
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'post_data': dict(request.POST) if request.method == 'POST' else {},
                }
            )
    
    def _update_admin_session(self, request):
        """Update or create admin session"""
        if not request.user.is_authenticated:
            return
        
        # Get session key
        session_key = request.session.session_key
        
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        
        # Update or create admin session
        try:
            admin_session = AdminSession.objects.get(
                admin=request.user,
                session_key=session_key
            )
            
            # Update last activity
            admin_session.last_activity = now()
            admin_session.ip_address = self._get_client_ip(request)
            admin_session.user_agent = request.META.get('HTTP_USER_AGENT', '')
            admin_session.save()
            
        except AdminSession.DoesNotExist:
            # Create new admin session
            AdminSession.objects.create(
                admin=request.user,
                session_key=session_key,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                expires_at=now() + settings.SESSION_COOKIE_AGE
            )
    
    def _get_action_type(self, method):
        """Get action type from HTTP method"""
        action_mapping = {
            'GET': 'VIEW',
            'POST': 'CREATE',
            'PUT': 'UPDATE',
            'PATCH': 'UPDATE',
            'DELETE': 'DELETE',
        }
        return action_mapping.get(method, 'VIEW')
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminSessionSecurityMiddleware(MiddlewareMixin):
    """
    Middleware to enforce session security for admin users
    """
    
    def process_request(self, request):
        """Process request for session security"""
        # Only apply to admin portal requests
        if not request.path.startswith('/admin-panel/'):
            return None
        
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return None
        
        # Check if user has admin profile
        if not hasattr(request.user, 'admin_profile'):
            return redirect('admin_portal:access_denied')
        
        # Check session validity
        if not self._is_session_valid(request):
            # Log out user and redirect to login
            from django.contrib.auth import logout
            logout(request)
            return redirect('admin_portal:access_denied')
        
        # Check concurrent sessions
        if not self._check_concurrent_sessions(request):
            return redirect('admin_portal:access_denied')
        
        # Update session activity
        self._update_session_activity(request)
        
        return None
    
    def _is_session_valid(self, request):
        """Check if admin session is valid"""
        try:
            session_key = request.session.session_key
            if not session_key:
                return False
            
            admin_session = AdminSession.objects.get(
                admin=request.user,
                session_key=session_key,
                is_active=True
            )
            
            # Check if session is expired
            if admin_session.is_expired():
                admin_session.is_active = False
                admin_session.save()
                return False
            
            # Check IP address if required
            if getattr(settings, 'ADMIN_SESSION_IP_CHECK', False):
                current_ip = self._get_client_ip(request)
                if admin_session.ip_address != current_ip:
                    admin_session.is_active = False
                    admin_session.save()
                    return False
            
            return True
            
        except AdminSession.DoesNotExist:
            return False
    
    def _check_concurrent_sessions(self, request):
        """Check for concurrent sessions"""
        max_sessions = getattr(settings, 'ADMIN_MAX_CONCURRENT_SESSIONS', 3)
        
        if max_sessions <= 0:
            return True  # No limit
        
        active_sessions = AdminSession.objects.filter(
            admin=request.user,
            is_active=True,
            expires_at__gt=now()
        ).exclude(session_key=request.session.session_key)
        
        if active_sessions.count() >= max_sessions:
            # Deactivate oldest session
            oldest_session = active_sessions.order_by('last_activity').first()
            if oldest_session:
                oldest_session.is_active = False
                oldest_session.save()
        
        return True
    
    def _update_session_activity(self, request):
        """Update session activity timestamp"""
        try:
            session_key = request.session.session_key
            admin_session = AdminSession.objects.get(
                admin=request.user,
                session_key=session_key,
                is_active=True
            )
            
            admin_session.last_activity = now()
            admin_session.save()
            
        except AdminSession.DoesNotExist:
            pass
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminPermissionMiddleware(MiddlewareMixin):
    """
    Middleware to validate admin permissions
    """
    
    def process_request(self, request):
        """Process request for permission validation"""
        # Only apply to admin portal requests
        if not request.path.startswith('/admin-panel/'):
            return None
        
        # Skip permission check for login and access denied pages
        if request.path in ['/admin-panel/login/', '/admin-panel/access-denied/']:
            return None
        
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return redirect('admin_portal:login')
        
        # Check if user has admin profile
        if not hasattr(request.user, 'admin_profile'):
            return redirect('admin_portal:access_denied')
        
        # Check if user has basic admin access
        if not check_permission(request.user, 'dashboard'):
            return redirect('admin_portal:access_denied')
        
        # Check specific permissions based on URL
        required_permission = self._get_required_permission(request.path)
        if required_permission and not check_permission(request.user, required_permission):
            return redirect('admin_portal:access_denied')
        
        return None
    
    def _get_required_permission(self, path):
        """Get required permission for a given path"""
        permission_mapping = {
            '/admin-panel/users/': 'user_management',
            '/admin-panel/requirements/': 'requirement_management',
            '/admin-panel/payments/': 'payment_management',
            '/admin-panel/communications/': 'communication_monitoring',
            '/admin-panel/analytics/': 'system_analytics',
            '/admin-panel/export/': 'data_export',
            '/admin-panel/settings/': 'system_settings',
        }
        
        for url_pattern, permission in permission_mapping.items():
            if path.startswith(url_pattern):
                return permission
        
        return None


class AdminRateLimitMiddleware(MiddlewareMixin):
    """
    Middleware to implement rate limiting for admin portal
    """
    
    def process_request(self, request):
        """Process request for rate limiting"""
        # Only apply to admin portal requests
        if not request.path.startswith('/admin-panel/'):
            return None
        
        # Skip rate limiting for authenticated admin users with high privileges
        if (request.user.is_authenticated and 
            hasattr(request.user, 'admin_profile') and 
            request.user.admin_profile.is_super_admin):
            return None
        
        # Check rate limit
        if self._is_rate_limited(request):
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': _('Too many requests. Please try again later.')
            }, status=429)
        
        return None
    
    def _is_rate_limited(self, request):
        """Check if request is rate limited"""
        # Get rate limit settings
        rate_limit = getattr(settings, 'ADMIN_RATE_LIMIT', '100/m')
        max_requests, period = self._parse_rate_limit(rate_limit)
        
        # Get client identifier
        client_id = self._get_client_identifier(request)
        
        # Get current count from cache
        cache_key = f"admin_rate_limit:{client_id}"
        current_count = cache.get(cache_key, 0)
        
        # Check if rate limit is exceeded
        if current_count >= max_requests:
            return True
        
        # Increment count
        cache.set(cache_key, current_count + 1, self._get_period_seconds(period))
        
        return False
    
    def _parse_rate_limit(self, rate_limit):
        """Parse rate limit string"""
        try:
            max_requests, period = rate_limit.split('/')
            return int(max_requests), period
        except:
            return 100, 'm'  # Default: 100 requests per minute
    
    def _get_period_seconds(self, period):
        """Get period in seconds"""
        period_mapping = {
            's': 1,      # second
            'm': 60,     # minute
            'h': 3600,   # hour
            'd': 86400,  # day
        }
        return period_mapping.get(period, 60)
    
    def _get_client_identifier(self, request):
        """Get client identifier for rate limiting"""
        # Use user ID if authenticated
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        
        # Use IP address otherwise
        ip = self._get_client_ip(request)
        return f"ip:{ip}"
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class AdminSecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers for admin portal
    """
    
    def process_response(self, request, response):
        """Add security headers to response"""
        # Only apply to admin portal requests
        if request.path.startswith('/admin-panel/'):
            # Add security headers
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Add CSP header if enabled
            if getattr(settings, 'ADMIN_CSP_ENABLED', False):
                csp = self._get_csp_header()
                response['Content-Security-Policy'] = csp
        
        return response
    
    def _get_csp_header(self):
        """Get Content Security Policy header"""
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self'",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        
        return '; '.join(csp_directives)