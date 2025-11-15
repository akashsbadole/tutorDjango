"""
Unit tests for accounts app models.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

from tests.factories import (
    UserFactory, TutorUserFactory, StudentUserFactory, 
    TutorProfileFactory, StudentProfileFactory
)
from tests.utils.helpers import TestMixin, DateTimeTestMixin

User = get_user_model()


class UserModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for User model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_user_creation(self):
        """Test user model creation."""
        user = UserFactory.create()
        self.assertTrue(isinstance(user, User))
        self.assertEqual(user.username, user.username)
        self.assertEqual(user.email, f"{user.username}@example.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        
    def test_user_string_representation(self):
        """Test user string representation."""
        user = UserFactory.create(first_name="John", last_name="Doe")
        self.assertEqual(str(user), "John Doe")
        
    def test_user_get_full_name(self):
        """Test user get_full_name method."""
        user = UserFactory.create(first_name="John", last_name="Doe")
        self.assertEqual(user.get_full_name(), "John Doe")
        
    def test_user_get_short_name(self):
        """Test user get_short_name method."""
        user = UserFactory.create(first_name="John", last_name="Doe")
        self.assertEqual(user.get_short_name(), "John")
        
    def test_user_email_normalization(self):
        """Test email normalization during user creation."""
        user = UserFactory.create(email="Test@Example.COM")
        self.assertEqual(user.email, "Test@example.com")
        
    def test_user_type_choices(self):
        """Test user type field choices."""
        tutor = TutorUserFactory.create()
        student = StudentUserFactory.create()
        
        self.assertEqual(tutor.user_type, 'TUTOR')
        self.assertEqual(student.user_type, 'STUDENT')
        
    def test_user_type_validation(self):
        """Test user type field validation."""
        with self.assertRaises(ValidationError):
            user = UserFactory.build(user_type='INVALID')
            user.full_clean()


class TutorProfileModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for TutorProfile model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.tutor = TutorUserFactory.create()
        
    def test_tutor_profile_creation(self):
        """Test tutor profile creation."""
        profile = TutorProfileFactory.create(user=self.tutor)
        self.assertTrue(isinstance(profile, type(self.tutor.tutorprofile)))
        self.assertEqual(profile.user, self.tutor)
        
    def test_tutor_profile_string_representation(self):
        """Test tutor profile string representation."""
        profile = self.tutor.tutorprofile
        expected = f"{self.tutor.username} - {profile.professional_title}"
        self.assertEqual(str(profile), expected)
        
    def test_tutor_profile_bio_max_length(self):
        """Test tutor profile bio max length validation."""
        profile = self.tutor.tutorprofile
        long_bio = "x" * 501  # Exceeds max length
        profile.bio = long_bio
        
        with self.assertRaises(ValidationError):
            profile.full_clean()
            
    def test_tutor_profile_hourly_rate_validation(self):
        """Test hourly rate validation."""
        profile = self.tutor.tutorprofile
        
        # Test minimum rate
        profile.hourly_rate_min = Decimal('0.00')
        with self.assertRaises(ValidationError):
            profile.full_clean()
            
        # Test rate range
        profile.hourly_rate_min = Decimal('50.00')
        profile.hourly_rate_max = Decimal('25.00')  # Less than min
        with self.assertRaises(ValidationError):
            profile.full_clean()
            
    def test_tutor_profile_experience_years_validation(self):
        """Test experience years validation."""
        profile = self.tutor.tutorprofile
        
        # Test negative years
        profile.experience_years = -1
        with self.assertRaises(ValidationError):
            profile.full_clean()
            
        # Test maximum years
        profile.experience_years = 101  # Exceeds reasonable max
        with self.assertRaises(ValidationError):
            profile.full_clean()
            
    def test_tutor_profile_verification_status_choices(self):
        """Test verification status field choices."""
        profile = self.tutor.tutorprofile
        
        valid_statuses = ['PENDING', 'VERIFIED', 'REJECTED']
        for status in valid_statuses:
            profile.verification_status = status
            profile.full_clean()  # Should not raise
            
        # Test invalid status
        profile.verification_status = 'INVALID'
        with self.assertRaises(ValidationError):
            profile.full_clean()
            
    def test_tutor_profile_is_verified_property(self):
        """Test is_verified property."""
        profile = self.tutor.tutorprofile
        
        # Test when verified
        profile.verification_status = 'VERIFIED'
        self.assertTrue(profile.is_verified)
        
        # Test when not verified
        profile.verification_status = 'PENDING'
        self.assertFalse(profile.is_verified)
        
    def test_tutor_profile_average_rating_method(self):
        """Test get_average_rating method."""
        profile = self.tutor.tutorprofile
        
        # Test with no ratings
        self.assertEqual(profile.get_average_rating(), 0.0)
        
        # Test with mock ratings (would need actual rating model)
        # This would be implemented when rating model is available


class StudentProfileModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for StudentProfile model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.student = StudentUserFactory.create()
        
    def test_student_profile_creation(self):
        """Test student profile creation."""
        profile = StudentProfileFactory.create(user=self.student)
        self.assertTrue(isinstance(profile, type(self.student.studentprofile)))
        self.assertEqual(profile.user, self.student)
        
    def test_student_profile_string_representation(self):
        """Test student profile string representation."""
        profile = self.student.studentprofile
        expected = f"{self.student.username} - Student"
        self.assertEqual(str(profile), expected)
        
    def test_student_profile_bio_max_length(self):
        """Test student profile bio max length validation."""
        profile = self.student.studentprofile
        long_bio = "x" * 301  # Exceeds max length
        profile.bio = long_bio
        
        with self.assertRaises(ValidationError):
            profile.full_clean()
            
    def test_student_profile_education_level_choices(self):
        """Test education level field choices."""
        profile = self.student.studentprofile
        
        valid_levels = ['HIGH_SCHOOL', 'BACHELOR', 'MASTER', 'PHD']
        for level in valid_levels:
            profile.education_level = level
            profile.full_clean()  # Should not raise
            
        # Test invalid level
        profile.education_level = 'INVALID'
        with self.assertRaises(ValidationError):
            profile.full_clean()
            
    def test_student_profile_learning_goals_max_length(self):
        """Test learning goals max length validation."""
        profile = self.student.studentprofile
        long_goals = "x" * 201  # Exceeds max length
        profile.learning_goals = long_goals
        
        with self.assertRaises(ValidationError):
            profile.full_clean()


class UserQuerySetTest(TestCase, TestMixin):
    """Test cases for User model custom querysets."""
    
    def test_tutors_queryset(self):
        """Test tutors queryset method."""
        # Create mixed users
        TutorUserFactory.create_batch(3)
        StudentUserFactory.create_batch(2)
        UserFactory.create_batch(1)  # Regular users
        
        tutors = User.objects.tutors()
        self.assertEqual(tutors.count(), 3)
        
        for tutor in tutors:
            self.assertEqual(tutor.user_type, 'TUTOR')
            
    def test_students_queryset(self):
        """Test students queryset method."""
        # Create mixed users
        TutorUserFactory.create_batch(2)
        StudentUserFactory.create_batch(3)
        UserFactory.create_batch(1)  # Regular users
        
        students = User.objects.students()
        self.assertEqual(students.count(), 3)
        
        for student in students:
            self.assertEqual(student.user_type, 'STUDENT')
            
    def test_verified_tutors_queryset(self):
        """Test verified_tutors queryset method."""
        # Create tutors with different verification statuses
        verified_tutor = TutorUserFactory.create()
        verified_tutor.tutorprofile.verification_status = 'VERIFIED'
        verified_tutor.tutorprofile.save()
        
        unverified_tutor = TutorUserFactory.create()
        unverified_tutor.tutorprofile.verification_status = 'PENDING'
        unverified_tutor.tutorprofile.save()
        
        verified_tutors = User.objects.verified_tutors()
        self.assertEqual(verified_tutors.count(), 1)
        self.assertEqual(verified_tutors.first(), verified_tutor)
        
    def test_active_users_queryset(self):
        """Test active_users queryset method."""
        # Create active and inactive users
        active_user = UserFactory.create(is_active=True)
        inactive_user = UserFactory.create(is_active=False)
        
        active_users = User.objects.active()
        self.assertEqual(active_users.count(), 1)
        self.assertEqual(active_users.first(), active_user)


class UserManagerTest(TestCase, TestMixin):
    """Test cases for User model custom manager."""
    
    def test_create_user_method(self):
        """Test custom create_user method."""
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User'
        }
        
        user = User.objects.create_user(**user_data)
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        
    def test_create_superuser_method(self):
        """Test custom create_superuser method."""
        user_data = {
            'username': 'admin',
            'email': 'admin@example.com',
            'password': 'adminpass123'
        }
        
        admin = User.objects.create_superuser(**user_data)
        
        self.assertEqual(admin.username, 'admin')
        self.assertEqual(admin.email, 'admin@example.com')
        self.assertTrue(admin.check_password('adminpass123'))
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        
    def test_create_tutor_method(self):
        """Test create_tutor method."""
        tutor_data = {
            'username': 'tutor',
            'email': 'tutor@example.com',
            'password': 'tutorpass123',
            'professional_title': 'Math Tutor'
        }
        
        tutor = User.objects.create_tutor(**tutor_data)
        
        self.assertEqual(tutor.user_type, 'TUTOR')
        self.assertTrue(hasattr(tutor, 'tutorprofile'))
        self.assertEqual(tutor.tutorprofile.professional_title, 'Math Tutor')
        
    def test_create_student_method(self):
        """Test create_student method."""
        student_data = {
            'username': 'student',
            'email': 'student@example.com',
            'password': 'studentpass123',
            'education_level': 'BACHELOR'
        }
        
        student = User.objects.create_student(**student_data)
        
        self.assertEqual(student.user_type, 'STUDENT')
        self.assertTrue(hasattr(student, 'studentprofile'))
        self.assertEqual(student.studentprofile.education_level, 'BACHELOR')


class UserProfileSignalTest(TestCase, TestMixin):
    """Test cases for user profile signals."""
    
    def test_profile_created_signal(self):
        """Test profile creation signal."""
        # This would test that profiles are automatically created
        # when users are created with specific user types
        pass  # Implementation depends on actual signal logic
        
    def test_profile_updated_signal(self):
        """Test profile update signal."""
        # This would test that profile updates trigger
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic