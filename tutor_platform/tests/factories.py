"""
Test factories for Django Tutor Platform.

This module contains factory classes for generating test data using factory_boy.
"""
import random
from datetime import datetime, timedelta
from decimal import Decimal
from factory import (
    Factory, SubFactory, LazyAttribute, LazyFunction, 
    Sequence, post_generation, RelatedFactory, Iterator
)
from factory.django import DjangoModelFactory
from faker import Faker

from django.contrib.auth import get_user_model
from django.utils import timezone

# Import models (these will need to be adjusted based on actual model names)
from accounts.models import User, TutorProfile, StudentProfile
from requirements.models import Requirement, Proposal, Subject, Category
from messaging.models import Message, Conversation, OnlineClass, ClassRecording
from notifications.models import Notification, NotificationPreference
from paymentsdetails.models import Payment, EscrowTransaction, CommissionRate
from paypal_integration.models import PayPalAccount, PayPalTransaction

User = get_user_model()
fake = Faker()


class UserFactory(DjangoModelFactory):
    """Factory for User model."""
    
    class Meta:
        model = User
    
    username = Sequence(lambda n: f"user{n}")
    email = LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = LazyAttribute(lambda _: fake.first_name())
    last_name = LazyAttribute(lambda _: fake.last_name())
    is_active = True
    is_staff = False
    is_superuser = False
    date_joined = LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 365)))
    last_login = LazyFunction(lambda: timezone.now() - timedelta(hours=random.randint(1, 24)))


class TutorUserFactory(UserFactory):
    """Factory for tutor users."""
    
    user_type = 'TUTOR'
    
    @post_generation
    def tutor_profile(self, create, extracted, **kwargs):
        """Create tutor profile for the user."""
        if create:
            return TutorProfileFactory.create(user=self, **kwargs)
        return TutorProfileFactory.build(user=self, **kwargs)


class StudentUserFactory(UserFactory):
    """Factory for student users."""
    
    user_type = 'STUDENT'
    
    @post_generation
    def student_profile(self, create, extracted, **kwargs):
        """Create student profile for the user."""
        if create:
            return StudentProfileFactory.create(user=self, **kwargs)
        return StudentProfileFactory.build(user=self, **kwargs)


class AdminUserFactory(UserFactory):
    """Factory for admin users."""
    
    is_staff = True
    is_superuser = True


class TutorProfileFactory(DjangoModelFactory):
    """Factory for TutorProfile model."""
    
    class Meta:
        model = TutorProfile
    
    user = SubFactory(TutorUserFactory)
    bio = LazyAttribute(lambda _: fake.text(max_nb_chars=500))
    professional_title = LazyAttribute(lambda _: fake.job())
    hourly_rate_min = LazyFunction(lambda: round(random.uniform(10, 50), 2))
    hourly_rate_max = LazyFunction(lambda: round(random.uniform(51, 100), 2))
    experience_years = LazyFunction(lambda: random.randint(1, 20))
    education = LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    is_verified = LazyFunction(lambda: random.choice([True, False]))
    verification_status = LazyFunction(lambda: random.choice(['PENDING', 'VERIFIED', 'REJECTED']))
    is_online = LazyFunction(lambda: random.choice([True, False]))


class StudentProfileFactory(DjangoModelFactory):
    """Factory for StudentProfile model."""
    
    class Meta:
        model = StudentProfile
    
    user = SubFactory(StudentUserFactory)
    bio = LazyAttribute(lambda _: fake.text(max_nb_chars=300))
    education_level = LazyFunction(lambda: random.choice(['HIGH_SCHOOL', 'BACHELOR', 'MASTER', 'PHD']))
    learning_goals = LazyAttribute(lambda _: fake.text(max_nb_chars=200))


class CategoryFactory(DjangoModelFactory):
    """Factory for Category model."""
    
    class Meta:
        model = Category
    
    name = Sequence(lambda n: f"Category {n}")
    description = LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    is_active = True


class SubjectFactory(DjangoModelFactory):
    """Factory for Subject model."""
    
    class Meta:
        model = Subject
    
    name = Sequence(lambda n: f"Subject {n}")
    description = LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    category = SubFactory(CategoryFactory)
    is_active = True


class RequirementFactory(DjangoModelFactory):
    """Factory for Requirement model."""
    
    class Meta:
        model = Requirement
    
    title = LazyAttribute(lambda _: fake.sentence(nb_words=6))
    description = LazyAttribute(lambda _: fake.text(max_nb_chars=1000))
    student = SubFactory(StudentUserFactory)
    subject = SubFactory(SubjectFactory)
    budget_min = LazyFunction(lambda: round(random.uniform(20, 100), 2))
    budget_max = LazyFunction(lambda: round(random.uniform(101, 500), 2))
    learning_level = LazyFunction(lambda: random.choice(['BEGINNER', 'INTERMEDIATE', 'ADVANCED']))
    duration_weeks = LazyFunction(lambda: random.randint(1, 52))
    hours_per_week = LazyFunction(lambda: random.randint(1, 40))
    location_type = LazyFunction(lambda: random.choice(['ONLINE', 'IN_PERSON', 'HYBRID']))
    status = 'OPEN'
    created_at = LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 30)))


class ProposalFactory(DjangoModelFactory):
    """Factory for Proposal model."""
    
    class Meta:
        model = Proposal
    
    requirement = SubFactory(RequirementFactory)
    tutor = SubFactory(TutorUserFactory)
    message = LazyAttribute(lambda _: fake.text(max_nb_chars=800))
    hourly_rate = LazyFunction(lambda: round(random.uniform(20, 200), 2))
    estimated_hours = LazyFunction(lambda: random.randint(1, 100))
    availability = LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    status = 'PENDING'
    created_at = LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 15)))


class ConversationFactory(DjangoModelFactory):
    """Factory for Conversation model."""
    
    class Meta:
        model = Conversation
    
    requirement = SubFactory(RequirementFactory)
    participants = RelatedFactory(ProposalFactory, 'requirement', tutor=SubFactory(TutorUserFactory))
    created_at = LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 30)))
    updated_at = LazyFunction(lambda: timezone.now() - timedelta(hours=random.randint(1, 24)))


class MessageFactory(DjangoModelFactory):
    """Factory for Message model."""
    
    class Meta:
        model = Message
    
    conversation = SubFactory(ConversationFactory)
    sender = SubFactory(UserFactory)
    content = LazyAttribute(lambda _: fake.text(max_nb_chars=500))
    is_read = LazyFunction(lambda: random.choice([True, False]))
    created_at = LazyFunction(lambda: timezone.now() - timedelta(hours=random.randint(1, 24)))


class OnlineClassFactory(DjangoModelFactory):
    """Factory for OnlineClass model."""
    
    class Meta:
        model = OnlineClass
    
    title = LazyAttribute(lambda _: fake.sentence(nb_words=4))
    description = LazyAttribute(lambda _: fake.text(max_nb_chars=500))
    host = SubFactory(TutorUserFactory)
    platform = LazyFunction(lambda: random.choice(['ZOOM', 'TEAMS', 'MEET', 'SKYPE']))
    scheduled_start = LazyFunction(lambda: timezone.now() + timedelta(hours=random.randint(1, 168)))
    scheduled_end = LazyFunction(lambda: timezone.now() + timedelta(hours=random.randint(2, 169)))
    meeting_url = LazyAttribute(lambda _: fake.url())
    meeting_id = LazyAttribute(lambda _: fake.uuid4())
    password = LazyAttribute(lambda _: fake.password(length=8))
    max_participants = LazyFunction(lambda: random.randint(1, 100))
    status = 'SCHEDULED'
    created_at = LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 7)))


class ClassRecordingFactory(DjangoModelFactory):
    """Factory for ClassRecording model."""
    
    class Meta:
        model = ClassRecording
    
    online_class = SubFactory(OnlineClassFactory)
    title = LazyAttribute(lambda _: fake.sentence(nb_words=4))
    description = LazyAttribute(lambda _: fake.text(max_nb_chars=300))
    file_url = LazyAttribute(lambda _: fake.url())
    file_size = LazyFunction(lambda: random.randint(1024, 1073741824))  # 1KB to 1GB
    duration_minutes = LazyFunction(lambda: random.randint(1, 480))  # 1 minute to 8 hours
    is_public = LazyFunction(lambda: random.choice([True, False]))
    view_count = LazyFunction(lambda: random.randint(0, 1000))
    created_at = LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 30)))


class NotificationFactory(DjangoModelFactory):
    """Factory for Notification model."""
    
    class Meta:
        model = Notification
    
    recipient = SubFactory(UserFactory)
    title = LazyAttribute(lambda _: fake.sentence(nb_words=4))
    message = LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    notification_type = LazyFunction(lambda: random.choice([
        'INFO', 'SUCCESS', 'WARNING', 'ERROR', 'PROPOSAL', 'MESSAGE', 'PAYMENT'
    ]))
    is_read = LazyFunction(lambda: random.choice([True, False]))
    created_at = LazyFunction(lambda: timezone.now() - timedelta(hours=random.randint(1, 24)))


class NotificationPreferenceFactory(DjangoModelFactory):
    """Factory for NotificationPreference model."""
    
    class Meta:
        model = NotificationPreference
    
    user = SubFactory(UserFactory)
    email_notifications = LazyFunction(lambda: random.choice([True, False]))
    push_notifications = LazyFunction(lambda: random.choice([True, False]))
    sms_notifications = False
    email_frequency = LazyFunction(lambda: random.choice(['IMMEDIATE', 'DAILY', 'WEEKLY']))
    notification_types = LazyFunction(lambda: random.choice(['ALL', 'IMPORTANT', 'NONE']))


class PaymentFactory(DjangoModelFactory):
    """Factory for Payment model."""
    
    class Meta:
        model = Payment
    
    payer = SubFactory(UserFactory)
    payee = SubFactory(UserFactory)
    amount = LazyFunction(lambda: round(random.uniform(10, 1000), 2))
    currency = 'USD'
    payment_method = LazyFunction(lambda: random.choice(['PAYPAL', 'STRIPE', 'BANK_TRANSFER']))
    status = LazyFunction(lambda: random.choice(['PENDING', 'COMPLETED', 'FAILED', 'REFUNDED']))
    description = LazyAttribute(lambda _: fake.text(max_nb_chars=200))
    transaction_id = LazyAttribute(lambda _: fake.uuid4())
    created_at = LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 30)))


class EscrowTransactionFactory(DjangoModelFactory):
    """Factory for EscrowTransaction model."""
    
    class Meta:
        model = EscrowTransaction
    
    payment = SubFactory(PaymentFactory)
    amount = LazyFunction(lambda: round(random.uniform(10, 1000), 2))
    transaction_type = LazyFunction(lambda: random.choice(['DEPOSIT', 'RELEASE', 'REFUND']))
    status = LazyFunction(lambda: random.choice(['PENDING', 'COMPLETED', 'FAILED']))
    created_at = LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 30)))


class CommissionRateFactory(DjangoModelFactory):
    """Factory for CommissionRate model."""
    
    class Meta:
        model = CommissionRate
    
    user_type = LazyFunction(lambda: random.choice(['TUTOR', 'STUDENT', 'PLATFORM']))
    rate_percentage = LazyFunction(lambda: round(random.uniform(1, 25), 2))
    is_active = True
    effective_from = LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 365)))


class PayPalAccountFactory(DjangoModelFactory):
    """Factory for PayPalAccount model."""
    
    class Meta:
        model = PayPalAccount
    
    user = SubFactory(UserFactory)
    paypal_email = LazyAttribute(lambda _: fake.email())
    paypal_user_id = LazyAttribute(lambda _: fake.uuid4())
    is_verified = LazyFunction(lambda: random.choice([True, False]))
    is_primary = True
    created_at = LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 365)))


class PayPalTransactionFactory(DjangoModelFactory):
    """Factory for PayPalTransaction model."""
    
    class Meta:
        model = PayPalTransaction
    
    paypal_account = SubFactory(PayPalAccountFactory)
    payment = SubFactory(PaymentFactory)
    paypal_transaction_id = LazyAttribute(lambda _: fake.uuid4())
    amount = LazyFunction(lambda: round(random.uniform(10, 1000), 2))
    currency = 'USD'
    status = LazyFunction(lambda: random.choice(['PENDING', 'COMPLETED', 'FAILED', 'REFUNDED']))
    transaction_type = LazyFunction(lambda: random.choice(['PAYMENT', 'REFUND', 'TRANSFER']))
    created_at = LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 30)))


# Utility functions for creating test data
def create_test_tutor(**kwargs):
    """Create a test tutor with profile."""
    return TutorUserFactory.create(**kwargs)


def create_test_student(**kwargs):
    """Create a test student with profile."""
    return StudentUserFactory.create(**kwargs)


def create_test_requirement(student=None, **kwargs):
    """Create a test requirement."""
    if student is None:
        student = StudentUserFactory()
    return RequirementFactory.create(student=student, **kwargs)


def create_test_proposal(requirement=None, tutor=None, **kwargs):
    """Create a test proposal."""
    if requirement is None:
        requirement = RequirementFactory()
    if tutor is None:
        tutor = TutorUserFactory()
    return ProposalFactory.create(requirement=requirement, tutor=tutor, **kwargs)


def create_test_conversation(requirement=None, **kwargs):
    """Create a test conversation."""
    if requirement is None:
        requirement = RequirementFactory()
    return ConversationFactory.create(requirement=requirement, **kwargs)


def create_test_message(conversation=None, sender=None, **kwargs):
    """Create a test message."""
    if conversation is None:
        conversation = ConversationFactory()
    if sender is None:
        sender = UserFactory()
    return MessageFactory.create(conversation=conversation, sender=sender, **kwargs)


def create_test_payment(payer=None, payee=None, **kwargs):
    """Create a test payment."""
    if payer is None:
        payer = UserFactory()
    if payee is None:
        payee = UserFactory()
    return PaymentFactory.create(payer=payer, payee=payee, **kwargs)