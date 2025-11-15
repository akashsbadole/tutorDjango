"""
Integration tests for user workflows.
"""
import pytest
from django.test import TestCase, LiveServerTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from unittest.mock import patch, MagicMock

from tests.factories import (
    UserFactory, TutorProfileFactory, StudentProfileFactory, CategoryFactory,
    SubjectFactory, RequirementFactory, ProposalFactory, PaymentFactory
)
from tests.utils.helpers import TestMixin, IntegrationTestMixin

User = get_user_model()


class UserRegistrationWorkflowTest(TestCase, IntegrationTestMixin):
    """Integration tests for user registration workflow."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_student_registration_workflow(self):
        """Test complete student registration workflow."""
        # Navigate to registration page
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        
        # Fill registration form
        data = {
            'username': 'teststudent',
            'email': 'student@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Student',
            'user_type': 'STUDENT'
        }
        
        # Submit form
        response = self.client.post(reverse('accounts:register'), data=data, follow=True)
        
        # Check redirect to profile
        self.assertRedirects(response, reverse('accounts:student_profile'))
        
        # Check user was created
        user = User.objects.get(username='teststudent')
        self.assertEqual(user.email, 'student@example.com')
        self.assertEqual(user.user_type, 'STUDENT')
        
        # Check student profile was created
        self.assertTrue(hasattr(user, 'student_profile'))
        
        # Check welcome email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Welcome', mail.outbox[0].subject)
        self.assertIn('student@example.com', mail.outbox[0].to)
        
    def test_tutor_registration_workflow(self):
        """Test complete tutor registration workflow."""
        # Navigate to registration page
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        
        # Fill registration form
        data = {
            'username': 'testtutor',
            'email': 'tutor@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Tutor',
            'user_type': 'TUTOR'
        }
        
        # Submit form
        response = self.client.post(reverse('accounts:register'), data=data, follow=True)
        
        # Check redirect to profile
        self.assertRedirects(response, reverse('accounts:tutor_profile'))
        
        # Check user was created
        user = User.objects.get(username='testtutor')
        self.assertEqual(user.email, 'tutor@example.com')
        self.assertEqual(user.user_type, 'TUTOR')
        
        # Check tutor profile was created
        self.assertTrue(hasattr(user, 'tutor_profile'))
        
        # Check welcome email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Welcome', mail.outbox[0].subject)
        self.assertIn('tutor@example.com', mail.outbox[0].to)
        
    def test_registration_with_existing_email(self):
        """Test registration with existing email fails."""
        # Create user with email
        existing_user = UserFactory.create(email='existing@example.com')
        
        # Try to register with same email
        data = {
            'username': 'newuser',
            'email': 'existing@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'New',
            'last_name': 'User',
            'user_type': 'STUDENT'
        }
        
        response = self.client.post(reverse('accounts:register'), data=data)
        
        # Check form error
        self.assertFormError(response, 'form', 'email', 'User with this Email already exists.')
        
        # Check no new user was created
        self.assertEqual(User.objects.filter(email='existing@example.com').count(), 1)


class UserAuthenticationWorkflowTest(TestCase, IntegrationTestMixin):
    """Integration tests for user authentication workflow."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        self.user.set_password('testpass123')
        self.user.save()
        
    def test_login_workflow(self):
        """Test complete login workflow."""
        # Navigate to login page
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        
        # Fill login form
        data = {
            'username': self.user.username,
            'password': 'testpass123'
        }
        
        # Submit form
        response = self.client.post(reverse('accounts:login'), data=data, follow=True)
        
        # Check redirect to profile
        self.assertRedirects(response, reverse('accounts:profile'))
        
        # Check user is authenticated
        self.assertTrue(response.context['user'].is_authenticated)
        
    def test_logout_workflow(self):
        """Test complete logout workflow."""
        # Login user
        self.client.login(username=self.user.username, password='testpass123')
        
        # Navigate to logout
        response = self.client.post(reverse('accounts:logout'), follow=True)
        
        # Check redirect to login
        self.assertRedirects(response, reverse('accounts:login'))
        
        # Check user is logged out
        self.assertFalse(response.context['user'].is_authenticated)
        
    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials fails."""
        # Navigate to login page
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        
        # Fill login form with invalid password
        data = {
            'username': self.user.username,
            'password': 'wrongpassword'
        }
        
        # Submit form
        response = self.client.post(reverse('accounts:login'), data=data)
        
        # Check form error
        self.assertFormError(response, 'form', None, 'Invalid username or password.')
        
        # Check user is not authenticated
        self.assertFalse(response.context['user'].is_authenticated)


class RequirementPostingWorkflowTest(TestCase, IntegrationTestMixin):
    """Integration tests for requirement posting workflow."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.category = CategoryFactory.create()
        self.subject = SubjectFactory.create(category=self.category)
        
    def test_requirement_posting_workflow(self):
        """Test complete requirement posting workflow."""
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Navigate to requirement creation page
        response = self.client.get(reverse('requirements:requirement_create'))
        self.assertEqual(response.status_code, 200)
        
        # Fill requirement form
        data = {
            'title': 'Python Programming Tutor',
            'description': 'Need help with Python programming',
            'category': self.category.id,
            'subject': self.subject.id,
            'budget': 50.00,
            'duration_weeks': 4,
            'hours_per_week': 2,
            'location': 'Online',
            'requirements': 'Basic Python knowledge'
        }
        
        # Submit form
        response = self.client.post(reverse('requirements:requirement_create'), data=data, follow=True)
        
        # Check redirect to requirement detail
        self.assertRedirects(response, reverse('requirements:requirement_detail', kwargs={'pk': 1}))
        
        # Check requirement was created
        requirement = Requirement.objects.get(title='Python Programming Tutor')
        self.assertEqual(requirement.created_by, self.student_user)
        self.assertEqual(requirement.subject, self.subject)
        self.assertEqual(requirement.budget, 50.00)
        
        # Check notification was sent to matching tutors
        # This would depend on the actual notification implementation
        pass
        
    def test_requirement_update_workflow(self):
        """Test requirement update workflow."""
        # Create requirement
        requirement = RequirementFactory.create(created_by=self.student_user)
        
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Navigate to requirement update page
        response = self.client.get(reverse('requirements:requirement_update', kwargs={'pk': requirement.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Fill updated form
        data = {
            'title': 'Updated Python Programming Tutor',
            'description': 'Need help with advanced Python programming',
            'category': requirement.category.id,
            'subject': requirement.subject.id,
            'budget': 75.00,
            'duration_weeks': 6,
            'hours_per_week': 3,
            'location': 'Online',
            'requirements': 'Advanced Python knowledge'
        }
        
        # Submit form
        response = self.client.post(
            reverse('requirements:requirement_update', kwargs={'pk': requirement.pk}),
            data=data, follow=True
        )
        
        # Check redirect to requirement detail
        self.assertRedirects(response, reverse('requirements:requirement_detail', kwargs={'pk': requirement.pk}))
        
        # Check requirement was updated
        requirement.refresh_from_db()
        self.assertEqual(requirement.title, 'Updated Python Programming Tutor')
        self.assertEqual(requirement.budget, 75.00)


class TutorProposalWorkflowTest(TestCase, IntegrationTestMixin):
    """Integration tests for tutor proposal workflow."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.tutor_profile = TutorProfileFactory.create(user=self.tutor_user)
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        
    def test_proposal_submission_workflow(self):
        """Test complete proposal submission workflow."""
        # Login as tutor
        self.client.login(username=self.tutor_user.username, password='testpass123')
        
        # Navigate to requirement detail page
        response = self.client.get(reverse('requirements:requirement_detail', kwargs={'pk': self.requirement.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Navigate to proposal creation page
        response = self.client.get(
            reverse('requirements:proposal_create', kwargs={'requirement_pk': self.requirement.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # Fill proposal form
        data = {
            'title': 'Python Programming Proposal',
            'description': 'I can help you with Python programming',
            'hourly_rate': 25.00,
            'total_hours': 8,
            'timeline': '2 weeks',
            'approach': 'Hands-on coding exercises',
            'qualifications': '5 years Python experience'
        }
        
        # Submit form
        response = self.client.post(
            reverse('requirements:proposal_create', kwargs={'requirement_pk': self.requirement.pk}),
            data=data, follow=True
        )
        
        # Check redirect to proposal detail
        self.assertRedirects(response, reverse('requirements:proposal_detail', kwargs={'pk': 1}))
        
        # Check proposal was created
        proposal = Proposal.objects.get(title='Python Programming Proposal')
        self.assertEqual(proposal.requirement, self.requirement)
        self.assertEqual(proposal.created_by, self.tutor_user)
        self.assertEqual(proposal.hourly_rate, 25.00)
        
        # Check notification was sent to student
        # This would depend on the actual notification implementation
        pass
        
    def test_proposal_update_workflow(self):
        """Test proposal update workflow."""
        # Create proposal
        proposal = ProposalFactory.create(
            requirement=self.requirement,
            created_by=self.tutor_user
        )
        
        # Login as tutor
        self.client.login(username=self.tutor_user.username, password='testpass123')
        
        # Navigate to proposal update page
        response = self.client.get(reverse('requirements:proposal_update', kwargs={'pk': proposal.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Fill updated form
        data = {
            'title': 'Updated Python Programming Proposal',
            'description': 'I can help you with advanced Python programming',
            'hourly_rate': 30.00,
            'total_hours': 10,
            'timeline': '3 weeks',
            'approach': 'Advanced coding exercises',
            'qualifications': '7 years Python experience'
        }
        
        # Submit form
        response = self.client.post(
            reverse('requirements:proposal_update', kwargs={'pk': proposal.pk}),
            data=data, follow=True
        )
        
        # Check redirect to proposal detail
        self.assertRedirects(response, reverse('requirements:proposal_detail', kwargs={'pk': proposal.pk}))
        
        # Check proposal was updated
        proposal.refresh_from_db()
        self.assertEqual(proposal.title, 'Updated Python Programming Proposal')
        self.assertEqual(proposal.hourly_rate, 30.00)


class ProposalAwardingWorkflowTest(TestCase, IntegrationTestMixin):
    """Integration tests for proposal awarding workflow."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.tutor_profile = TutorProfileFactory.create(user=self.tutor_user)
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        self.proposal = ProposalFactory.create(
            requirement=self.requirement,
            created_by=self.tutor_user
        )
        
    def test_proposal_awarding_workflow(self):
        """Test complete proposal awarding workflow."""
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Navigate to proposal detail page
        response = self.client.get(reverse('requirements:proposal_detail', kwargs={'pk': self.proposal.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Navigate to award page
        response = self.client.get(reverse('requirements:award', kwargs={'pk': self.proposal.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Fill award form
        data = {
            'price': 200.00,
            'terms': 'Payment will be made upon completion'
        }
        
        # Submit form
        response = self.client.post(
            reverse('requirements:award', kwargs={'pk': self.proposal.pk}),
            data=data, follow=True
        )
        
        # Check redirect to proposal detail
        self.assertRedirects(response, reverse('requirements:proposal_detail', kwargs={'pk': self.proposal.pk}))
        
        # Check award was created
        from requirements.models import Award  # Import here to avoid circular imports
        award = Award.objects.get(proposal=self.proposal)
        self.assertEqual(award.price, 200.00)
        self.assertEqual(award.terms, 'Payment will be made upon completion')
        
        # Check proposal was marked as accepted
        self.proposal.refresh_from_db()
        self.assertTrue(self.proposal.is_accepted)
        
        # Check requirement was marked as closed
        self.requirement.refresh_from_db()
        self.assertTrue(self.requirement.is_closed)
        
        # Check notification was sent to tutor
        # This would depend on the actual notification implementation
        pass


class PaymentProcessingWorkflowTest(TestCase, IntegrationTestMixin):
    """Integration tests for payment processing workflow."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.tutor_profile = TutorProfileFactory.create(user=self.tutor_user)
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        self.proposal = ProposalFactory.create(
            requirement=self.requirement,
            created_by=self.tutor_user
        )
        
        # Create award
        from requirements.models import Award  # Import here to avoid circular imports
        self.award = AwardFactory.create(
            proposal=self.proposal,
            price=200.00
        )
        
    @patch('paypal_integration.services.PayPalService.create_payment')
    def test_payment_creation_workflow(self, mock_create_payment):
        """Test complete payment creation workflow."""
        # Mock PayPal payment creation
        mock_create_payment.return_value = {
            'payment_id': 'PAY-12345',
            'approval_url': 'https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=EC-12345'
        }
        
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Navigate to payment creation
        response = self.client.get(
            reverse('paymentsdetails:payment_create', kwargs={'award_pk': self.award.pk})
        )
        self.assertEqual(response.status_code, 200)
        
        # Submit payment form
        data = {
            'payment_method': 'PAYPAL'
        }
        
        response = self.client.post(
            reverse('paymentsdetails:payment_create', kwargs={'award_pk': self.award.pk}),
            data=data, follow=True
        )
        
        # Check redirect to PayPal
        self.assertRedirects(response, 'https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_express-checkout&token=EC-12345')
        
        # Check payment was created
        from paymentsdetails.models import Payment  # Import here to avoid circular imports
        payment = Payment.objects.get(award=self.award)
        self.assertEqual(payment.amount, 200.00)
        self.assertEqual(payment.status, 'PENDING')
        self.assertEqual(payment.payment_method, 'PAYPAL')
        
    @patch('paypal_integration.services.PayPalService.execute_payment')
    def test_payment_completion_workflow(self, mock_execute_payment):
        """Test complete payment completion workflow."""
        # Create payment
        from paymentsdetails.models import Payment  # Import here to avoid circular imports
        payment = PaymentFactory.create(
            award=self.award,
            amount=200.00,
            status='PENDING',
            payment_method='PAYPAL',
            paypal_payment_id='PAY-12345'
        )
        
        # Mock PayPal payment execution
        mock_execute_payment.return_value = {
            'status': 'completed',
            'transaction_id': 'TXN-67890'
        }
        
        # Simulate PayPal callback
        response = self.client.get(
            reverse('paypal_integration:payment_success'),
            {'paymentId': 'PAY-12345', 'PayerID': 'PAYER-12345'}
        )
        
        # Check redirect to payment detail
        self.assertRedirects(response, reverse('paymentsdetails:payment_detail', kwargs={'pk': payment.pk}))
        
        # Check payment was completed
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'COMPLETED')
        self.assertEqual(payment.paypal_transaction_id, 'TXN-67890')
        
        # Check escrow was created
        from paymentsdetails.models import EscrowTransaction  # Import here to avoid circular imports
        escrow = EscrowTransaction.objects.get(payment=payment)
        self.assertEqual(escrow.amount, 200.00)
        self.assertEqual(escrow.status, 'HELD')


class MessagingWorkflowTest(TestCase, IntegrationTestMixin):
    """Integration tests for messaging workflow."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user1 = UserFactory.create()
        self.user2 = UserFactory.create()
        
    def test_conversation_creation_workflow(self):
        """Test complete conversation creation workflow."""
        # Login as user1
        self.client.login(username=self.user1.username, password='testpass123')
        
        # Navigate to conversation creation
        response = self.client.get(reverse('messaging:conversation_create'))
        self.assertEqual(response.status_code, 200)
        
        # Fill conversation form
        data = {
            'participants': [self.user2.id],
            'subject': 'Test Conversation'
        }
        
        # Submit form
        response = self.client.post(reverse('messaging:conversation_create'), data=data, follow=True)
        
        # Check redirect to conversation detail
        self.assertRedirects(response, reverse('messaging:conversation_detail', kwargs={'pk': 1}))
        
        # Check conversation was created
        from messaging.models import Conversation  # Import here to avoid circular imports
        conversation = Conversation.objects.get(subject='Test Conversation')
        self.assertEqual(conversation.participants.count(), 2)
        self.assertIn(self.user1, conversation.participants.all())
        self.assertIn(self.user2, conversation.participants.all())
        
    def test_message_sending_workflow(self):
        """Test complete message sending workflow."""
        # Create conversation
        from messaging.models import Conversation  # Import here to avoid circular imports
        conversation = ConversationFactory.create()
        conversation.participants.add(self.user1, self.user2)
        
        # Login as user1
        self.client.login(username=self.user1.username, password='testpass123')
        
        # Navigate to conversation detail
        response = self.client.get(reverse('messaging:conversation_detail', kwargs={'pk': conversation.pk}))
        self.assertEqual(response.status_code, 200)
        
        # Fill message form
        data = {
            'content': 'Hello, this is a test message'
        }
        
        # Submit form
        response = self.client.post(
            reverse('messaging:message_create', kwargs={'conversation_pk': conversation.pk}),
            data=data, follow=True
        )
        
        # Check redirect to conversation detail
        self.assertRedirects(response, reverse('messaging:conversation_detail', kwargs={'pk': conversation.pk}))
        
        # Check message was created
        from messaging.models import Message  # Import here to avoid circular imports
        message = Message.objects.get(content='Hello, this is a test message')
        self.assertEqual(message.conversation, conversation)
        self.assertEqual(message.sender, self.user1)
        
        # Check notification was sent to user2
        # This would depend on the actual notification implementation
        pass


class ProfileManagementWorkflowTest(TestCase, IntegrationTestMixin):
    """Integration tests for profile management workflow."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.tutor_profile = TutorProfileFactory.create(user=self.tutor_user)
        
    def test_student_profile_update_workflow(self):
        """Test complete student profile update workflow."""
        # Login as student
        self.client.login(username=self.student_user.username, password='testpass123')
        
        # Navigate to profile update
        response = self.client.get(reverse('accounts:student_profile_update'))
        self.assertEqual(response.status_code, 200)
        
        # Fill profile form
        data = {
            'education_level': 'GRADUATE',
            'subjects_of_interest': 'Python, Mathematics, Physics',
            'learning_goals': 'Learn Python programming',
            'bio': 'Motivated student'
        }
        
        # Submit form
        response = self.client.post(reverse('accounts:student_profile_update'), data=data, follow=True)
        
        # Check redirect to profile
        self.assertRedirects(response, reverse('accounts:student_profile'))
        
        # Check profile was updated
        from accounts.models import StudentProfile  # Import here to avoid circular imports
        profile = StudentProfile.objects.get(user=self.student_user)
        self.assertEqual(profile.education_level, 'GRADUATE')
        self.assertEqual(profile.subjects_of_interest, 'Python, Mathematics, Physics')
        self.assertEqual(profile.learning_goals, 'Learn Python programming')
        self.assertEqual(profile.bio, 'Motivated student')
        
    def test_tutor_profile_update_workflow(self):
        """Test complete tutor profile update workflow."""
        # Login as tutor
        self.client.login(username=self.tutor_user.username, password='testpass123')
        
        # Navigate to profile update
        response = self.client.get(reverse('accounts:tutor_profile_update'))
        self.assertEqual(response.status_code, 200)
        
        # Fill profile form
        data = {
            'hourly_rate': 50.00,
            'experience_years': 5,
            'education': 'Bachelor\'s in Computer Science',
            'subjects': 'Python, Django, JavaScript',
            'availability': 'Monday, Wednesday, Friday',
            'bio': 'Experienced tutor'
        }
        
        # Submit form
        response = self.client.post(reverse('accounts:tutor_profile_update'), data=data, follow=True)
        
        # Check redirect to profile
        self.assertRedirects(response, reverse('accounts:tutor_profile'))
        
        # Check profile was updated
        from accounts.models import TutorProfile  # Import here to avoid circular imports
        profile = TutorProfile.objects.get(user=self.tutor_user)
        self.assertEqual(profile.hourly_rate, 50.00)
        self.assertEqual(profile.experience_years, 5)
        self.assertEqual(profile.education, 'Bachelor\'s in Computer Science')
        self.assertEqual(profile.subjects, 'Python, Django, JavaScript')
        self.assertEqual(profile.availability, 'Monday, Wednesday, Friday')
        self.assertEqual(profile.bio, 'Experienced tutor')


class SearchWorkflowTest(TestCase, IntegrationTestMixin):
    """Integration tests for search workflow."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.category = CategoryFactory.create()
        self.subject = SubjectFactory.create(category=self.category)
        
        # Create requirements
        self.python_req = RequirementFactory.create(
            title='Python Programming Tutor',
            subject=self.subject
        )
        self.math_req = RequirementFactory.create(
            title='Mathematics Tutor',
            subject=self.subject
        )
        
    def test_requirement_search_workflow(self):
        """Test complete requirement search workflow."""
        # Navigate to search page
        response = self.client.get(reverse('search:search'))
        self.assertEqual(response.status_code, 200)
        
        # Search for 'Python'
        response = self.client.get(reverse('search:search'), {'q': 'Python'})
        self.assertEqual(response.status_code, 200)
        
        # Check search results
        self.assertContains(response, 'Python Programming Tutor')
        self.assertNotContains(response, 'Mathematics Tutor')
        
        # Click on result
        response = self.client.get(reverse('requirements:requirement_detail', kwargs={'pk': self.python_req.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python Programming Tutor')
        
    def test_requirement_filter_workflow(self):
        """Test complete requirement filter workflow."""
        # Navigate to search page
        response = self.client.get(reverse('search:search'))
        self.assertEqual(response.status_code, 200)
        
        # Filter by subject
        response = self.client.get(reverse('search:search'), {'subject': self.subject.id})
        self.assertEqual(response.status_code, 200)
        
        # Check filter results
        self.assertContains(response, 'Python Programming Tutor')
        self.assertContains(response, 'Mathematics Tutor')
        
    def test_requirement_sort_workflow(self):
        """Test complete requirement sort workflow."""
        # Navigate to search page
        response = self.client.get(reverse('search:search'))
        self.assertEqual(response.status_code, 200)
        
        # Sort by budget (low to high)
        response = self.client.get(reverse('search:search'), {'sort': 'budget_asc'})
        self.assertEqual(response.status_code, 200)
        
        # Check sort results (implementation depends on actual sorting logic)
        pass


class SeleniumUserWorkflowTest(LiveServerTestCase, IntegrationTestMixin):
    """Selenium tests for user workflows."""
    
    @classmethod
    def setUpClass(cls):
        """Set up Selenium WebDriver."""
        super().setUpClass()
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        cls.selenium = webdriver.Chrome(options=chrome_options)
        cls.selenium.implicitly_wait(10)
        
    @classmethod
    def tearDownClass(cls):
        """Tear down Selenium WebDriver."""
        cls.selenium.quit()
        super().tearDownClass()
        
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.student_user.set_password('testpass123')
        self.student_user.save()
        
    def test_selenium_login_workflow(self):
        """Test complete login workflow with Selenium."""
        # Navigate to login page
        self.selenium.get(f'{self.live_server_url}{reverse("accounts:login")}')
        
        # Fill login form
        username_input = self.selenium.find_element(By.NAME, 'username')
        password_input = self.selenium.find_element(By.NAME, 'password')
        username_input.send_keys(self.student_user.username)
        password_input.send_keys('testpass123')
        
        # Submit form
        submit_button = self.selenium.find_element(By.XPATH, '//button[@type="submit"]')
        submit_button.click()
        
        # Wait for redirect to profile
        WebDriverWait(self.selenium, 10).until(
            EC.url_contains(reverse('accounts:profile'))
        )
        
        # Check current URL
        current_url = self.selenium.current_url
        self.assertIn(reverse('accounts:profile'), current_url)
        
    def test_selenium_requirement_creation_workflow(self):
        """Test complete requirement creation workflow with Selenium."""
        # Login first
        self.selenium.get(f'{self.live_server_url}{reverse("accounts:login")}')
        username_input = self.selenium.find_element(By.NAME, 'username')
        password_input = self.selenium.find_element(By.NAME, 'password')
        username_input.send_keys(self.student_user.username)
        password_input.send_keys('testpass123')
        submit_button = self.selenium.find_element(By.XPATH, '//button[@type="submit"]')
        submit_button.click()
        
        # Wait for redirect to profile
        WebDriverWait(self.selenium, 10).until(
            EC.url_contains(reverse('accounts:profile'))
        )
        
        # Navigate to requirement creation
        self.selenium.get(f'{self.live_server_url}{reverse("requirements:requirement_create")}')
        
        # Fill requirement form
        title_input = self.selenium.find_element(By.NAME, 'title')
        description_input = self.selenium.find_element(By.NAME, 'description')
        budget_input = self.selenium.find_element(By.NAME, 'budget')
        
        title_input.send_keys('Python Programming Tutor')
        description_input.send_keys('Need help with Python programming')
        budget_input.send_keys('50.00')
        
        # Submit form
        submit_button = self.selenium.find_element(By.XPATH, '//button[@type="submit"]')
        submit_button.click()
        
        # Wait for redirect to requirement detail
        WebDriverWait(self.selenium, 10).until(
            EC.url_contains(reverse('requirements:requirement_detail', kwargs={'pk': 1}))
        )
        
        # Check current URL
        current_url = self.selenium.current_url
        self.assertIn(reverse('requirements:requirement_detail', kwargs={'pk': 1}), current_url)
        
        # Check requirement details
        title_element = self.selenium.find_element(By.XPATH, '//h1')
        self.assertEqual(title_element.text, 'Python Programming Tutor')