"""
Unit tests for requirements app views and business logic.
"""
import pytest
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.messages import get_messages
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from unittest.mock import patch, MagicMock

from requirements.views import (
    RequirementListView, RequirementDetailView, RequirementCreateView, RequirementUpdateView,
    RequirementDeleteView, ProposalListView, ProposalDetailView, ProposalCreateView,
    ProposalUpdateView, ProposalDeleteView, AwardView, SessionCreateView, SessionUpdateView
)
from tests.factories import (
    UserFactory, TutorProfileFactory, StudentProfileFactory, CategoryFactory,
    SubjectFactory, RequirementFactory, ProposalFactory, AwardFactory, SessionFactory
)
from tests.utils.helpers import TestMixin, ViewTestMixin


class RequirementListViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for RequirementListView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        
    def test_requirement_list_view_get(self):
        """Test RequirementListView GET request."""
        # Create requirements
        RequirementFactory.create_batch(5)
        
        request = self.factory.get(reverse('requirements:requirement_list'))
        request.user = self.tutor_user
        
        response = RequirementListView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/requirement_list.html')
        self.assertEqual(len(response.context['requirements']), 5)
        
    def test_requirement_list_view_filtering(self):
        """Test RequirementListView with filtering."""
        # Create requirements with different subjects
        math_subject = SubjectFactory.create(name='Mathematics')
        science_subject = SubjectFactory.create(name='Science')
        
        math_requirement = RequirementFactory.create(subject=math_subject)
        science_requirement = RequirementFactory.create(subject=science_subject)
        
        # Test filtering by subject
        request = self.factory.get(
            reverse('requirements:requirement_list'),
            {'subject': math_subject.id}
        )
        request.user = self.tutor_user
        
        response = RequirementListView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['requirements']), 1)
        self.assertEqual(response.context['requirements'][0], math_requirement)
        
    def test_requirement_list_view_search(self):
        """Test RequirementListView with search."""
        # Create requirements
        python_requirement = RequirementFactory.create(title='Python Programming Tutor')
        math_requirement = RequirementFactory.create(title='Mathematics Tutor')
        
        # Test search
        request = self.factory.get(
            reverse('requirements:requirement_list'),
            {'q': 'Python'}
        )
        request.user = self.tutor_user
        
        response = RequirementListView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['requirements']), 1)
        self.assertEqual(response.context['requirements'][0], python_requirement)
        
    def test_requirement_list_view_pagination(self):
        """Test RequirementListView pagination."""
        # Create more requirements than page size
        RequirementFactory.create_batch(25)
        
        request = self.factory.get(reverse('requirements:requirement_list'))
        request.user = self.tutor_user
        
        response = RequirementListView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(response.context['requirements'], 'object_list'))
        self.assertTrue(hasattr(response.context['requirements'], 'paginator'))


class RequirementDetailViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for RequirementDetailView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        
    def test_requirement_detail_view_get(self):
        """Test RequirementDetailView GET request."""
        request = self.factory.get(
            reverse('requirements:requirement_detail', kwargs={'pk': self.requirement.pk})
        )
        request.user = self.tutor_user
        
        response = RequirementDetailView.as_view()(request, pk=self.requirement.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/requirement_detail.html')
        self.assertEqual(response.context['requirement'], self.requirement)
        
    def test_requirement_detail_view_nonexistent(self):
        """Test RequirementDetailView with nonexistent requirement."""
        request = self.factory.get(
            reverse('requirements:requirement_detail', kwargs={'pk': 999})
        )
        request.user = self.tutor_user
        
        response = RequirementDetailView.as_view()(request, pk=999)
        
        self.assertEqual(response.status_code, 404)
        
    def test_requirement_detail_view_proposals(self):
        """Test RequirementDetailView includes proposals."""
        # Create proposals
        ProposalFactory.create_batch(3, requirement=self.requirement)
        
        request = self.factory.get(
            reverse('requirements:requirement_detail', kwargs={'pk': self.requirement.pk})
        )
        request.user = self.tutor_user
        
        response = RequirementDetailView.as_view()(request, pk=self.requirement.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['proposals']), 3)


class RequirementCreateViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for RequirementCreateView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        
    def test_requirement_create_view_get(self):
        """Test RequirementCreateView GET request."""
        request = self.factory.get(reverse('requirements:requirement_create'))
        request.user = self.student_user
        
        response = RequirementCreateView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/requirement_form.html')
        
    def test_requirement_create_view_post_valid_data(self):
        """Test RequirementCreateView POST request with valid data."""
        category = CategoryFactory.create()
        subject = SubjectFactory.create(category=category)
        
        data = {
            'title': 'Python Programming Tutor',
            'description': 'Need help with Python programming',
            'category': category.id,
            'subject': subject.id,
            'budget': 50.00,
            'duration_weeks': 4,
            'hours_per_week': 2,
            'location': 'Online',
            'requirements': 'Basic Python knowledge'
        }
        
        request = self.factory.post(reverse('requirements:requirement_create'), data=data)
        request.user = self.student_user
        
        with patch('requirements.views.messages.success') as mock_success:
            response = RequirementCreateView.as_view()(request)
            
            # Check that requirement was created
            self.assertTrue(Requirement.objects.filter(title='Python Programming Tutor').exists())
            
            # Check that success message was called
            mock_success.assert_called_once()
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            
    def test_requirement_create_view_post_invalid_data(self):
        """Test RequirementCreateView POST request with invalid data."""
        data = {
            'title': '',  # Empty title
            'description': 'Need help with Python programming',
            'category': '',  # Empty category
            'subject': '',  # Empty subject
            'budget': 50.00,
            'duration_weeks': 4,
            'hours_per_week': 2,
            'location': 'Online',
            'requirements': 'Basic Python knowledge'
        }
        
        request = self.factory.post(reverse('requirements:requirement_create'), data=data)
        request.user = self.student_user
        
        response = RequirementCreateView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'title', 'This field is required.')
        self.assertFormError(response, 'form', 'category', 'This field is required.')
        self.assertFormError(response, 'form', 'subject', 'This field is required.')
        
    def test_requirement_create_view_tutor_access_denied(self):
        """Test RequirementCreateView denies access to tutors."""
        request = self.factory.get(reverse('requirements:requirement_create'))
        request.user = self.tutor_user
        
        response = RequirementCreateView.as_view()(request)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)


class RequirementUpdateViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for RequirementUpdateView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.other_student = UserFactory.create(user_type='STUDENT')
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        
    def test_requirement_update_view_get(self):
        """Test RequirementUpdateView GET request."""
        request = self.factory.get(
            reverse('requirements:requirement_update', kwargs={'pk': self.requirement.pk})
        )
        request.user = self.student_user
        
        response = RequirementUpdateView.as_view()(request, pk=self.requirement.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/requirement_form.html')
        self.assertEqual(response.context['form'].instance, self.requirement)
        
    def test_requirement_update_view_post_valid_data(self):
        """Test RequirementUpdateView POST request with valid data."""
        data = {
            'title': 'Updated Python Programming Tutor',
            'description': 'Need help with advanced Python programming',
            'category': self.requirement.category.id,
            'subject': self.requirement.subject.id,
            'budget': 75.00,
            'duration_weeks': 6,
            'hours_per_week': 3,
            'location': 'Online',
            'requirements': 'Advanced Python knowledge'
        }
        
        request = self.factory.post(
            reverse('requirements:requirement_update', kwargs={'pk': self.requirement.pk}),
            data=data
        )
        request.user = self.student_user
        
        with patch('requirements.views.messages.success') as mock_success:
            response = RequirementUpdateView.as_view()(request, pk=self.requirement.pk)
            
            # Check that requirement was updated
            self.requirement.refresh_from_db()
            self.assertEqual(self.requirement.title, 'Updated Python Programming Tutor')
            self.assertEqual(self.requirement.budget, 75.00)
            
            # Check that success message was called
            mock_success.assert_called_once()
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            
    def test_requirement_update_view_other_user_denied(self):
        """Test RequirementUpdateView denies access to other users."""
        request = self.factory.get(
            reverse('requirements:requirement_update', kwargs={'pk': self.requirement.pk})
        )
        request.user = self.other_student
        
        response = RequirementUpdateView.as_view()(request, pk=self.requirement.pk)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)


class RequirementDeleteViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for RequirementDeleteView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.other_student = UserFactory.create(user_type='STUDENT')
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        
    def test_requirement_delete_view_get(self):
        """Test RequirementDeleteView GET request."""
        request = self.factory.get(
            reverse('requirements:requirement_delete', kwargs={'pk': self.requirement.pk})
        )
        request.user = self.student_user
        
        response = RequirementDeleteView.as_view()(request, pk=self.requirement.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/requirement_confirm_delete.html')
        self.assertEqual(response.context['requirement'], self.requirement)
        
    def test_requirement_delete_view_post(self):
        """Test RequirementDeleteView POST request."""
        request = self.factory.post(
            reverse('requirements:requirement_delete', kwargs={'pk': self.requirement.pk})
        )
        request.user = self.student_user
        
        with patch('requirements.views.messages.success') as mock_success:
            response = RequirementDeleteView.as_view()(request, pk=self.requirement.pk)
            
            # Check that requirement was deleted
            self.assertFalse(Requirement.objects.filter(pk=self.requirement.pk).exists())
            
            # Check that success message was called
            mock_success.assert_called_once()
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            
    def test_requirement_delete_view_other_user_denied(self):
        """Test RequirementDeleteView denies access to other users."""
        request = self.factory.get(
            reverse('requirements:requirement_delete', kwargs={'pk': self.requirement.pk})
        )
        request.user = self.other_student
        
        response = RequirementDeleteView.as_view()(request, pk=self.requirement.pk)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)


class ProposalListViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for ProposalListView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        
    def test_proposal_list_view_get(self):
        """Test ProposalListView GET request."""
        # Create proposals
        ProposalFactory.create_batch(5, requirement=self.requirement)
        
        request = self.factory.get(
            reverse('requirements:proposal_list', kwargs={'requirement_pk': self.requirement.pk})
        )
        request.user = self.student_user
        
        response = ProposalListView.as_view()(request, requirement_pk=self.requirement.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/proposal_list.html')
        self.assertEqual(len(response.context['proposals']), 5)
        
    def test_proposal_list_view_other_user_denied(self):
        """Test ProposalListView denies access to other users."""
        other_student = UserFactory.create(user_type='STUDENT')
        
        request = self.factory.get(
            reverse('requirements:proposal_list', kwargs={'requirement_pk': self.requirement.pk})
        )
        request.user = other_student
        
        response = ProposalListView.as_view()(request, requirement_pk=self.requirement.pk)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)


class ProposalDetailViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for ProposalDetailView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        self.proposal = ProposalFactory.create(
            requirement=self.requirement,
            created_by=self.tutor_user
        )
        
    def test_proposal_detail_view_get_student(self):
        """Test ProposalDetailView GET request for student."""
        request = self.factory.get(
            reverse('requirements:proposal_detail', kwargs={'pk': self.proposal.pk})
        )
        request.user = self.student_user
        
        response = ProposalDetailView.as_view()(request, pk=self.proposal.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/proposal_detail.html')
        self.assertEqual(response.context['proposal'], self.proposal)
        
    def test_proposal_detail_view_get_tutor(self):
        """Test ProposalDetailView GET request for tutor."""
        request = self.factory.get(
            reverse('requirements:proposal_detail', kwargs={'pk': self.proposal.pk})
        )
        request.user = self.tutor_user
        
        response = ProposalDetailView.as_view()(request, pk=self.proposal.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/proposal_detail.html')
        self.assertEqual(response.context['proposal'], self.proposal)
        
    def test_proposal_detail_view_other_user_denied(self):
        """Test ProposalDetailView denies access to other users."""
        other_student = UserFactory.create(user_type='STUDENT')
        
        request = self.factory.get(
            reverse('requirements:proposal_detail', kwargs={'pk': self.proposal.pk})
        )
        request.user = other_student
        
        response = ProposalDetailView.as_view()(request, pk=self.proposal.pk)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)


class ProposalCreateViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for ProposalCreateView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        
    def test_proposal_create_view_get(self):
        """Test ProposalCreateView GET request."""
        request = self.factory.get(
            reverse('requirements:proposal_create', kwargs={'requirement_pk': self.requirement.pk})
        )
        request.user = self.tutor_user
        
        response = ProposalCreateView.as_view()(request, requirement_pk=self.requirement.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/proposal_form.html')
        
    def test_proposal_create_view_post_valid_data(self):
        """Test ProposalCreateView POST request with valid data."""
        data = {
            'title': 'Python Programming Proposal',
            'description': 'I can help you with Python programming',
            'hourly_rate': 25.00,
            'total_hours': 8,
            'timeline': '2 weeks',
            'approach': 'Hands-on coding exercises',
            'qualifications': '5 years Python experience'
        }
        
        request = self.factory.post(
            reverse('requirements:proposal_create', kwargs={'requirement_pk': self.requirement.pk}),
            data=data
        )
        request.user = self.tutor_user
        
        with patch('requirements.views.messages.success') as mock_success:
            response = ProposalCreateView.as_view()(request, requirement_pk=self.requirement.pk)
            
            # Check that proposal was created
            self.assertTrue(Proposal.objects.filter(title='Python Programming Proposal').exists())
            
            # Check that success message was called
            mock_success.assert_called_once()
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            
    def test_proposal_create_view_student_access_denied(self):
        """Test ProposalCreateView denies access to students."""
        request = self.factory.get(
            reverse('requirements:proposal_create', kwargs={'requirement_pk': self.requirement.pk})
        )
        request.user = self.student_user
        
        response = ProposalCreateView.as_view()(request, requirement_pk=self.requirement.pk)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)


class ProposalUpdateViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for ProposalUpdateView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.other_tutor = UserFactory.create(user_type='TUTOR')
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        self.proposal = ProposalFactory.create(
            requirement=self.requirement,
            created_by=self.tutor_user
        )
        
    def test_proposal_update_view_get(self):
        """Test ProposalUpdateView GET request."""
        request = self.factory.get(
            reverse('requirements:proposal_update', kwargs={'pk': self.proposal.pk})
        )
        request.user = self.tutor_user
        
        response = ProposalUpdateView.as_view()(request, pk=self.proposal.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/proposal_form.html')
        self.assertEqual(response.context['form'].instance, self.proposal)
        
    def test_proposal_update_view_post_valid_data(self):
        """Test ProposalUpdateView POST request with valid data."""
        data = {
            'title': 'Updated Python Programming Proposal',
            'description': 'I can help you with advanced Python programming',
            'hourly_rate': 30.00,
            'total_hours': 10,
            'timeline': '3 weeks',
            'approach': 'Advanced coding exercises',
            'qualifications': '7 years Python experience'
        }
        
        request = self.factory.post(
            reverse('requirements:proposal_update', kwargs={'pk': self.proposal.pk}),
            data=data
        )
        request.user = self.tutor_user
        
        with patch('requirements.views.messages.success') as mock_success:
            response = ProposalUpdateView.as_view()(request, pk=self.proposal.pk)
            
            # Check that proposal was updated
            self.proposal.refresh_from_db()
            self.assertEqual(self.proposal.title, 'Updated Python Programming Proposal')
            self.assertEqual(self.proposal.hourly_rate, 30.00)
            
            # Check that success message was called
            mock_success.assert_called_once()
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            
    def test_proposal_update_view_other_user_denied(self):
        """Test ProposalUpdateView denies access to other users."""
        request = self.factory.get(
            reverse('requirements:proposal_update', kwargs={'pk': self.proposal.pk})
        )
        request.user = self.other_tutor
        
        response = ProposalUpdateView.as_view()(request, pk=self.proposal.pk)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)


class ProposalDeleteViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for ProposalDeleteView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.other_tutor = UserFactory.create(user_type='TUTOR')
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        self.proposal = ProposalFactory.create(
            requirement=self.requirement,
            created_by=self.tutor_user
        )
        
    def test_proposal_delete_view_get(self):
        """Test ProposalDeleteView GET request."""
        request = self.factory.get(
            reverse('requirements:proposal_delete', kwargs={'pk': self.proposal.pk})
        )
        request.user = self.tutor_user
        
        response = ProposalDeleteView.as_view()(request, pk=self.proposal.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/proposal_confirm_delete.html')
        self.assertEqual(response.context['proposal'], self.proposal)
        
    def test_proposal_delete_view_post(self):
        """Test ProposalDeleteView POST request."""
        request = self.factory.post(
            reverse('requirements:proposal_delete', kwargs={'pk': self.proposal.pk})
        )
        request.user = self.tutor_user
        
        with patch('requirements.views.messages.success') as mock_success:
            response = ProposalDeleteView.as_view()(request, pk=self.proposal.pk)
            
            # Check that proposal was deleted
            self.assertFalse(Proposal.objects.filter(pk=self.proposal.pk).exists())
            
            # Check that success message was called
            mock_success.assert_called_once()
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            
    def test_proposal_delete_view_other_user_denied(self):
        """Test ProposalDeleteView denies access to other users."""
        request = self.factory.get(
            reverse('requirements:proposal_delete', kwargs={'pk': self.proposal.pk})
        )
        request.user = self.other_tutor
        
        response = ProposalDeleteView.as_view()(request, pk=self.proposal.pk)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)


class AwardViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for AwardView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.other_student = UserFactory.create(user_type='STUDENT')
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        self.proposal = ProposalFactory.create(
            requirement=self.requirement,
            created_by=self.tutor_user
        )
        
    def test_award_view_get(self):
        """Test AwardView GET request."""
        request = self.factory.get(
            reverse('requirements:award', kwargs={'pk': self.proposal.pk})
        )
        request.user = self.student_user
        
        response = AwardView.as_view()(request, pk=self.proposal.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/award_form.html')
        self.assertEqual(response.context['proposal'], self.proposal)
        
    def test_award_view_post_valid_data(self):
        """Test AwardView POST request with valid data."""
        data = {
            'price': 200.00,
            'terms': 'Payment will be made upon completion'
        }
        
        request = self.factory.post(
            reverse('requirements:award', kwargs={'pk': self.proposal.pk}),
            data=data
        )
        request.user = self.student_user
        
        with patch('requirements.views.messages.success') as mock_success:
            response = AwardView.as_view()(request, pk=self.proposal.pk)
            
            # Check that award was created
            self.assertTrue(Award.objects.filter(proposal=self.proposal).exists())
            
            # Check that success message was called
            mock_success.assert_called_once()
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            
    def test_award_view_tutor_access_denied(self):
        """Test AwardView denies access to tutors."""
        request = self.factory.get(
            reverse('requirements:award', kwargs={'pk': self.proposal.pk})
        )
        request.user = self.tutor_user
        
        response = AwardView.as_view()(request, pk=self.proposal.pk)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)
        
    def test_award_view_other_student_denied(self):
        """Test AwardView denies access to other students."""
        request = self.factory.get(
            reverse('requirements:award', kwargs={'pk': self.proposal.pk})
        )
        request.user = self.other_student
        
        response = AwardView.as_view()(request, pk=self.proposal.pk)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)


class SessionCreateViewTest(TestCase, TestMixin, ViewTestMixin):
    """Test cases for SessionCreateView."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.factory = RequestFactory()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        self.requirement = RequirementFactory.create(created_by=self.student_user)
        self.proposal = ProposalFactory.create(
            requirement=self.requirement,
            created_by=self.tutor_user
        )
        self.award = AwardFactory.create(proposal=self.proposal)
        
    def test_session_create_view_get(self):
        """Test SessionCreateView GET request."""
        request = self.factory.get(
            reverse('requirements:session_create', kwargs={'award_pk': self.award.pk})
        )
        request.user = self.tutor_user
        
        response = SessionCreateView.as_view()(request, award_pk=self.award.pk)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirements/session_form.html')
        
    def test_session_create_view_post_valid_data(self):
        """Test SessionCreateView POST request with valid data."""
        data = {
            'title': 'Python Programming Session 1',
            'description': 'Introduction to Python basics',
            'scheduled_at': '2023-12-01T10:00:00Z',
            'duration_minutes': 60,
            'location': 'Online'
        }
        
        request = self.factory.post(
            reverse('requirements:session_create', kwargs={'award_pk': self.award.pk}),
            data=data
        )
        request.user = self.tutor_user
        
        with patch('requirements.views.messages.success') as mock_success:
            response = SessionCreateView.as_view()(request, award_pk=self.award.pk)
            
            # Check that session was created
            self.assertTrue(Session.objects.filter(title='Python Programming Session 1').exists())
            
            # Check that success message was called
            mock_success.assert_called_once()
            
            # Check redirect
            self.assertEqual(response.status_code, 302)
            
    def test_session_create_view_student_access_denied(self):
        """Test SessionCreateView denies access to students."""
        request = self.factory.get(
            reverse('requirements:session_create', kwargs={'award_pk': self.award.pk})
        )
        request.user = self.student_user
        
        response = SessionCreateView.as_view()(request, award_pk=self.award.pk)
        
        # Check redirect
        self.assertEqual(response.status_code, 302)


class RequirementsBusinessLogicTest(TestCase, TestMixin):
    """Test cases for requirements app business logic."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.student_user = UserFactory.create(user_type='STUDENT')
        self.tutor_user = UserFactory.create(user_type='TUTOR')
        
    def test_requirement_status_property(self):
        """Test Requirement status property."""
        # Test open requirement
        open_requirement = RequirementFactory.create()
        self.assertEqual(open_requirement.status, 'OPEN')
        
        # Test closed requirement
        closed_requirement = RequirementFactory.create(is_closed=True)
        self.assertEqual(closed_requirement.status, 'CLOSED')
        
    def test_requirement_proposal_count_property(self):
        """Test Requirement proposal_count property."""
        requirement = RequirementFactory.create()
        
        # Test with no proposals
        self.assertEqual(requirement.proposal_count, 0)
        
        # Create proposals
        ProposalFactory.create_batch(3, requirement=requirement)
        
        # Test with proposals
        self.assertEqual(requirement.proposal_count, 3)
        
    def test_requirement_has_proposal_from_tutor_method(self):
        """Test Requirement has_proposal_from_tutor method."""
        requirement = RequirementFactory.create()
        
        # Test with no proposals
        self.assertFalse(requirement.has_proposal_from_tutor(self.tutor_user))
        
        # Create proposal from tutor
        ProposalFactory.create(requirement=requirement, created_by=self.tutor_user)
        
        # Test with proposal from tutor
        self.assertTrue(requirement.has_proposal_from_tutor(self.tutor_user))
        
    def test_proposal_status_property(self):
        """Test Proposal status property."""
        requirement = RequirementFactory.create()
        
        # Test pending proposal
        pending_proposal = ProposalFactory.create(requirement=requirement)
        self.assertEqual(pending_proposal.status, 'PENDING')
        
        # Test accepted proposal
        accepted_proposal = ProposalFactory.create(requirement=requirement, is_accepted=True)
        self.assertEqual(accepted_proposal.status, 'ACCEPTED')
        
        # Test rejected proposal
        rejected_proposal = ProposalFactory.create(requirement=requirement, is_rejected=True)
        self.assertEqual(rejected_proposal.status, 'REJECTED')
        
    def test_proposal_total_price_property(self):
        """Test Proposal total_price property."""
        proposal = ProposalFactory.create(
            hourly_rate=25.00,
            total_hours=8
        )
        
        self.assertEqual(proposal.total_price, 200.00)
        
    def test_award_status_property(self):
        """Test Award status property."""
        proposal = ProposalFactory.create()
        
        # Test pending award
        pending_award = AwardFactory.create(proposal=proposal)
        self.assertEqual(pending_award.status, 'PENDING')
        
        # Test active award
        active_award = AwardFactory.create(proposal=proposal, is_active=True)
        self.assertEqual(active_award.status, 'ACTIVE')
        
        # Test completed award
        completed_award = AwardFactory.create(proposal=proposal, is_completed=True)
        self.assertEqual(completed_award.status, 'COMPLETED')
        
    def test_session_status_property(self):
        """Test Session status property."""
        award = AwardFactory.create()
        
        # Test scheduled session
        scheduled_session = SessionFactory.create(award=award)
        self.assertEqual(scheduled_session.status, 'SCHEDULED')
        
        # Test in-progress session
        in_progress_session = SessionFactory.create(award=award, is_in_progress=True)
        self.assertEqual(in_progress_session.status, 'IN_PROGRESS')
        
        # Test completed session
        completed_session = SessionFactory.create(award=award, is_completed=True)
        self.assertEqual(completed_session.status, 'COMPLETED')
        
    def test_session_duration_property(self):
        """Test Session duration property."""
        session = SessionFactory.create(duration_minutes=60)
        
        self.assertEqual(session.duration, "1 hour")
        
        # Test with different durations
        session_30_min = SessionFactory.create(duration_minutes=30)
        self.assertEqual(session_30_min.duration, "30 minutes")
        
        session_90_min = SessionFactory.create(duration_minutes=90)
        self.assertEqual(session_90_min.duration, "1 hour 30 minutes")