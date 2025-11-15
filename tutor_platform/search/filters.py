import django_filters
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta

from accounts.models import TutorProfile, Subject, TutorSubject
from requirements.models import Requirement
from paymentsdetails.models import Payment
from messaging.models import Message
from .models import SearchIndex

User = get_user_model()


class TutorFilterSet(django_filters.FilterSet):
    """Filter set for tutor searches"""
    
    # Basic filters
    username = django_filters.CharFilter(
        method='filter_username',
        label='Username'
    )
    
    name = django_filters.CharFilter(
        method='filter_name',
        label='Name'
    )
    
    bio = django_filters.CharFilter(
        field_name='tutorprofile__bio',
        lookup_expr='icontains',
        label='Bio'
    )
    
    # Subject filters
    subjects = django_filters.ModelMultipleChoiceFilter(
        field_name='tutorprofile__tutor_subjects__subject',
        queryset=Subject.objects.filter(is_active=True),
        label='Subjects'
    )
    
    proficiency_level = django_filters.ChoiceFilter(
        field_name='tutorprofile__tutor_subjects__proficiency_level',
        choices=TutorSubject.ProficiencyLevel.choices,
        label='Proficiency Level'
    )
    
    # Rate filters
    hourly_rate_min = django_filters.NumberFilter(
        method='filter_hourly_rate_min',
        label='Min Hourly Rate'
    )
    
    hourly_rate_max = django_filters.NumberFilter(
        method='filter_hourly_rate_max',
        label='Max Hourly Rate'
    )
    
    # Status filters
    availability_status = django_filters.ChoiceFilter(
        field_name='tutorprofile__availability_status',
        choices=TutorProfile.AvailabilityStatus.choices,
        label='Availability Status'
    )
    
    is_verified = django_filters.BooleanFilter(
        field_name='is_verified',
        label='Verified'
    )
    
    is_online = django_filters.BooleanFilter(
        field_name='is_online',
        label='Online Now'
    )
    
    is_featured = django_filters.BooleanFilter(
        field_name='tutorprofile__is_featured',
        label='Featured'
    )
    
    # Experience filters
    experience_years = django_filters.NumberFilter(
        field_name='tutorprofile__experience_years',
        lookup_expr='gte',
        label='Min Experience (Years)'
    )
    
    # Rating filter
    rating_min = django_filters.NumberFilter(
        method='filter_rating_min',
        label='Min Rating'
    )
    
    # Language filter
    languages = django_filters.CharFilter(
        field_name='tutorprofile__languages',
        lookup_expr='icontains',
        label='Languages'
    )
    
    # Date filters
    created_after = django_filters.DateFilter(
        field_name='date_joined',
        lookup_expr='gte',
        label='Joined After'
    )
    
    created_before = django_filters.DateFilter(
        field_name='date_joined',
        lookup_expr='lte',
        label='Joined Before'
    )
    
    # Ordering
    ordering = django_filters.OrderingFilter(
        fields=[
            'username', 'first_name', 'last_name',
            'tutorprofile__hourly_rate_min', 'tutorprofile__experience_years',
            'tutorprofile__availability_status', 'date_joined'
        ],
        label='Order by'
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'name', 'bio', 'subjects', 'proficiency_level',
            'hourly_rate_min', 'hourly_rate_max', 'availability_status',
            'is_verified', 'is_online', 'is_featured', 'experience_years',
            'rating_min', 'languages', 'created_after', 'created_before'
        ]
    
    def filter_username(self, queryset, name, value):
        """Filter by username"""
        if not value:
            return queryset
        return queryset.filter(username__icontains=value)
    
    def filter_name(self, queryset, name, value):
        """Filter by first name or last name"""
        if not value:
            return queryset
        return queryset.filter(
            Q(first_name__icontains=value) | Q(last_name__icontains=value)
        )
    
    def filter_hourly_rate_min(self, queryset, name, value):
        """Filter by minimum hourly rate"""
        if not value:
            return queryset
        return queryset.filter(
            Q(tutorprofile__hourly_rate_min__gte=value) |
            Q(tutorprofile__hourly_rate_max__gte=value)
        )
    
    def filter_hourly_rate_max(self, queryset, name, value):
        """Filter by maximum hourly rate"""
        if not value:
            return queryset
        return queryset.filter(
            Q(tutorprofile__hourly_rate_min__lte=value) |
            Q(tutorprofile__hourly_rate_max__lte=value)
        )
    
    def filter_rating_min(self, queryset, name, value):
        """Filter by minimum rating"""
        if not value:
            return queryset
        return queryset.annotate(
            avg_rating=Avg('tutorprofile__ratings__rating')
        ).filter(avg_rating__gte=value)


class RequirementFilterSet(django_filters.FilterSet):
    """Filter set for requirement searches"""
    
    # Basic filters
    title = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Title'
    )
    
    description = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Description'
    )
    
    # Subject and level filters
    subject = django_filters.ModelChoiceFilter(
        queryset=Subject.objects.filter(is_active=True),
        label='Subject'
    )
    
    learning_level = django_filters.ChoiceFilter(
        choices=Requirement._meta.get_field('learning_level').choices,
        label='Learning Level'
    )
    
    # Budget filters
    budget_min = django_filters.NumberFilter(
        method='filter_budget_min',
        label='Min Budget'
    )
    
    budget_max = django_filters.NumberFilter(
        method='filter_budget_max',
        label='Max Budget'
    )
    
    budget_type = django_filters.ChoiceFilter(
        choices=Requirement.BudgetType.choices,
        label='Budget Type'
    )
    
    # Status filters
    urgency_level = django_filters.ChoiceFilter(
        choices=Requirement.UrgencyLevel.choices,
        label='Urgency Level'
    )
    
    location_type = django_filters.ChoiceFilter(
        choices=Requirement.LocationType.choices,
        label='Location Type'
    )
    
    is_featured = django_filters.BooleanFilter(
        field_name='is_featured',
        label='Featured'
    )
    
    # Date filters
    deadline_after = django_filters.DateFilter(
        field_name='deadline',
        lookup_expr='gte',
        label='Deadline After'
    )
    
    deadline_before = django_filters.DateFilter(
        field_name='deadline',
        lookup_expr='lte',
        label='Deadline Before'
    )
    
    created_after = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Created After'
    )
    
    created_before = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Created Before'
    )
    
    # Student filter
    student = django_filters.CharFilter(
        method='filter_student',
        label='Student Name'
    )
    
    # Ordering
    ordering = django_filters.OrderingFilter(
        fields=[
            'title', 'created_at', 'deadline', 'budget_min',
            'urgency_level', 'view_count', 'proposal_count'
        ],
        label='Order by'
    )
    
    class Meta:
        model = Requirement
        fields = [
            'title', 'description', 'subject', 'learning_level',
            'budget_min', 'budget_max', 'budget_type',
            'urgency_level', 'location_type', 'is_featured',
            'deadline_after', 'deadline_before', 'created_after', 'created_before',
            'student'
        ]
    
    def filter_budget_min(self, queryset, name, value):
        """Filter by minimum budget"""
        if not value:
            return queryset
        return queryset.filter(
            Q(budget_min__gte=value) | Q(budget_max__gte=value)
        )
    
    def filter_budget_max(self, queryset, name, value):
        """Filter by maximum budget"""
        if not value:
            return queryset
        return queryset.filter(
            Q(budget_min__lte=value) | Q(budget_max__lte=value)
        )
    
    def filter_student(self, queryset, name, value):
        """Filter by student name"""
        if not value:
            return queryset
        return queryset.filter(
            Q(student__first_name__icontains=value) |
            Q(student__last_name__icontains=value)
        )


class MessageFilterSet(django_filters.FilterSet):
    """Filter set for message searches"""
    
    # Basic filters
    content = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Message Content'
    )
    
    # Conversation filters
    conversation_type = django_filters.ChoiceFilter(
        method='filter_conversation_type',
        choices=[
            ('all', 'All Messages'),
            ('sent', 'Sent Messages'),
            ('received', 'Received Messages')
        ],
        label='Conversation Type'
    )
    
    # Date filters
    date_after = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Sent After'
    )
    
    date_before = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Sent Before'
    )
    
    # Status filters
    is_read = django_filters.BooleanFilter(
        field_name='is_read',
        label='Read'
    )
    
    is_unread = django_filters.BooleanFilter(
        method='filter_is_unread',
        label='Unread'
    )
    
    has_attachments = django_filters.BooleanFilter(
        method='filter_has_attachments',
        label='Has Attachments'
    )
    
    # Sender filter
    sender = django_filters.CharFilter(
        method='filter_sender',
        label='Sender Name'
    )
    
    # Ordering
    ordering = django_filters.OrderingFilter(
        fields=['created_at', 'sender__username', 'is_read'],
        label='Order by'
    )
    
    class Meta:
        model = Message
        fields = [
            'content', 'conversation_type', 'date_after', 'date_before',
            'is_read', 'is_unread', 'has_attachments', 'sender'
        ]
    
    def filter_conversation_type(self, queryset, name, value):
        """Filter by conversation type"""
        if not value or value == 'all':
            return queryset
        
        # This would need to be implemented based on the actual Message model
        # and relationship with User
        return queryset
    
    def filter_is_unread(self, queryset, name, value):
        """Filter for unread messages"""
        if not value:
            return queryset
        return queryset.filter(is_read=False)
    
    def filter_has_attachments(self, queryset, name, value):
        """Filter for messages with attachments"""
        if not value:
            return queryset
        return queryset.filter(attachments__isnull=False).distinct()
    
    def filter_sender(self, queryset, name, value):
        """Filter by sender name"""
        if not value:
            return queryset
        return queryset.filter(
            Q(sender__first_name__icontains=value) |
            Q(sender__last_name__icontains=value) |
            Q(sender__username__icontains=value)
        )


class PaymentFilterSet(django_filters.FilterSet):
    """Filter set for payment searches"""
    
    # Basic filters
    description = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Description'
    )
    
    transaction_id = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Transaction ID'
    )
    
    # Type and status filters
    payment_type = django_filters.ChoiceFilter(
        choices=Payment.PaymentType.choices,
        label='Payment Type'
    )
    
    status = django_filters.ChoiceFilter(
        choices=Payment.PaymentStatus.choices,
        label='Status'
    )
    
    # Amount filters
    amount_min = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='gte',
        label='Min Amount'
    )
    
    amount_max = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='lte',
        label='Max Amount'
    )
    
    # Currency filter
    currency = django_filters.ChoiceFilter(
        choices=[('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP')],
        label='Currency'
    )
    
    # Date filters
    date_after = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Created After'
    )
    
    date_before = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Created Before'
    )
    
    completed_after = django_filters.DateFilter(
        field_name='completed_at',
        lookup_expr='gte',
        label='Completed After'
    )
    
    completed_before = django_filters.DateFilter(
        field_name='completed_at',
        lookup_expr='lte',
        label='Completed Before'
    )
    
    # User filters
    payer = django_filters.CharFilter(
        method='filter_payer',
        label='Payer Name'
    )
    
    payee = django_filters.CharFilter(
        method='filter_payee',
        label='Payee Name'
    )
    
    # Ordering
    ordering = django_filters.OrderingFilter(
        fields=(
            'created_at', 'amount', 'status', 'payment_type',
            'payer__username', 'payee__username'
        ),
        label='Order by'
    )
    
    class Meta:
        model = Payment
        fields = [
            'description', 'transaction_id', 'payment_type', 'status',
            'amount_min', 'amount_max', 'currency',
            'date_after', 'date_before', 'completed_after', 'completed_before',
            'payer', 'payee'
        ]
    
    def filter_payer(self, queryset, name, value):
        """Filter by payer name"""
        if not value:
            return queryset
        return queryset.filter(
            Q(payer__first_name__icontains=value) |
            Q(payer__last_name__icontains=value) |
            Q(payer__username__icontains=value)
        )
    
    def filter_payee(self, queryset, name, value):
        """Filter by payee name"""
        if not value:
            return queryset
        return queryset.filter(
            Q(payee__first_name__icontains=value) |
            Q(payee__last_name__icontains=value) |
            Q(payee__username__icontains=value)
        )


class GlobalSearchFilterSet(django_filters.FilterSet):
    """Filter set for global searches across all content types"""
    
    # Basic filters
    query = django_filters.CharFilter(
        method='filter_query',
        label='Search Query'
    )
    
    content_type = django_filters.ChoiceFilter(
        choices=[
            ('all', 'All Content'),
            ('tutor', 'Tutors'),
            ('requirement', 'Requirements'),
            ('message', 'Messages'),
            ('payment', 'Payments')
        ],
        label='Content Type'
    )
    
    # Date filters
    date_range = django_filters.ChoiceFilter(
        method='filter_date_range',
        choices=[
            ('', 'Any Time'),
            ('1', 'Last 24 Hours'),
            ('7', 'Last Week'),
            ('30', 'Last Month'),
            ('90', 'Last 3 Months'),
            ('365', 'Last Year')
        ],
        label='Date Range'
    )
    
    # User type filter
    user_type = django_filters.ChoiceFilter(
        choices=[
            ('', 'All Users'),
            ('STUDENT', 'Students'),
            ('TUTOR', 'Tutors'),
            ('ADMIN', 'Administrators')
        ],
        label='User Type'
    )
    
    # Status filters
    is_active = django_filters.BooleanFilter(
        label='Active Users Only'
    )
    
    is_verified = django_filters.BooleanFilter(
        label='Verified Users Only'
    )
    
    # Ordering
    ordering = django_filters.OrderingFilter(
        fields=('created_at', 'relevance_score'),
        label='Order by'
    )
    
    class Meta:
        model = SearchIndex
        fields = ['query', 'content_type', 'date_range', 'user_type', 'is_active', 'is_verified']
    
    def filter_query(self, queryset, name, value):
        """Filter by search query"""
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value) |
            Q(content__icontains=value) |
            Q(metadata__icontains=value)
        )
    
    def filter_date_range(self, queryset, name, value):
        """Filter by date range"""
        if not value:
            return queryset
        
        now = timezone.now()
        
        if value == '1':  # Last 24 hours
            date_threshold = now - timedelta(hours=24)
        elif value == '7':  # Last week
            date_threshold = now - timedelta(days=7)
        elif value == '30':  # Last month
            date_threshold = now - timedelta(days=30)
        elif value == '90':  # Last 3 months
            date_threshold = now - timedelta(days=90)
        elif value == '365':  # Last year
            date_threshold = now - timedelta(days=365)
        else:
            return queryset
        
        return queryset.filter(last_updated__gte=date_threshold)