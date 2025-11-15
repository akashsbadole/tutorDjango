"""
Unit tests for requirements app models.
"""
import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from tests.factories import (
    UserFactory, TutorUserFactory, StudentUserFactory,
    RequirementFactory, ProposalFactory, SubjectFactory, CategoryFactory
)
from tests.utils.helpers import TestMixin, DateTimeTestMixin


class CategoryModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for Category model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_category_creation(self):
        """Test category model creation."""
        category = CategoryFactory.create()
        self.assertTrue(isinstance(category, CategoryFactory._meta.model))
        self.assertTrue(category.is_active)
        
    def test_category_string_representation(self):
        """Test category string representation."""
        category = CategoryFactory.create(name="Mathematics")
        self.assertEqual(str(category), "Mathematics")
        
    def test_category_name_unique(self):
        """Test category name uniqueness."""
        CategoryFactory.create(name="Mathematics")
        
        # Creating another category with same name should fail
        with self.assertRaises(Exception):  # Could be IntegrityError or ValidationError
            CategoryFactory.create(name="Mathematics")
            
    def test_category_description_max_length(self):
        """Test category description max length validation."""
        category = CategoryFactory.build()
        long_description = "x" * 201  # Exceeds max length
        category.description = long_description
        
        with self.assertRaises(ValidationError):
            category.full_clean()
            
    def test_category_active_default(self):
        """Test category is_active defaults to True."""
        category = CategoryFactory.build()
        self.assertTrue(category.is_active)


class SubjectModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for Subject model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.category = CategoryFactory.create()
        
    def test_subject_creation(self):
        """Test subject model creation."""
        subject = SubjectFactory.create(category=self.category)
        self.assertTrue(isinstance(subject, SubjectFactory._meta.model))
        self.assertEqual(subject.category, self.category)
        self.assertTrue(subject.is_active)
        
    def test_subject_string_representation(self):
        """Test subject string representation."""
        subject = SubjectFactory.create(name="Algebra", category=self.category)
        self.assertEqual(str(subject), "Algebra")
        
    def test_subject_category_relationship(self):
        """Test subject-category relationship."""
        subject = SubjectFactory.create(category=self.category)
        
        # Test reverse relationship
        self.assertIn(subject, self.category.subject_set.all())
        
    def test_subject_name_unique_per_category(self):
        """Test subject name uniqueness within category."""
        SubjectFactory.create(name="Algebra", category=self.category)
        
        # Creating another subject with same name in same category should fail
        with self.assertRaises(Exception):
            SubjectFactory.create(name="Algebra", category=self.category)
            
    def test_subject_description_max_length(self):
        """Test subject description max length validation."""
        subject = SubjectFactory.build(category=self.category)
        long_description = "x" * 201  # Exceeds max length
        subject.description = long_description
        
        with self.assertRaises(ValidationError):
            subject.full_clean()


class RequirementModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for Requirement model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.student = StudentUserFactory.create()
        self.subject = SubjectFactory.create()
        
    def test_requirement_creation(self):
        """Test requirement model creation."""
        requirement = RequirementFactory.create(
            student=self.student,
            subject=self.subject
        )
        self.assertTrue(isinstance(requirement, RequirementFactory._meta.model))
        self.assertEqual(requirement.student, self.student)
        self.assertEqual(requirement.subject, self.subject)
        self.assertEqual(requirement.status, 'OPEN')
        
    def test_requirement_string_representation(self):
        """Test requirement string representation."""
        requirement = RequirementFactory.create(
            title="Need Math Tutor",
            student=self.student,
            subject=self.subject
        )
        self.assertEqual(str(requirement), "Need Math Tutor")
        
    def test_requirement_budget_validation(self):
        """Test budget field validation."""
        requirement = RequirementFactory.build(
            student=self.student,
            subject=self.subject
        )
        
        # Test negative budget
        requirement.budget_min = Decimal('-10.00')
        with self.assertRaises(ValidationError):
            requirement.full_clean()
            
        # Test budget range
        requirement.budget_min = Decimal('100.00')
        requirement.budget_max = Decimal('50.00')  # Less than min
        with self.assertRaises(ValidationError):
            requirement.full_clean()
            
    def test_requirement_learning_level_choices(self):
        """Test learning level field choices."""
        requirement = RequirementFactory.build(
            student=self.student,
            subject=self.subject
        )
        
        valid_levels = ['BEGINNER', 'INTERMEDIATE', 'ADVANCED']
        for level in valid_levels:
            requirement.learning_level = level
            requirement.full_clean()  # Should not raise
            
        # Test invalid level
        requirement.learning_level = 'INVALID'
        with self.assertRaises(ValidationError):
            requirement.full_clean()
            
    def test_requirement_duration_validation(self):
        """Test duration field validation."""
        requirement = RequirementFactory.build(
            student=self.student,
            subject=self.subject
        )
        
        # Test negative duration
        requirement.duration_weeks = -1
        with self.assertRaises(ValidationError):
            requirement.full_clean()
            
        # Test zero duration
        requirement.duration_weeks = 0
        with self.assertRaises(ValidationError):
            requirement.full_clean()
            
    def test_requirement_hours_per_week_validation(self):
        """Test hours per week field validation."""
        requirement = RequirementFactory.build(
            student=self.student,
            subject=self.subject
        )
        
        # Test negative hours
        requirement.hours_per_week = -1
        with self.assertRaises(ValidationError):
            requirement.full_clean()
            
        # Test excessive hours
        requirement.hours_per_week = 169  # More than hours in a week
        with self.assertRaises(ValidationError):
            requirement.full_clean()
            
    def test_requirement_location_type_choices(self):
        """Test location type field choices."""
        requirement = RequirementFactory.build(
            student=self.student,
            subject=self.subject
        )
        
        valid_types = ['ONLINE', 'IN_PERSON', 'HYBRID']
        for location_type in valid_types:
            requirement.location_type = location_type
            requirement.full_clean()  # Should not raise
            
        # Test invalid type
        requirement.location_type = 'INVALID'
        with self.assertRaises(ValidationError):
            requirement.full_clean()
            
    def test_requirement_status_choices(self):
        """Test status field choices."""
        requirement = RequirementFactory.build(
            student=self.student,
            subject=self.subject
        )
        
        valid_statuses = ['OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']
        for status in valid_statuses:
            requirement.status = status
            requirement.full_clean()  # Should not raise
            
        # Test invalid status
        requirement.status = 'INVALID'
        with self.assertRaises(ValidationError):
            requirement.full_clean()
            
    def test_requirement_student_relationship(self):
        """Test requirement-student relationship."""
        requirement = RequirementFactory.create(student=self.student)
        
        # Test reverse relationship
        self.assertIn(requirement, self.student.requirements.all())
        
    def test_requirement_subject_relationship(self):
        """Test requirement-subject relationship."""
        requirement = RequirementFactory.create(subject=self.subject)
        
        # Test reverse relationship
        self.assertIn(requirement, self.subject.requirements.all())


class ProposalModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for Proposal model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.requirement = RequirementFactory.create()
        self.tutor = TutorUserFactory.create()
        
    def test_proposal_creation(self):
        """Test proposal model creation."""
        proposal = ProposalFactory.create(
            requirement=self.requirement,
            tutor=self.tutor
        )
        self.assertTrue(isinstance(proposal, ProposalFactory._meta.model))
        self.assertEqual(proposal.requirement, self.requirement)
        self.assertEqual(proposal.tutor, self.tutor)
        self.assertEqual(proposal.status, 'PENDING')
        
    def test_proposal_string_representation(self):
        """Test proposal string representation."""
        proposal = ProposalFactory.create(
            requirement=self.requirement,
            tutor=self.tutor
        )
        expected = f"Proposal by {self.tutor.username} for {self.requirement.title}"
        self.assertEqual(str(proposal), expected)
        
    def test_proposal_unique_requirement_tutor(self):
        """Test unique constraint on requirement-tutor combination."""
        ProposalFactory.create(
            requirement=self.requirement,
            tutor=self.tutor
        )
        
        # Creating another proposal for same requirement-tutor should fail
        with self.assertRaises(Exception):
            ProposalFactory.create(
                requirement=self.requirement,
                tutor=self.tutor
            )
            
    def test_proposal_hourly_rate_validation(self):
        """Test hourly rate field validation."""
        proposal = ProposalFactory.build(
            requirement=self.requirement,
            tutor=self.tutor
        )
        
        # Test negative rate
        proposal.hourly_rate = Decimal('-10.00')
        with self.assertRaises(ValidationError):
            proposal.full_clean()
            
        # Test zero rate
        proposal.hourly_rate = Decimal('0.00')
        with self.assertRaises(ValidationError):
            proposal.full_clean()
            
    def test_proposal_estimated_hours_validation(self):
        """Test estimated hours field validation."""
        proposal = ProposalFactory.build(
            requirement=self.requirement,
            tutor=self.tutor
        )
        
        # Test negative hours
        proposal.estimated_hours = -1
        with self.assertRaises(ValidationError):
            proposal.full_clean()
            
        # Test zero hours
        proposal.estimated_hours = 0
        with self.assertRaises(ValidationError):
            proposal.full_clean()
            
    def test_proposal_status_choices(self):
        """Test status field choices."""
        proposal = ProposalFactory.build(
            requirement=self.requirement,
            tutor=self.tutor
        )
        
        valid_statuses = ['PENDING', 'ACCEPTED', 'REJECTED', 'WITHDRAWN']
        for status in valid_statuses:
            proposal.status = status
            proposal.full_clean()  # Should not raise
            
        # Test invalid status
        proposal.status = 'INVALID'
        with self.assertRaises(ValidationError):
            proposal.full_clean()
            
    def test_proposal_requirement_relationship(self):
        """Test proposal-requirement relationship."""
        proposal = ProposalFactory.create(requirement=self.requirement)
        
        # Test reverse relationship
        self.assertIn(proposal, self.requirement.proposals.all())
        
    def test_proposal_tutor_relationship(self):
        """Test proposal-tutor relationship."""
        proposal = ProposalFactory.create(tutor=self.tutor)
        
        # Test reverse relationship
        self.assertIn(proposal, self.tutor.proposals.all())


class RequirementQuerySetTest(TestCase, TestMixin):
    """Test cases for Requirement model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.student = StudentUserFactory.create()
        
    def test_open_requirements_queryset(self):
        """Test open_requirements queryset method."""
        # Create requirements with different statuses
        open_req = RequirementFactory.create(
            student=self.student,
            status='OPEN'
        )
        closed_req = RequirementFactory.create(
            student=self.student,
            status='COMPLETED'
        )
        
        open_requirements = Requirement.objects.open()
        self.assertEqual(open_requirements.count(), 1)
        self.assertIn(open_req, open_requirements)
        self.assertNotIn(closed_req, open_requirements)
        
    def test_by_subject_queryset(self):
        """Test by_subject queryset method."""
        subject1 = SubjectFactory.create()
        subject2 = SubjectFactory.create()
        
        req1 = RequirementFactory.create(
            student=self.student,
            subject=subject1
        )
        req2 = RequirementFactory.create(
            student=self.student,
            subject=subject2
        )
        
        # Test filtering by subject1
        subject1_requirements = Requirement.objects.by_subject(subject1.id)
        self.assertEqual(subject1_requirements.count(), 1)
        self.assertIn(req1, subject1_requirements)
        
    def test_by_budget_range_queryset(self):
        """Test by_budget_range queryset method."""
        # Create requirements with different budgets
        low_budget = RequirementFactory.create(
            student=self.student,
            budget_min=10,
            budget_max=50
        )
        high_budget = RequirementFactory.create(
            student=self.student,
            budget_min=100,
            budget_max=200
        )
        
        # Test filtering by budget range
        mid_range_requirements = Requirement.objects.by_budget_range(25, 75)
        self.assertEqual(mid_range_requirements.count(), 1)
        self.assertIn(low_budget, mid_range_requirements)
        self.assertNotIn(high_budget, mid_range_requirements)


class ProposalQuerySetTest(TestCase, TestMixin):
    """Test cases for Proposal model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.tutor = TutorUserFactory.create()
        self.requirement = RequirementFactory.create()
        
    def test_pending_proposals_queryset(self):
        """Test pending_proposals queryset method."""
        # Create proposals with different statuses
        pending = ProposalFactory.create(
            requirement=self.requirement,
            tutor=self.tutor,
            status='PENDING'
        )
        accepted = ProposalFactory.create(
            requirement=self.requirement,
            tutor=self.tutor,
            status='ACCEPTED'
        )
        
        pending_proposals = Proposal.objects.pending()
        self.assertEqual(pending_proposals.count(), 1)
        self.assertIn(pending, pending_proposals)
        self.assertNotIn(accepted, pending_proposals)
        
    def test_by_tutor_queryset(self):
        """Test by_tutor queryset method."""
        tutor1 = TutorUserFactory.create()
        tutor2 = TutorUserFactory.create()
        
        prop1 = ProposalFactory.create(
            requirement=self.requirement,
            tutor=tutor1
        )
        prop2 = ProposalFactory.create(
            requirement=self.requirement,
            tutor=tutor2
        )
        
        # Test filtering by tutor1
        tutor1_proposals = Proposal.objects.by_tutor(tutor1.id)
        self.assertEqual(tutor1_proposals.count(), 1)
        self.assertIn(prop1, tutor1_proposals)
        
    def test_by_requirement_queryset(self):
        """Test by_requirement queryset method."""
        req1 = RequirementFactory.create()
        req2 = RequirementFactory.create()
        
        prop1 = ProposalFactory.create(
            requirement=req1,
            tutor=self.tutor
        )
        prop2 = ProposalFactory.create(
            requirement=req2,
            tutor=self.tutor
        )
        
        # Test filtering by req1
        req1_proposals = Proposal.objects.by_requirement(req1.id)
        self.assertEqual(req1_proposals.count(), 1)
        self.assertIn(prop1, req1_proposals)


class RequirementSignalTest(TestCase, TestMixin):
    """Test cases for Requirement model signals."""
    
    def test_requirement_created_signal(self):
        """Test requirement creation signal."""
        # This would test that requirement creation triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_requirement_status_change_signal(self):
        """Test requirement status change signal."""
        # This would test that status changes trigger
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic


class ProposalSignalTest(TestCase, TestMixin):
    """Test cases for Proposal model signals."""
    
    def test_proposal_created_signal(self):
        """Test proposal creation signal."""
        # This would test that proposal creation triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_proposal_status_change_signal(self):
        """Test proposal status change signal."""
        # This would test that status changes trigger
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic