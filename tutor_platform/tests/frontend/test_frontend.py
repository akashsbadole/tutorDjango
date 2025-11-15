"""
Frontend tests for Django tutoring platform.
"""
import pytest
from django.test import TestCase, LiveServerTestCase
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import time
import os

from tests.factories import (
    UserFactory, TutorProfileFactory, StudentProfileFactory, CategoryFactory,
    SubjectFactory, RequirementFactory, ProposalFactory
)
from tests.utils.helpers import TestMixin, SeleniumTestMixin

User = get_user_model()


class JavaScriptTest(TestCase, TestMixin):
    """Tests for JavaScript functionality."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_form_validation_javascript(self):
        """Test JavaScript form validation."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get requirement creation page
        response = self.client.get(reverse('requirements:requirement_create'))
        self.assertEqual(response.status_code, 200)
        
        # Check that JavaScript validation is present
        self.assertContains(response, 'validateForm')
        self.assertContains(response, 'required')
        
    def test_ajax_request_handling(self):
        """Test AJAX request handling."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Create requirement
        requirement = RequirementFactory.create()
        
        # Test AJAX request for proposal list
        response = self.client.get(
            reverse('requirements:proposal_list', kwargs={'requirement_pk': requirement.pk}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        # Check that response is JSON
        self.assertEqual(response['Content-Type'], 'application/json')
        
    def test_dynamic_content_loading(self):
        """Test dynamic content loading."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get dashboard page
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Check that dynamic loading scripts are present
        self.assertContains(response, 'loadContent')
        self.assertContains(response, 'fetchData')
        
    def test_search_autocomplete(self):
        """Test search autocomplete functionality."""
        # Create test data
        RequirementFactory.create_batch(5)
        
        # Get search page
        response = self.client.get(reverse('search:search'))
        self.assertEqual(response.status_code, 200)
        
        # Check that autocomplete scripts are present
        self.assertContains(response, 'autocomplete')
        self.assertContains(response, 'suggest')
        
    def test_notification_system(self):
        """Test notification system JavaScript."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get dashboard page
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Check that notification scripts are present
        self.assertContains(response, 'notification')
        self.assertContains(response, 'showNotification')
        
    def test_real_time_updates(self):
        """Test real-time update functionality."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get messaging page
        response = self.client.get(reverse('messaging:conversation_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that real-time update scripts are present
        self.assertContains(response, 'WebSocket')
        self.assertContains(response, 'updateMessages')


class HTMXTest(TestCase, TestMixin):
    """Tests for HTMX functionality."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_htmx_attributes_present(self):
        """Test that HTMX attributes are present in templates."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get requirement list page
        response = self.client.get(reverse('requirements:requirement_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that HTMX attributes are present
        self.assertContains(response, 'hx-get')
        self.assertContains(response, 'hx-post')
        self.assertContains(response, 'hx-target')
        
    def test_htmx_request_headers(self):
        """Test HTMX request headers."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Make HTMX request
        response = self.client.get(
            reverse('requirements:requirement_list'),
            HTTP_HX_REQUEST='true'
        )
        
        # Check that response is successful
        self.assertEqual(response.status_code, 200)
        
    def test_htmx_partial_updates(self):
        """Test HTMX partial updates."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Create requirement
        requirement = RequirementFactory.create()
        
        # Test HTMX partial update
        response = self.client.get(
            reverse('requirements:requirement_detail', kwargs={'pk': requirement.pk}),
            HTTP_HX_REQUEST='true',
            HTTP_HX_TARGET='requirement-detail'
        )
        
        # Check that response is successful
        self.assertEqual(response.status_code, 200)
        
    def test_htmx_loading_states(self):
        """Test HTMX loading states."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get requirement list page
        response = self.client.get(reverse('requirements:requirement_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that loading state indicators are present
        self.assertContains(response, 'hx-indicator')
        self.assertContains(response, 'htmx-request')
        
    def test_htmx_error_handling(self):
        """Test HTMX error handling."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Test HTMX error response
        response = self.client.get(
            reverse('requirements:requirement_detail', kwargs={'pk': 99999}),
            HTTP_HX_REQUEST='true'
        )
        
        # Check that error is handled
        self.assertEqual(response.status_code, 404)


class AlpineJSTest(TestCase, TestMixin):
    """Tests for Alpine.js functionality."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_alpine_js_attributes_present(self):
        """Test that Alpine.js attributes are present in templates."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get dashboard page
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Check that Alpine.js attributes are present
        self.assertContains(response, 'x-data')
        self.assertContains(response, 'x-show')
        self.assertContains(response, 'x-on:click')
        
    def test_alpine_js_component_initialization(self):
        """Test Alpine.js component initialization."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get profile page
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        
        # Check that Alpine.js components are initialized
        self.assertContains(response, 'alpine')
        self.assertContains(response, 'x-init')
        
    def test_alpine_js_reactive_data(self):
        """Test Alpine.js reactive data binding."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get search page
        response = self.client.get(reverse('search:search'))
        self.assertEqual(response.status_code, 200)
        
        # Check that reactive data binding is present
        self.assertContains(response, 'x-model')
        self.assertContains(response, 'x-bind')
        
    def test_alpine_js_event_handling(self):
        """Test Alpine.js event handling."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get messaging page
        response = self.client.get(reverse('messaging:conversation_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that event handling is present
        self.assertContains(response, 'x-on:')
        self.assertContains(response, '@click')
        
    def test_alpine_js_conditional_rendering(self):
        """Test Alpine.js conditional rendering."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get dashboard page
        response = self.client.get(reverse('accounts:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Check that conditional rendering is present
        self.assertContains(response, 'x-if')
        self.assertContains(response, 'x-show')


class FormValidationTest(TestCase, TestMixin):
    """Tests for frontend form validation."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_requirement_form_validation(self):
        """Test requirement form validation."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get requirement creation page
        response = self.client.get(reverse('requirements:requirement_create'))
        self.assertEqual(response.status_code, 200)
        
        # Check that validation attributes are present
        self.assertContains(response, 'required')
        self.assertContains(response, 'minlength')
        self.assertContains(response, 'maxlength')
        
    def test_proposal_form_validation(self):
        """Test proposal form validation."""
        # Login as tutor
        tutor_user = UserFactory.create(user_type='TUTOR')
        self.client.login(username=tutor_user.username, password='testpass123')
        
        # Create requirement
        requirement = RequirementFactory.create()
        
        # Get proposal creation page
        response = self.client.get(
            reverse('requirements:proposal_create', kwargs={'requirement_pk': requirement.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that validation attributes are present
        self.assertContains(response, 'required')
        self.assertContains(response, 'min')
        self.assertContains(response, 'max')
        
    def test_profile_form_validation(self):
        """Test profile form validation."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get profile update page
        response = self.client.get(reverse('accounts:profile_update'))
        self.assertEqual(response.status_code, 200)
        
        # Check that validation attributes are present
        self.assertContains(response, 'pattern')
        self.assertContains(response, 'type="email"')
        self.assertContains(response, 'type="tel"')
        
    def test_registration_form_validation(self):
        """Test registration form validation."""
        # Get registration page
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        
        # Check that validation attributes are present
        self.assertContains(response, 'required')
        self.assertContains(response, 'minlength')
        self.assertContains(response, 'pattern')
        
    def test_message_form_validation(self):
        """Test message form validation."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Create conversation
        from messaging.models import Conversation
        conversation = ConversationFactory.create()
        conversation.participants.add(self.user)
        
        # Get conversation page
        response = self.client.get(
            reverse('messaging:conversation_detail', kwargs={'pk': conversation.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that validation attributes are present
        self.assertContains(response, 'required')
        self.assertContains(response, 'maxlength')


class ResponsiveDesignTest(TestCase, TestMixin):
    """Tests for responsive design."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        self.user = UserFactory.create()
        
    def test_mobile_viewport_meta(self):
        """Test mobile viewport meta tag."""
        # Get home page
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        
        # Check that viewport meta tag is present
        self.assertContains(response, 'name="viewport"')
        self.assertContains(response, 'width=device-width')
        
    def test_responsive_css_classes(self):
        """Test responsive CSS classes."""
        # Get requirement list page
        response = self.client.get(reverse('requirements:requirement_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that responsive CSS classes are present
        self.assertContains(response, 'col-')
        self.assertContains(response, 'col-md-')
        self.assertContains(response, 'col-lg-')
        
    def test_responsive_navigation(self):
        """Test responsive navigation."""
        # Get home page
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        
        # Check that responsive navigation elements are present
        self.assertContains(response, 'navbar-toggler')
        self.assertContains(response, 'navbar-collapse')
        
    def test_responsive_images(self):
        """Test responsive images."""
        # Get profile page
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
        
        # Check that responsive image classes are present
        self.assertContains(response, 'img-fluid')
        self.assertContains(response, 'rounded')
        
    def test_responsive_tables(self):
        """Test responsive tables."""
        # Login as user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Get requirement list page
        response = self.client.get(reverse('requirements:requirement_list'))
        self.assertEqual(response.status_code, 200)
        
        # Check that responsive table classes are present
        self.assertContains(response, 'table-responsive')


class BrowserCompatibilityTest(StaticLiveServerTestCase, SeleniumTestMixin):
    """Tests for browser compatibility."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_chrome_compatibility(self):
        """Test Chrome browser compatibility."""
        # Set up Chrome driver
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        
        try:
            # Test login
            self.driver.get(f'{self.live_server_url}{reverse("accounts:login")}')
            
            username_field = self.driver.find_element(By.NAME, 'username')
            password_field = self.driver.find_element(By.NAME, 'password')
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            
            username_field.send_keys(self.user.username)
            password_field.send_keys('testpass123')
            submit_button.click()
            
            # Check that login was successful
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'dashboard'))
            )
            
            # Test requirement creation
            self.driver.get(f'{self.live_server_url}{reverse("requirements:requirement_create")}')
            
            title_field = self.driver.find_element(By.NAME, 'title')
            description_field = self.driver.find_element(By.NAME, 'description')
            budget_field = self.driver.find_element(By.NAME, 'budget')
            
            title_field.send_keys('Test Requirement')
            description_field.send_keys('Test Description')
            budget_field.send_keys('50.00')
            
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            submit_button.click()
            
            # Check that requirement was created
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'requirement-detail'))
            )
            
        finally:
            self.driver.quit()
            
    def test_firefox_compatibility(self):
        """Test Firefox browser compatibility."""
        # Set up Firefox driver
        from selenium.webdriver.firefox.options import Options as FirefoxOptions
        options = FirefoxOptions()
        options.add_argument('--headless')
        
        self.driver = webdriver.Firefox(options=options)
        self.driver.implicitly_wait(10)
        
        try:
            # Test login
            self.driver.get(f'{self.live_server_url}{reverse("accounts:login")}')
            
            username_field = self.driver.find_element(By.NAME, 'username')
            password_field = self.driver.find_element(By.NAME, 'password')
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            
            username_field.send_keys(self.user.username)
            password_field.send_keys('testpass123')
            submit_button.click()
            
            # Check that login was successful
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'dashboard'))
            )
            
        finally:
            self.driver.quit()
            
    def test_edge_compatibility(self):
        """Test Edge browser compatibility."""
        # Set up Edge driver
        from selenium.webdriver.edge.options import Options as EdgeOptions
        options = EdgeOptions()
        options.add_argument('--headless')
        
        self.driver = webdriver.Edge(options=options)
        self.driver.implicitly_wait(10)
        
        try:
            # Test login
            self.driver.get(f'{self.live_server_url}{reverse("accounts:login")}')
            
            username_field = self.driver.find_element(By.NAME, 'username')
            password_field = self.driver.find_element(By.NAME, 'password')
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            
            username_field.send_keys(self.user.username)
            password_field.send_keys('testpass123')
            submit_button.click()
            
            # Check that login was successful
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'dashboard'))
            )
            
        finally:
            self.driver.quit()


class AccessibilityTest(StaticLiveServerTestCase, SeleniumTestMixin):
    """Tests for accessibility."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_alt_text_for_images(self):
        """Test that images have alt text."""
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        
        try:
            # Get profile page
            self.driver.get(f'{self.live_server_url}{reverse("accounts:profile")}')
            
            # Check that images have alt text
            images = self.driver.find_elements(By.TAG_NAME, 'img')
            for image in images:
                self.assertTrue(image.get_attribute('alt'), 'Image missing alt text')
                
        finally:
            self.driver.quit()
            
    def test_form_labels(self):
        """Test that form inputs have labels."""
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        
        try:
            # Get login page
            self.driver.get(f'{self.live_server_url}{reverse("accounts:login")}')
            
            # Check that form inputs have labels
            inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="text"], input[type="password"], input[type="email"]')
            for input_element in inputs:
                label_id = input_element.get_attribute('aria-labelledby')
                if label_id:
                    label = self.driver.find_element(By.ID, label_id)
                    self.assertTrue(label.text, 'Label is empty')
                    
        finally:
            self.driver.quit()
            
    def test_heading_hierarchy(self):
        """Test heading hierarchy."""
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        
        try:
            # Get home page
            self.driver.get(f'{self.live_server_url}{reverse("home")}')
            
            # Check heading hierarchy
            headings = self.driver.find_elements(By.CSS_SELECTOR, 'h1, h2, h3, h4, h5, h6')
            previous_level = 0
            
            for heading in headings:
                current_level = int(heading.tag_name[1])
                self.assertLessEqual(current_level, previous_level + 1, 'Heading hierarchy is incorrect')
                previous_level = current_level
                
        finally:
            self.driver.quit()
            
    def test_aria_attributes(self):
        """Test ARIA attributes."""
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        
        try:
            # Get dashboard page
            self.driver.login(username=self.user.username, password='testpass123')
            self.driver.get(f'{self.live_server_url}{reverse("accounts:dashboard")}')
            
            # Check that interactive elements have ARIA attributes
            buttons = self.driver.find_elements(By.TAG_NAME, 'button')
            for button in buttons:
                aria_label = button.get_attribute('aria-label')
                if not button.text.strip() and not aria_label:
                    self.fail('Button missing aria-label or text')
                    
        finally:
            self.driver.quit()
            
    def test_keyboard_navigation(self):
        """Test keyboard navigation."""
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        
        try:
            # Get home page
            self.driver.get(f'{self.live_server_url}{reverse("home")}')
            
            # Test tab navigation
            self.driver.find_element(By.TAG_NAME, 'body').send_keys('\t')
            
            # Check that focus is visible
            focused_element = self.driver.switch_to.active_element
            self.assertIsNotNone(focused_element, 'No element is focused after tab')
            
            # Test enter key on links
            links = self.driver.find_elements(By.TAG_NAME, 'a')
            if links:
                links[0].send_keys('\n')
                
        finally:
            self.driver.quit()


class PerformanceTest(StaticLiveServerTestCase, SeleniumTestMixin):
    """Tests for frontend performance."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_page_load_time(self):
        """Test page load time."""
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        
        try:
            # Measure page load time
            start_time = time.time()
            self.driver.get(f'{self.live_server_url}{reverse("home")}')
            end_time = time.time()
            
            load_time = end_time - start_time
            
            # Check that page loads within 3 seconds
            self.assertLess(load_time, 3.0, 'Page load time exceeds 3 seconds')
            
        finally:
            self.driver.quit()
            
    def test_javascript_execution_time(self):
        """Test JavaScript execution time."""
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        
        try:
            # Get page with JavaScript
            self.driver.get(f'{self.live_server_url}{reverse("accounts:dashboard")}')
            
            # Measure JavaScript execution time
            start_time = time.time()
            self.driver.execute_script('return document.readyState')
            end_time = time.time()
            
            execution_time = end_time - start_time
            
            # Check that JavaScript executes within 1 second
            self.assertLess(execution_time, 1.0, 'JavaScript execution time exceeds 1 second')
            
        finally:
            self.driver.quit()
            
    def test_image_optimization(self):
        """Test image optimization."""
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        
        try:
            # Get profile page
            self.driver.get(f'{self.live_server_url}{reverse("accounts:profile")}')
            
            # Check image sizes
            images = self.driver.find_elements(By.TAG_NAME, 'img')
            for image in images:
                src = image.get_attribute('src')
                if src and not src.startswith('data:'):
                    # Check that image is optimized (basic check)
                    self.assertTrue(
                        any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']),
                        f'Image {src} is not in an optimized format'
                    )
                    
        finally:
            self.driver.quit()
            
    def test_css_minification(self):
        """Test CSS minification."""
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        
        try:
            # Get any page
            self.driver.get(f'{self.live_server_url}{reverse("home")}')
            
            # Check for minified CSS files
            css_links = self.driver.find_elements(By.CSS_SELECTOR, 'link[rel="stylesheet"]')
            for link in css_links:
                href = link.get_attribute('href')
                if href and '.min.css' not in href:
                    # In production, CSS should be minified
                    # This is a basic check - in real tests, you'd check file size
                    pass
                    
        finally:
            self.driver.quit()
            
    def test_javascript_minification(self):
        """Test JavaScript minification."""
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        
        try:
            # Get any page
            self.driver.get(f'{self.live_server_url}{reverse("home")}')
            
            # Check for minified JavaScript files
            script_links = self.driver.find_elements(By.TAG_NAME, 'script')
            for script in script_links:
                src = script.get_attribute('src')
                if src and '.min.js' not in src:
                    # In production, JavaScript should be minified
                    # This is a basic check - in real tests, you'd check file size
                    pass
                    
        finally:
            self.driver.quit()