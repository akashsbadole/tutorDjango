"""
Security test mixins for Django tutoring platform.
"""
import pytest
from django.test import TestCase
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock

User = get_user_model()


class SecurityTestMixin:
    """Mixin with security testing utilities."""
    
    def assertNoSQLInjection(self, response, malicious_input):
        """Assert that SQL injection was not successful."""
        # Check that response is successful
        self.assertEqual(response.status_code, 200)
        
        # Check that no SQL errors occurred
        self.assertNotIn('SQL', response.content.decode())
        self.assertNotIn('syntax error', response.content.decode())
        self.assertNotIn('mysql', response.content.decode())
        self.assertNotIn('postgresql', response.content.decode())
        
    def assertNoXSS(self, response, xss_payload):
        """Assert that XSS payload is properly escaped."""
        # Check that XSS payload is escaped
        self.assertNotIn('<script>', response.content.decode())
        self.assertNotIn('javascript:', response.content.decode())
        self.assertNotIn('onerror=', response.content.decode())
        self.assertNotIn('onload=', response.content.decode())
        
        # Check that escaped version exists
        self.assertIn('<script>', response.content.decode())
        
    def assertCSRFProtected(self, response):
        """Assert that CSRF protection is active."""
        # Check that request is rejected without CSRF token
        self.assertEqual(response.status_code, 403)
        
    def assertRateLimited(self, response):
        """Assert that request is rate limited."""
        # Check that request is rate limited
        self.assertEqual(response.status_code, 429)
        
    def assertSecureHeaders(self, response):
        """Assert that security headers are present."""
        # Check for security headers
        self.assertIn('X-Content-Type-Options', response)
        self.assertIn('X-Frame-Options', response)
        self.assertIn('X-XSS-Protection', response)
        
        # Check header values
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['X-Frame-Options'], 'DENY')
        
    def assertNoDataLeakage(self, response, sensitive_data):
        """Assert that sensitive data is not leaked."""
        # Check that sensitive data is not in response
        for data in sensitive_data:
            self.assertNotIn(data, response.content.decode())
            
    def assertSecureCookie(self, response, cookie_name):
        """Assert that cookie is secure."""
        # Check that cookie has secure attributes
        cookie = response.cookies.get(cookie_name)
        if cookie:
            if settings.SESSION_COOKIE_SECURE:
                self.assertTrue(cookie.get('secure'))
            if settings.SESSION_COOKIE_HTTPONLY:
                self.assertTrue(cookie.get('httponly'))
            if settings.CSRF_COOKIE_SECURE:
                self.assertTrue(cookie.get('secure'))
            if settings.CSRF_COOKIE_HTTPONLY:
                self.assertTrue(cookie.get('httponly'))
                
    def assertNoPasswordLeakage(self, response):
        """Assert that password is not leaked."""
        # Check that password-related data is not in response
        self.assertNotIn('password', response.content.decode())
        self.assertNotIn('Password', response.content.decode())
        self.assertNotIn('PASSWORD', response.content.decode())
        self.assertNotIn('passwd', response.content.decode())
        self.assertNotIn('secret', response.content.decode())
        
    def assertNoTokenLeakage(self, response):
        """Assert that tokens are not leaked."""
        # Check that token-related data is not in response
        self.assertNotIn('token', response.content.decode())
        self.assertNotIn('Token', response.content.decode())
        self.assertNotIn('TOKEN', response.content.decode())
        self.assertNotIn('api_key', response.content.decode())
        self.assertNotIn('secret_key', response.content.decode())
        
    def assertNoInternalErrorLeakage(self, response):
        """Assert that internal errors are not leaked."""
        # Check that internal error information is not in response
        self.assertNotIn('traceback', response.content.decode())
        self.assertNotIn('Traceback', response.content.decode())
        self.assertNotIn('Traceback (most recent call last)', response.content.decode())
        self.assertNotIn('Exception', response.content.decode())
        self.assertNotIn('Error', response.content.decode())
        self.assertNotIn('error', response.content.decode())
        self.assertNotIn('debug', response.content.decode())
        self.assertNotIn('DEBUG', response.content.decode())
        
    def assertNoDatabaseLeakage(self, response):
        """Assert that database information is not leaked."""
        # Check that database information is not in response
        self.assertNotIn('database', response.content.decode())
        self.assertNotIn('Database', response.content.decode())
        self.assertNotIn('DATABASE', response.content.decode())
        self.assertNotIn('query', response.content.decode())
        self.assertNotIn('Query', response.content.decode())
        self.assertNotIn('QUERY', response.content.decode())
        self.assertNotIn('SELECT', response.content.decode())
        self.assertNotIn('INSERT', response.content.decode())
        self.assertNotIn('UPDATE', response.content.decode())
        self.assertNotIn('DELETE', response.content.decode())
        
    def assertNoFileSystemLeakage(self, response):
        """Assert that file system information is not leaked."""
        # Check that file system information is not in response
        self.assertNotIn('/etc/', response.content.decode())
        self.assertNotIn('/var/', response.content.decode())
        self.assertNotIn('/usr/', response.content.decode())
        self.assertNotIn('/home/', response.content.decode())
        self.assertNotIn('C:\\', response.content.decode())
        self.assertNotIn('D:\\', response.content.decode())
        self.assertNotIn('file://', response.content.decode())
        self.assertNotIn('FILE://', response.content.decode())
        
    def assertNoServerLeakage(self, response):
        """Assert that server information is not leaked."""
        # Check that server information is not in response
        self.assertNotIn('apache', response.content.decode())
        self.assertNotIn('nginx', response.content.decode())
        self.assertNotIn('gunicorn', response.content.decode())
        self.assertNotIn('uwsgi', response.content.decode())
        self.assertNotIn('mod_wsgi', response.content.decode())
        self.assertNotIn('Server:', response.content.decode())
        self.assertNotIn('server:', response.content.decode())
        
    def assertNoPythonLeakage(self, response):
        """Assert that Python information is not leaked."""
        # Check that Python information is not in response
        self.assertNotIn('python', response.content.decode())
        self.assertNotIn('Python', response.content.decode())
        self.assertNotIn('PYTHON', response.content.decode())
        self.assertNotIn('django', response.content.decode())
        self.assertNotIn('Django', response.content.decode())
        self.assertNotIn('DJANGO', response.content.decode())
        self.assertNotIn('pip', response.content.decode())
        self.assertNotIn('virtualenv', response.content.decode())
        
    def assertNoDependencyLeakage(self, response):
        """Assert that dependency information is not leaked."""
        # Check that dependency information is not in response
        self.assertNotIn('requirements.txt', response.content.decode())
        self.assertNotIn('package.json', response.content.decode())
        self.assertNotIn('yarn.lock', response.content.decode())
        self.assertNotIn('Pipfile', response.content.decode())
        self.assertNotIn('poetry.lock', response.content.decode())
        
    def assertNoVersionLeakage(self, response):
        """Assert that version information is not leaked."""
        # Check that version information is not in response
        self.assertNotIn('version', response.content.decode())
        self.assertNotIn('Version', response.content.decode())
        self.assertNotIn('VERSION', response.content.decode())
        self.assertNotIn('v1.', response.content.decode())
        self.assertNotIn('v2.', response.content.decode())
        self.assertNotIn('v3.', response.content.decode())
        
    def assertNoConfigLeakage(self, response):
        """Assert that configuration information is not leaked."""
        # Check that configuration information is not in response
        self.assertNotIn('settings.py', response.content.decode())
        self.assertNotIn('config.py', response.content.decode())
        self.assertNotIn('env', response.content.decode())
        self.assertNotIn('ENV', response.content.decode())
        self.assertNotIn('environment', response.content.decode())
        self.assertNotIn('Environment', response.content.decode())
        
    def assertNoIPLeakage(self, response):
        """Assert that IP addresses are not leaked."""
        # Check that IP addresses are not in response
        import re
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ips = re.findall(ip_pattern, response.content.decode())
        
        # Filter out common non-sensitive IPs
        non_sensitive_ips = ['127.0.0.1', '0.0.0.0', '255.255.255.255']
        for ip in ips:
            if ip not in non_sensitive_ips:
                self.fail(f"IP address {ip} found in response")
                
    def assertNoEmailLeakage(self, response, allowed_emails=None):
        """Assert that email addresses are not leaked."""
        # Check that email addresses are not in response
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, response.content.decode())
        
        # Filter out allowed emails
        if allowed_emails:
            for email in emails:
                if email not in allowed_emails:
                    self.fail(f"Email address {email} found in response")
        else:
            # If no allowed emails, any email is a potential leak
            for email in emails:
                # Filter out common non-sensitive emails
                non_sensitive_emails = ['noreply@example.com', 'support@example.com', 'admin@example.com']
                if email not in non_sensitive_emails:
                    self.fail(f"Email address {email} found in response")
                    
    def assertNoPhoneLeakage(self, response):
        """Assert that phone numbers are not leaked."""
        # Check that phone numbers are not in response
        import re
        phone_patterns = [
            r'\b\d{3}-\d{3}-\d{4}\b',  # 123-456-7890
            r'\b\(\d{3}\) \d{3}-\d{4}\b',  # (123) 456-7890
            r'\b\d{3} \d{3} \d{4}\b',  # 123 456 7890
            r'\b\+\d{1,3} \d{3} \d{3} \d{4}\b',  # +1 123 456 7890
        ]
        
        for pattern in phone_patterns:
            phones = re.findall(pattern, response.content.decode())
            for phone in phones:
                self.fail(f"Phone number {phone} found in response")
                
    def assertNoSSNLeakage(self, response):
        """Assert that Social Security Numbers are not leaked."""
        # Check that SSNs are not in response
        import re
        ssn_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # 123-45-6789
            r'\b\d{3} \d{2} \d{4}\b',  # 123 45 6789
        ]
        
        for pattern in ssn_patterns:
            ssns = re.findall(pattern, response.content.decode())
            for ssn in ssns:
                self.fail(f"SSN {ssn} found in response")
                
    def assertNoCreditCardLeakage(self, response):
        """Assert that credit card numbers are not leaked."""
        # Check that credit card numbers are not in response
        import re
        cc_patterns = [
            r'\b\d{4} \d{4} \d{4} \d{4}\b',  # 1234 5678 9012 3456
            r'\b\d{4}-\d{4}-\d{4}-\d{4}\b',  # 1234-5678-9012-3456
            r'\b\d{16}\b',  # 1234567890123456
        ]
        
        for pattern in cc_patterns:
            ccs = re.findall(pattern, response.content.decode())
            for cc in ccs:
                self.fail(f"Credit card number {cc} found in response")
                
    def assertNoBankAccountLeakage(self, response):
        """Assert that bank account numbers are not leaked."""
        # Check that bank account numbers are not in response
        import re
        ba_patterns = [
            r'\b\d{10,12}\b',  # 10-12 digit account numbers
            r'\b\d{4} \d{4} \d{4}\b',  # 1234 5678 9012
            r'\b\d{4}-\d{4}-\d{4}\b',  # 1234-5678-9012
        ]
        
        for pattern in ba_patterns:
            bas = re.findall(pattern, response.content.decode())
            for ba in bas:
                self.fail(f"Bank account number {ba} found in response")
                
    def assertNoRoutingLeakage(self, response):
        """Assert that routing numbers are not leaked."""
        # Check that routing numbers are not in response
        import re
        routing_pattern = r'\b\d{9}\b'  # 9-digit routing numbers
        
        routings = re.findall(routing_pattern, response.content.decode())
        for routing in routings:
            self.fail(f"Routing number {routing} found in response")
            
    def assertNoPasswordResetTokenLeakage(self, response):
        """Assert that password reset tokens are not leaked."""
        # Check that password reset tokens are not in response
        import re
        token_patterns = [
            r'\b[a-zA-Z0-9]{20,}\b',  # Long alphanumeric tokens
            r'\b[a-zA-Z0-9_-]{20,}\b',  # Tokens with special characters
        ]
        
        for pattern in token_patterns:
            tokens = re.findall(pattern, response.content.decode())
            for token in tokens:
                self.fail(f"Potential token {token} found in response")
                
    def assertNoSessionIDLeakage(self, response):
        """Assert that session IDs are not leaked."""
        # Check that session IDs are not in response
        import re
        session_patterns = [
            r'\b[a-zA-Z0-9]{32}\b',  # 32-character session IDs
            r'\b[a-zA-Z0-9]{40}\b',  # 40-character session IDs
            r'\b[a-zA-Z0-9]{64}\b',  # 64-character session IDs
        ]
        
        for pattern in session_patterns:
            sessions = re.findall(pattern, response.content.decode())
            for session in sessions:
                self.fail(f"Potential session ID {session} found in response")
                
    def assertNoAPIKeyLeakage(self, response):
        """Assert that API keys are not leaked."""
        # Check that API keys are not in response
        import re
        api_key_patterns = [
            r'\bAIza[a-zA-Z0-9_-]{35}\b',  # Google API keys
            r'\bAKIA[a-zA-Z0-9]{16}\b',  # AWS access keys
            r'\b[a-zA-Z0-9]{32}\b',  # Generic 32-character API keys
            r'\b[a-zA-Z0-9]{40}\b',  # Generic 40-character API keys
            r'\b[a-zA-Z0-9]{64}\b',  # Generic 64-character API keys
        ]
        
        for pattern in api_key_patterns:
            api_keys = re.findall(pattern, response.content.decode())
            for api_key in api_keys:
                self.fail(f"Potential API key {api_key} found in response")
                
    def assertNoSecretLeakage(self, response):
        """Assert that secrets are not leaked."""
        # Check that secrets are not in response
        import re
        secret_patterns = [
            r'\b[a-zA-Z0-9]{32}\b',  # 32-character secrets
            r'\b[a-zA-Z0-9]{40}\b',  # 40-character secrets
            r'\b[a-zA-Z0-9]{64}\b',  # 64-character secrets
            r'\b[a-zA-Z0-9]{128}\b',  # 128-character secrets
        ]
        
        for pattern in secret_patterns:
            secrets = re.findall(pattern, response.content.decode())
            for secret in secrets:
                self.fail(f"Potential secret {secret} found in response")
                
    def assertNoPrivateKeyLeakage(self, response):
        """Assert that private keys are not leaked."""
        # Check that private keys are not in response
        self.assertNotIn('-----BEGIN PRIVATE KEY-----', response.content.decode())
        self.assertNotIn('-----BEGIN RSA PRIVATE KEY-----', response.content.decode())
        self.assertNotIn('-----BEGIN DSA PRIVATE KEY-----', response.content.decode())
        self.assertNotIn('-----BEGIN EC PRIVATE KEY-----', response.content.decode())
        self.assertNotIn('-----BEGIN OPENSSH PRIVATE KEY-----', response.content.decode())
        self.assertNotIn('-----END PRIVATE KEY-----', response.content.decode())
        self.assertNotIn('-----END RSA PRIVATE KEY-----', response.content.decode())
        self.assertNotIn('-----END DSA PRIVATE KEY-----', response.content.decode())
        self.assertNotIn('-----END EC PRIVATE KEY-----', response.content.decode())
        self.assertNotIn('-----END OPENSSH PRIVATE KEY-----', response.content.decode())
        
    def assertNoCertificateLeakage(self, response):
        """Assert that certificates are not leaked."""
        # Check that certificates are not in response
        self.assertNotIn('-----BEGIN CERTIFICATE-----', response.content.decode())
        self.assertNotIn('-----END CERTIFICATE-----', response.content.decode())
        
    def assertNoSSHKeyLeakage(self, response):
        """Assert that SSH keys are not leaked."""
        # Check that SSH keys are not in response
        self.assertNotIn('ssh-rsa', response.content.decode())
        self.assertNotIn('ssh-dss', response.content.decode())
        self.assertNotIn('ssh-ed25519', response.content.decode())
        self.assertNotIn('ecdsa-sha2-', response.content.decode())
        
    def assertNoDatabaseConnectionLeakage(self, response):
        """Assert that database connection strings are not leaked."""
        # Check that database connection strings are not in response
        self.assertNotIn('mysql://', response.content.decode())
        self.assertNotIn('postgresql://', response.content.decode())
        self.assertNotIn('sqlite://', response.content.decode())
        self.assertNotIn('mongodb://', response.content.decode())
        self.assertNotIn('redis://', response.content.decode())
        self.assertNotIn('elasticsearch://', response.content.decode())
        
    def assertNoCloudCredentialsLeakage(self, response):
        """Assert that cloud credentials are not leaked."""
        # Check that cloud credentials are not in response
        self.assertNotIn('aws_access_key_id', response.content.decode())
        self.assertNotIn('aws_secret_access_key', response.content.decode())
        self.assertNotIn('google_application_credentials', response.content.decode())
        self.assertNotIn('azure_subscription_id', response.content.decode())
        self.assertNotIn('azure_client_secret', response.content.decode())
        
    def assertNoThirdPartyCredentialsLeakage(self, response):
        """Assert that third-party credentials are not leaked."""
        # Check that third-party credentials are not in response
        self.assertNotIn('stripe_secret_key', response.content.decode())
        self.assertNotIn('stripe_publishable_key', response.content.decode())
        self.assertNotIn('paypal_client_id', response.content.decode())
        self.assertNotIn('paypal_client_secret', response.content.decode())
        self.assertNotIn('github_token', response.content.decode())
        self.assertNotIn('facebook_app_secret', response.content.decode())
        self.assertNotIn('twitter_consumer_secret', response.content.decode())
        
    def assertNoEnvironmentVariableLeakage(self, response):
        """Assert that environment variables are not leaked."""
        # Check that environment variables are not in response
        import re
        env_pattern = r'\b[A-Z_]{2,}=[a-zA-Z0-9_/.-]+\b'
        envs = re.findall(env_pattern, response.content.decode())
        
        for env in envs:
            # Filter out common non-sensitive environment variables
            non_sensitive_envs = ['PATH=', 'HOME=', 'USER=', 'LANG=', 'TERM=', 'SHELL=']
            is_non_sensitive = any(env.startswith(non_sensitive) for non_sensitive in non_sensitive_envs)
            
            if not is_non_sensitive:
                self.fail(f"Environment variable {env} found in response")
                
    def assertNoDebugInformationLeakage(self, response):
        """Assert that debug information is not leaked."""
        # Check that debug information is not in response
        self.assertNotIn('DEBUG = True', response.content.decode())
        self.assertNotIn('DEBUG=True', response.content.decode())
        self.assertNotIn('settings.DEBUG', response.content.decode())
        self.assertNotIn('django-debug-toolbar', response.content.decode())
        self.assertNotIn('django_extensions', response.content.decode())
        
    def assertNoAdminPanelLeakage(self, response):
        """Assert that admin panel information is not leaked."""
        # Check that admin panel information is not in response
        self.assertNotIn('/admin/', response.content.decode())
        self.assertNotIn('Django administration', response.content.decode())
        self.assertNotIn('Site administration', response.content.decode())
        
    def assertNoFrameworkLeakage(self, response):
        """Assert that framework information is not leaked."""
        # Check that framework information is not in response
        self.assertNotIn('Django', response.content.decode())
        self.assertNotIn('django', response.content.decode())
        self.assertNotIn('Flask', response.content.decode())
        self.assertNotIn('flask', response.content.decode())
        self.assertNotIn('Rails', response.content.decode())
        self.assertNotIn('rails', response.content.decode())
        self.assertNotIn('Laravel', response.content.decode())
        self.assertNotIn('laravel', response.content.decode())
        
    def assertNoServerSoftwareLeakage(self, response):
        """Assert that server software information is not leaked."""
        # Check that server software information is not in response
        self.assertNotIn('Apache', response.content.decode())
        self.assertNotIn('apache', response.content.decode())
        self.assertNotIn('Nginx', response.content.decode())
        self.assertNotIn('nginx', response.content.decode())
        self.assertNotIn('Gunicorn', response.content.decode())
        self.assertNotIn('gunicorn', response.content.decode())
        self.assertNotIn('uWSGI', response.content.decode())
        self.assertNotIn('uwsgi', response.content.decode())
        
    def assertNoDatabaseSoftwareLeakage(self, response):
        """Assert that database software information is not leaked."""
        # Check that database software information is not in response
        self.assertNotIn('MySQL', response.content.decode())
        self.assertNotIn('mysql', response.content.decode())
        self.assertNotIn('PostgreSQL', response.content.decode())
        self.assertNotIn('postgresql', response.content.decode())
        self.assertNotIn('SQLite', response.content.decode())
        self.assertNotIn('sqlite', response.content.decode())
        self.assertNotIn('MongoDB', response.content.decode())
        self.assertNotIn('mongodb', response.content.decode())
        self.assertNotIn('Redis', response.content.decode())
        self.assertNotIn('redis', response.content.decode())
        
    def assertNoCacheSoftwareLeakage(self, response):
        """Assert that cache software information is not leaked."""
        # Check that cache software information is not in response
        self.assertNotIn('Memcached', response.content.decode())
        self.assertNotIn('memcached', response.content.decode())
        self.assertNotIn('Redis', response.content.decode())
        self.assertNotIn('redis', response.content.decode())
        self.assertNotIn('Varnish', response.content.decode())
        self.assertNotIn('varnish', response.content.decode())
        
    def assertNoSearchEngineLeakage(self, response):
        """Assert that search engine information is not leaked."""
        # Check that search engine information is not in response
        self.assertNotIn('Elasticsearch', response.content.decode())
        self.assertNotIn('elasticsearch', response.content.decode())
        self.assertNotIn('Solr', response.content.decode())
        self.assertNotIn('solr', response.content.decode())
        self.assertNotIn('Algolia', response.content.decode())
        self.assertNotIn('algolia', response.content.decode())
        
    def assertNoQueueSoftwareLeakage(self, response):
        """Assert that queue software information is not leaked."""
        # Check that queue software information is not in response
        self.assertNotIn('Celery', response.content.decode())
        self.assertNotIn('celery', response.content.decode())
        self.assertNotIn('RabbitMQ', response.content.decode())
        self.assertNotIn('rabbitmq', response.content.decode())
        self.assertNotIn('Kafka', response.content.decode())
        self.assertNotIn('kafka', response.content.decode())
        
    def assertNoMonitoringSoftwareLeakage(self, response):
        """Assert that monitoring software information is not leaked."""
        # Check that monitoring software information is not in response
        self.assertNotIn('Prometheus', response.content.decode())
        self.assertNotIn('prometheus', response.content.decode())
        self.assertNotIn('Grafana', response.content.decode())
        self.assertNotIn('grafana', response.content.decode())
        self.assertNotIn('New Relic', response.content.decode())
        self.assertNotIn('Datadog', response.content.decode())
        
    def assertNoLoggingSoftwareLeakage(self, response):
        """Assert that logging software information is not leaked."""
        # Check that logging software information is not in response
        self.assertNotIn('Logstash', response.content.decode())
        self.assertNotIn('logstash', response.content.decode())
        self.assertNotIn('Fluentd', response.content.decode())
        self.assertNotIn('fluentd', response.content.decode())
        self.assertNotIn('Splunk', response.content.decode())
        self.assertNotIn('splunk', response.content.decode())
        
    def assertNoContainerSoftwareLeakage(self, response):
        """Assert that container software information is not leaked."""
        # Check that container software information is not in response
        self.assertNotIn('Docker', response.content.decode())
        self.assertNotIn('docker', response.content.decode())
        self.assertNotIn('Kubernetes', response.content.decode())
        self.assertNotIn('kubernetes', response.content.decode())
        self.assertNotIn('K8s', response.content.decode())
        self.assertNotIn('k8s', response.content.decode())
        
    def assertNoCloudProviderLeakage(self, response):
        """Assert that cloud provider information is not leaked."""
        # Check that cloud provider information is not in response
        self.assertNotIn('AWS', response.content.decode())
        self.assertNotIn('Amazon Web Services', response.content.decode())
        self.assertNotIn('Google Cloud', response.content.decode())
        self.assertNotIn('GCP', response.content.decode())
        self.assertNotIn('Azure', response.content.decode())
        self.assertNotIn('Microsoft Azure', response.content.decode())
        self.assertNotIn('DigitalOcean', response.content.decode())
        self.assertNotIn('Heroku', response.content.decode())
        self.assertNotIn('Vercel', response.content.decode())
        self.assertNotIn('Netlify', response.content.decode())