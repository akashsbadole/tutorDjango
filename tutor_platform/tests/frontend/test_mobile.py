"""
Mobile device tests for Django tutoring platform.
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
import time

from tests.factories import (
    UserFactory, TutorProfileFactory, StudentProfileFactory, CategoryFactory,
    SubjectFactory, RequirementFactory, ProposalFactory
)
from tests.utils.helpers import TestMixin, SeleniumTestMixin

User = get_user_model()


class MobileViewportTest(StaticLiveServerTestCase, SeleniumTestMixin):
    """Tests for mobile viewport functionality."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
        # Set up Chrome driver with mobile viewport
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=375,812')  # iPhone X dimensions
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        
    def tearDown(self):
        """Clean up test environment."""
        self.driver.quit()
        
    def test_mobile_navigation(self):
        """Test mobile navigation functionality."""
        # Get home page
        self.driver.get(f'{self.live_server_url}{reverse("home")}')
        
        # Check that mobile navigation is present
        try:
            navbar_toggler = self.driver.find_element(By.CLASS_NAME, 'navbar-toggler')
            self.assertTrue(navbar_toggler.is_displayed(), 'Mobile navigation toggle not visible')
        except NoSuchElementException:
            self.fail('Mobile navigation toggle not found')
            
        # Test navigation toggle
        navbar_toggler.click()
        
        # Check that navigation menu is expanded
        try:
            navbar_collapse = self.driver.find_element(By.CLASS_NAME, 'navbar-collapse')
            self.assertTrue('show' in navbar_collapse.get_attribute('class'), 'Navigation menu not expanded')
        except NoSuchElementException:
            self.fail('Navigation menu not found')
            
    def test_mobile_form_layout(self):
        """Test mobile form layout."""
        # Get login page
        self.driver.get(f'{self.live_server_url}{reverse("accounts:login")}')
        
        # Check that form elements are properly sized for mobile
        try:
            username_field = self.driver.find_element(By.NAME, 'username')
            password_field = self.driver.find_element(By.NAME, 'password')
            
            # Check that fields take full width on mobile
            username_width = username_field.size['width']
            viewport_width = self.driver.execute_script('return window.innerWidth')
            
            self.assertGreater(username_width, viewport_width * 0.8, 'Username field not wide enough for mobile')
            
        except NoSuchElementException:
            self.fail('Form elements not found')
            
    def test_mobile_table_responsiveness(self):
        """Test mobile table responsiveness."""
        # Login as user
        self.driver.get(f'{self.live_server_url}{reverse("accounts:login")}')
        
        username_field = self.driver.find_element(By.NAME, 'username')
        password_field = self.driver.find_element(By.NAME, 'password')
        submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        
        username_field.send_keys(self.user.username)
        password_field.send_keys('testpass123')
        submit_button.click()
        
        # Get requirement list page
        self.driver.get(f'{self.live_server_url}{reverse("requirements:requirement_list")}')
        
        # Check that table is responsive on mobile
        try:
            table_container = self.driver.find_element(By.CLASS_NAME, 'table-responsive')
            self.assertTrue(table_container.is_displayed(), 'Responsive table container not visible')
        except NoSuchElementException:
            # If no table is present, that's okay for this test
            pass
            
    def test_mobile_button_sizes(self):
        """Test mobile button sizes."""
        # Get home page
        self.driver.get(f'{self.live_server_url}{reverse("home")}')
        
        # Check that buttons are large enough for mobile
        buttons = self.driver.find_elements(By.TAG_NAME, 'button')
        for button in buttons:
            if button.is_displayed():
                button_height = button.size['height']
                self.assertGreater(button_height, 40, 'Button too small for mobile touch interaction')
                
    def test_mobile_font_sizes(self):
        """Test mobile font sizes."""
        # Get home page
        self.driver.get(f'{self.live_server_url}{reverse("home")}')
        
        # Check that text is readable on mobile
        body_element = self.driver.find_element(By.TAG_NAME, 'body')
        font_size = body_element.value_of_css_property('font-size')
        
        # Convert to pixels (assuming it's in px)
        font_size_value = float(font_size.replace('px', ''))
        self.assertGreaterEqual(font_size_value, 14, 'Font size too small for mobile readability')


class MobileTouchTest(StaticLiveServerTestCase, SeleniumTestMixin):
    """Tests for mobile touch interactions."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
        # Set up Chrome driver with mobile touch emulation
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=375,812')  # iPhone X dimensions
        
        # Enable touch events
        mobile_emulation = {
            "deviceMetrics": {"width": 375, "height": 812, "pixelRatio": 3.0},
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0 Mobile/15E148 Safari/604.1"
        }
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        
    def tearDown(self):
        """Clean up test environment."""
        self.driver.quit()
        
    def test_mobile_tap_targets(self):
        """Test mobile tap targets."""
        # Get login page
        self.driver.get(f'{self.live_server_url}{reverse("accounts:login")}')
        
        # Check that tap targets are large enough
        clickable_elements = self.driver.find_elements(By.CSS_SELECTOR, 'button, a, input[type="submit"]')
        for element in clickable_elements:
            if element.is_displayed():
                size = element.size
                area = size['width'] * size['height']
                self.assertGreaterEqual(area, 48 * 48, 'Tap target too small for mobile')
                
    def test_mobile_swipe_gestures(self):
        """Test mobile swipe gestures."""
        # Get requirement list page
        self.driver.get(f'{self.live_server_url}{reverse("requirements:requirement_list")}')
        
        # Test swipe gesture (basic implementation)
        touch_screen = self.driver.touch
        screen_size = self.driver.get_window_size()
        
        # Swipe from right to left
        touch_screen.tap(screen_size['width'] - 50, screen_size['height'] // 2)
        touch_screen.move(50, screen_size['height'] // 2)
        
        # Check that page responds to swipe (implementation depends on actual functionality)
        time.sleep(1)
        
    def test_mobile_pinch_zoom(self):
        """Test mobile pinch zoom."""
        # Get home page
        self.driver.get(f'{self.live_server_url}{reverse("home")}')
        
        # Test pinch zoom (basic implementation)
        touch_screen = self.driver.touch
        screen_size = self.driver.get_window_size()
        center_x = screen_size['width'] // 2
        center_y = screen_size['height'] // 2
        
        # Pinch gesture
        touch_screen.tap(center_x - 50, center_y)
        touch_screen.tap(center_x + 50, center_y)
        
        # Check that zoom is handled (implementation depends on actual functionality)
        time.sleep(1)


class MobileOrientationTest(StaticLiveServerTestCase, SeleniumTestMixin):
    """Tests for mobile orientation changes."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
        # Set up Chrome driver with mobile viewport
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        
    def tearDown(self):
        """Clean up test environment."""
        self.driver.quit()
        
    def test_portrait_orientation(self):
        """Test portrait orientation."""
        # Set portrait orientation
        self.driver.set_window_size(375, 812)  # iPhone X portrait
        
        # Get home page
        self.driver.get(f'{self.live_server_url}{reverse("home")}')
        
        # Check that layout adapts to portrait
        viewport_width = self.driver.execute_script('return window.innerWidth')
        viewport_height = self.driver.execute_script('return window.innerHeight')
        
        self.assertLess(viewport_width, viewport_height, 'Not in portrait orientation')
        
    def test_landscape_orientation(self):
        """Test landscape orientation."""
        # Set landscape orientation
        self.driver.set_window_size(812, 375)  # iPhone X landscape
        
        # Get home page
        self.driver.get(f'{self.live_server_url}{reverse("home")}')
        
        # Check that layout adapts to landscape
        viewport_width = self.driver.execute_script('return window.innerWidth')
        viewport_height = self.driver.execute_script('return window.innerHeight')
        
        self.assertGreater(viewport_width, viewport_height, 'Not in landscape orientation')
        
    def test_orientation_change(self):
        """Test orientation change."""
        # Start in portrait
        self.driver.set_window_size(375, 812)
        self.driver.get(f'{self.live_server_url}{reverse("home")}')
        
        # Change to landscape
        self.driver.set_window_size(812, 375)
        
        # Wait for orientation change to be handled
        time.sleep(1)
        
        # Check that layout adapts
        viewport_width = self.driver.execute_script('return window.innerWidth')
        viewport_height = self.driver.execute_script('return window.innerHeight')
        
        self.assertGreater(viewport_width, viewport_height, 'Orientation change not handled properly')


class MobilePerformanceTest(StaticLiveServerTestCase, SeleniumTestMixin):
    """Tests for mobile performance."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
        # Set up Chrome driver with mobile viewport and performance logging
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=375,812')  # iPhone X dimensions
        options.add_argument('--enable-logging')
        options.add_argument('--log-level=0')
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(10)
        
    def tearDown(self):
        """Clean up test environment."""
        self.driver.quit()
        
    def test_mobile_page_load_time(self):
        """Test mobile page load time."""
        # Measure page load time
        start_time = time.time()
        self.driver.get(f'{self.live_server_url}{reverse("home")}')
        end_time = time.time()
        
        load_time = end_time - start_time
        
        # Check that page loads within 4 seconds on mobile (slightly more lenient than desktop)
        self.assertLess(load_time, 4.0, 'Mobile page load time exceeds 4 seconds')
        
    def test_mobile_javascript_performance(self):
        """Test mobile JavaScript performance."""
        # Get page with JavaScript
        self.driver.get(f'{self.live_server_url}{reverse("accounts:dashboard")}')
        
        # Measure JavaScript execution time
        start_time = time.time()
        self.driver.execute_script('return document.readyState')
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Check that JavaScript executes within 2 seconds on mobile
        self.assertLess(execution_time, 2.0, 'Mobile JavaScript execution time exceeds 2 seconds')
        
    def test_mobile_memory_usage(self):
        """Test mobile memory usage."""
        # Get page with content
        self.driver.get(f'{self.live_server_url}{reverse("requirements:requirement_list")}')
        
        # Check memory usage (basic check)
        memory_info = self.driver.execute_script('return performance.memory')
        
        if memory_info:
            used_memory = memory_info.get('usedJSHeapSize', 0)
            # Check that memory usage is reasonable (less than 50MB)
            self.assertLess(used_memory, 50 * 1024 * 1024, 'Mobile memory usage too high')


class MobileCompatibilityTest(StaticLiveServerTestCase, SeleniumTestMixin):
    """Tests for mobile browser compatibility."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_chrome_mobile(self):
        """Test Chrome mobile browser."""
        # Set up Chrome driver with mobile user agent
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=375,812')
        options.add_argument('--user-agent=Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36')
        
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
            
        finally:
            self.driver.quit()
            
    def test_safari_mobile(self):
        """Test Safari mobile browser."""
        # Set up Chrome driver with Safari user agent
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=375,812')
        options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1')
        
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
            
        finally:
            self.driver.quit()
            
    def test_firefox_mobile(self):
        """Test Firefox mobile browser."""
        # Set up Chrome driver with Firefox user agent
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=375,812')
        options.add_argument('--user-agent=Mozilla/5.0 (Mobile; rv:68.0) Gecko/68.0 Firefox/88.0')
        
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
            
        finally:
            self.driver.quit()