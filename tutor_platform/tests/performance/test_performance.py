"""
Performance tests for the Django tutoring platform.
"""
import pytest
import time
from django.test import TestCase, override_settings
from django.test.utils import override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.db import connection
from django.conf import settings
from django.test.client import Client
from unittest.mock import patch

from tests.factories import (
    UserFactory, TutorProfileFactory, StudentProfileFactory, CategoryFactory,
    SubjectFactory, RequirementFactory, ProposalFactory, PaymentFactory
)
from tests.utils.helpers import TestMixin, PerformanceTestMixin

User = get_user_model()


class DatabaseQueryPerformanceTest(TestCase, PerformanceTestMixin):
    """Performance tests for database queries."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        
    def test_requirement_list_query_count(self):
        """Test requirement list view query count."""
        # Create requirements
        RequirementFactory.create_batch(100)
        
        # Check query count
        with self.assertNumQueries(3):  # Should be minimal queries
            response = self.client.get(reverse('requirements:requirement_list'))
            self.assertEqual(response.status_code, 200)
            
    def test_requirement_detail_query_count(self):
        """Test requirement detail view query count."""
        # Create requirement with proposals
        requirement = RequirementFactory.create()
        ProposalFactory.create_batch(10, requirement=requirement)
        
        # Check query count
        with self.assertNumQueries(4):  # Should be minimal queries
            response = self.client.get(reverse('requirements:requirement_detail', kwargs={'pk': requirement.pk}))
            self.assertEqual(response.status_code, 200)
            
    def test_profile_view_query_count(self):
        """Test profile view query count."""
        # Create user with profile
        user = UserFactory.create(user_type='TUTOR')
        TutorProfileFactory.create(user=user)
        
        # Check query count
        with self.assertNumQueries(3):  # Should be minimal queries
            self.client.force_login(user)
            response = self.client.get(reverse('accounts:tutor_profile'))
            self.assertEqual(response.status_code, 200)
            
    def test_search_query_count(self):
        """Test search view query count."""
        # Create requirements
        RequirementFactory.create_batch(100)
        
        # Check query count
        with self.assertNumQueries(5):  # Should be minimal queries
            response = self.client.get(reverse('search:search'), {'q': 'Python'})
            self.assertEqual(response.status_code, 200)
            
    def test_api_requirement_list_query_count(self):
        """Test API requirement list query count."""
        # Create requirements
        RequirementFactory.create_batch(100)
        
        # Check query count
        with self.assertNumQueries(3):  # Should be minimal queries
            response = self.client.get(reverse('api:requirement-list'))
            self.assertEqual(response.status_code, 200)
            
    def test_complex_join_query_performance(self):
        """Test complex join query performance."""
        # Create complex data
        users = UserFactory.create_batch(50)
        tutors = [UserFactory.create(user_type='TUTOR') for _ in range(50)]
        tutor_profiles = [TutorProfileFactory.create(user=tutor) for tutor in tutors]
        
        categories = CategoryFactory.create_batch(10)
        subjects = [SubjectFactory.create(category=category) for category in categories]
        
        requirements = []
        for i in range(100):
            requirement = RequirementFactory.create(
                subject=subjects[i % len(subjects)],
                created_by=users[i % len(users)]
            )
            # Create proposals for some requirements
            if i % 2 == 0:
                ProposalFactory.create_batch(
                    5,
                    requirement=requirement,
                    created_by=tutors[i % len(tutors)]
                )
            requirements.append(requirement)
            
        # Time the query
        start_time = time.time()
        
        # Execute complex query
        from django.db.models import Count, Avg
        from requirements.models import Requirement  # Import here to avoid circular imports
        
        requirements_with_stats = Requirement.objects.annotate(
            proposal_count=Count('proposal'),
            avg_proposal_rate=Avg('proposal__hourly_rate')
        ).filter(
            proposal_count__gt=0
        ).order_by('-avg_proposal_rate')
        
        # Force evaluation
        list(requirements_with_stats)
        
        end_time = time.time()
        query_time = end_time - start_time
        
        # Check query time (should be under 1 second for 100 records)
        self.assertLess(query_time, 1.0)
        
    def test_bulk_create_performance(self):
        """Test bulk create performance."""
        # Time bulk create
        start_time = time.time()
        
        # Bulk create 1000 requirements
        requirements = [
            RequirementFactory.build() for _ in range(1000)
        ]
        Requirement.objects.bulk_create(requirements)
        
        end_time = time.time()
        create_time = end_time - start_time
        
        # Check create time (should be under 1 second for 1000 records)
        self.assertLess(create_time, 1.0)
        
        # Verify records were created
        self.assertEqual(Requirement.objects.count(), 1000)
        
    def test_bulk_update_performance(self):
        """Test bulk update performance."""
        # Create requirements
        requirements = RequirementFactory.create_batch(1000)
        
        # Time bulk update
        start_time = time.time()
        
        # Bulk update all requirements
        for requirement in requirements:
            requirement.budget = 100.00
            
        Requirement.objects.bulk_update(
            requirements,
            ['budget']
        )
        
        end_time = time.time()
        update_time = end_time - start_time
        
        # Check update time (should be under 1 second for 1000 records)
        self.assertLess(update_time, 1.0)
        
        # Verify records were updated
        for requirement in Requirement.objects.all():
            self.assertEqual(requirement.budget, 100.00)


class PageLoadPerformanceTest(TestCase, PerformanceTestMixin):
    """Performance tests for page load times."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        
    def test_home_page_load_time(self):
        """Test home page load time."""
        # Time page load
        start_time = time.time()
        
        response = self.client.get(reverse('home'))
        
        end_time = time.time()
        load_time = end_time - start_time
        
        # Check load time (should be under 0.5 seconds)
        self.assertLess(load_time, 0.5)
        self.assertEqual(response.status_code, 200)
        
    def test_requirement_list_page_load_time(self):
        """Test requirement list page load time."""
        # Create requirements
        RequirementFactory.create_batch(100)
        
        # Time page load
        start_time = time.time()
        
        response = self.client.get(reverse('requirements:requirement_list'))
        
        end_time = time.time()
        load_time = end_time - start_time
        
        # Check load time (should be under 1 second for 100 records)
        self.assertLess(load_time, 1.0)
        self.assertEqual(response.status_code, 200)
        
    def test_requirement_detail_page_load_time(self):
        """Test requirement detail page load time."""
        # Create requirement with proposals
        requirement = RequirementFactory.create()
        ProposalFactory.create_batch(20, requirement=requirement)
        
        # Time page load
        start_time = time.time()
        
        response = self.client.get(reverse('requirements:requirement_detail', kwargs={'pk': requirement.pk}))
        
        end_time = time.time()
        load_time = end_time - start_time
        
        # Check load time (should be under 1 second for 20 proposals)
        self.assertLess(load_time, 1.0)
        self.assertEqual(response.status_code, 200)
        
    def test_search_page_load_time(self):
        """Test search page load time."""
        # Create requirements
        RequirementFactory.create_batch(1000)
        
        # Time page load
        start_time = time.time()
        
        response = self.client.get(reverse('search:search'), {'q': 'Python'})
        
        end_time = time.time()
        load_time = end_time - start_time
        
        # Check load time (should be under 2 seconds for 1000 records)
        self.assertLess(load_time, 2.0)
        self.assertEqual(response.status_code, 200)
        
    def test_profile_page_load_time(self):
        """Test profile page load time."""
        # Create user with profile and history
        user = UserFactory.create(user_type='TUTOR')
        tutor_profile = TutorProfileFactory.create(user=user)
        
        # Create requirements and proposals for this tutor
        requirements = RequirementFactory.create_batch(10)
        for requirement in requirements:
            ProposalFactory.create(requirement=requirement, created_by=user)
            
        # Time page load
        start_time = time.time()
        
        self.client.force_login(user)
        response = self.client.get(reverse('accounts:tutor_profile'))
        
        end_time = time.time()
        load_time = end_time - start_time
        
        # Check load time (should be under 1 second)
        self.assertLess(load_time, 1.0)
        self.assertEqual(response.status_code, 200)
        
    def test_admin_dashboard_load_time(self):
        """Test admin dashboard load time."""
        # Create admin user
        admin_user = UserFactory.create(is_staff=True)
        
        # Create various data for dashboard
        RequirementFactory.create_batch(100)
        ProposalFactory.create_batch(50)
        PaymentFactory.create_batch(25)
        
        # Time page load
        start_time = time.time()
        
        self.client.force_login(admin_user)
        response = self.client.get(reverse('admin:index'))
        
        end_time = time.time()
        load_time = end_time - start_time
        
        # Check load time (should be under 2 seconds)
        self.assertLess(load_time, 2.0)
        self.assertEqual(response.status_code, 200)


class APIResponseTimeTest(TestCase, PerformanceTestMixin):
    """Performance tests for API response times."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        
    def test_api_requirement_list_response_time(self):
        """Test API requirement list response time."""
        # Create requirements
        RequirementFactory.create_batch(100)
        
        # Time API response
        start_time = time.time()
        
        response = self.client.get(reverse('api:requirement-list'))
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Check response time (should be under 0.5 seconds)
        self.assertLess(response_time, 0.5)
        self.assertEqual(response.status_code, 200)
        
    def test_api_requirement_detail_response_time(self):
        """Test API requirement detail response time."""
        # Create requirement with proposals
        requirement = RequirementFactory.create()
        ProposalFactory.create_batch(20, requirement=requirement)
        
        # Time API response
        start_time = time.time()
        
        response = self.client.get(reverse('api:requirement-detail', kwargs={'pk': requirement.pk}))
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Check response time (should be under 0.5 seconds)
        self.assertLess(response_time, 0.5)
        self.assertEqual(response.status_code, 200)
        
    def test_api_search_response_time(self):
        """Test API search response time."""
        # Create requirements
        RequirementFactory.create_batch(1000)
        
        # Time API response
        start_time = time.time()
        
        response = self.client.get(reverse('api:search'), {'q': 'Python'})
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Check response time (should be under 1 second for 1000 records)
        self.assertLess(response_time, 1.0)
        self.assertEqual(response.status_code, 200)
        
    def test_api_user_profile_response_time(self):
        """Test API user profile response time."""
        # Create user with profile and history
        user = UserFactory.create(user_type='TUTOR')
        tutor_profile = TutorProfileFactory.create(user=user)
        
        # Create requirements and proposals for this user
        requirements = RequirementFactory.create_batch(10)
        for requirement in requirements:
            ProposalFactory.create(requirement=requirement, created_by=user)
            
        # Time API response
        start_time = time.time()
        
        # Simulate authenticated API request
        from rest_framework.authtoken.models import Token
        token = Token.objects.get_or_create(user=user)[0]
        
        response = self.client.get(
            reverse('api:user-profile'),
            HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Check response time (should be under 0.5 seconds)
        self.assertLess(response_time, 0.5)
        self.assertEqual(response.status_code, 200)


class SearchPerformanceTest(TestCase, PerformanceTestMixin):
    """Performance tests for search functionality."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.client = Client()
        
    def test_search_performance_with_large_dataset(self):
        """Test search performance with large dataset."""
        # Create large dataset
        categories = CategoryFactory.create_batch(20)
        subjects = []
        for category in categories:
            subjects.extend(SubjectFactory.create_batch(5, category=category))
            
        # Create 10,000 requirements
        RequirementFactory.create_batch(
            10000,
            subject=lambda: subjects[0]  # Use first subject for simplicity
        )
        
        # Time search
        start_time = time.time()
        
        response = self.client.get(reverse('search:search'), {'q': 'Python'})
        
        end_time = time.time()
        search_time = end_time - start_time
        
        # Check search time (should be under 2 seconds for 10,000 records)
        self.assertLess(search_time, 2.0)
        self.assertEqual(response.status_code, 200)
        
    def test_search_performance_with_complex_filters(self):
        """Test search performance with complex filters."""
        # Create requirements with varied data
        categories = CategoryFactory.create_batch(10)
        subjects = []
        for category in categories:
            subjects.extend(SubjectFactory.create_batch(5, category=category))
            
        requirements = []
        for i in range(1000):
            requirement = RequirementFactory.create(
                subject=subjects[i % len(subjects)],
                budget=(i % 10) * 10 + 10  # Budgets from 10 to 100
            )
            requirements.append(requirement)
            
        # Time complex search
        start_time = time.time()
        
        response = self.client.get(reverse('search:search'), {
            'q': 'Python',
            'category': categories[0].id,
            'min_budget': 30,
            'max_budget': 70
        })
        
        end_time = time.time()
        search_time = end_time - start_time
        
        # Check search time (should be under 1 second for 1000 records)
        self.assertLess(search_time, 1.0)
        self.assertEqual(response.status_code, 200)
        
    def test_full_text_search_performance(self):
        """Test full-text search performance."""
        # Create requirements with varied content
        requirements = []
        for i in range(1000):
            requirement = RequirementFactory.create(
                title=f'Python Programming Tutorial {i}',
                description=f'Learn Python programming with expert tutors. This is tutorial number {i} in our comprehensive Python learning series.'
            )
            requirements.append(requirement)
            
        # Time full-text search
        start_time = time.time()
        
        response = self.client.get(reverse('search:search'), {'q': 'comprehensive Python'})
        
        end_time = time.time()
        search_time = end_time - start_time
        
        # Check search time (should be under 1 second for 1000 records)
        self.assertLess(search_time, 1.0)
        self.assertEqual(response.status_code, 200)


class ConcurrentUserLoadTest(TestCase, PerformanceTestMixin):
    """Performance tests for concurrent user load."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_concurrent_requirement_list_load(self):
        """Test concurrent load on requirement list."""
        # Create requirements
        RequirementFactory.create_batch(100)
        
        # Simulate concurrent requests
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            """Make a request and record time."""
            client = Client()
            start_time = time.time()
            
            response = client.get(reverse('requirements:requirement_list'))
            
            end_time = time.time()
            load_time = end_time - start_time
            
            results.put({
                'status_code': response.status_code,
                'load_time': load_time
            })
            
        # Create 20 concurrent threads
        threads = []
        for _ in range(20):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Check results
        successful_requests = 0
        total_load_time = 0
        
        while not results.empty():
            result = results.get()
            if result['status_code'] == 200:
                successful_requests += 1
                total_load_time += result['load_time']
                
        # Check that all requests were successful
        self.assertEqual(successful_requests, 20)
        
        # Check average load time (should be under 1 second)
        avg_load_time = total_load_time / successful_requests
        self.assertLess(avg_load_time, 1.0)
        
    def test_concurrent_api_load(self):
        """Test concurrent load on API endpoints."""
        # Create requirements
        RequirementFactory.create_batch(100)
        
        # Simulate concurrent API requests
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_api_request():
            """Make an API request and record time."""
            client = Client()
            start_time = time.time()
            
            response = client.get(reverse('api:requirement-list'))
            
            end_time = time.time()
            response_time = end_time - start_time
            
            results.put({
                'status_code': response.status_code,
                'response_time': response_time
            })
            
        # Create 50 concurrent threads
        threads = []
        for _ in range(50):
            thread = threading.Thread(target=make_api_request)
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Check results
        successful_requests = 0
        total_response_time = 0
        
        while not results.empty():
            result = results.get()
            if result['status_code'] == 200:
                successful_requests += 1
                total_response_time += result['response_time']
                
        # Check that all requests were successful
        self.assertEqual(successful_requests, 50)
        
        # Check average response time (should be under 0.5 seconds)
        avg_response_time = total_response_time / successful_requests
        self.assertLess(avg_response_time, 0.5)
        
    def test_concurrent_search_load(self):
        """Test concurrent load on search."""
        # Create requirements
        RequirementFactory.create_batch(1000)
        
        # Simulate concurrent search requests
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_search_request():
            """Make a search request and record time."""
            client = Client()
            start_time = time.time()
            
            response = client.get(reverse('search:search'), {'q': 'Python'})
            
            end_time = time.time()
            search_time = end_time - start_time
            
            results.put({
                'status_code': response.status_code,
                'search_time': search_time
            })
            
        # Create 30 concurrent threads
        threads = []
        for _ in range(30):
            thread = threading.Thread(target=make_search_request)
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        # Check results
        successful_requests = 0
        total_search_time = 0
        
        while not results.empty():
            result = results.get()
            if result['status_code'] == 200:
                successful_requests += 1
                total_search_time += result['search_time']
                
        # Check that all requests were successful
        self.assertEqual(successful_requests, 30)
        
        # Check average search time (should be under 2 seconds)
        avg_search_time = total_search_time / successful_requests
        self.assertLess(avg_search_time, 2.0)


class MemoryUsageTest(TestCase, PerformanceTestMixin):
    """Performance tests for memory usage."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_memory_usage_with_large_dataset(self):
        """Test memory usage with large dataset."""
        # Get initial memory usage
        import psutil
        import os
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large dataset
        requirements = RequirementFactory.create_batch(1000)
        
        for requirement in requirements:
            # Create related data
            ProposalFactory.create_batch(10, requirement=requirement)
            
        # Process all data
        from requirements.models import Requirement  # Import here to avoid circular imports
        
        requirements_with_data = Requirement.objects.all().prefetch_related('proposal')
        count = 0
        for requirement in requirements_with_data:
            count += 1
            # Access related data
            list(requirement.proposal.all())
            
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Check memory usage (should be reasonable)
        self.assertLess(memory_increase, 200)  # Less than 200MB increase
        self.assertEqual(count, 1000)
        
    def test_memory_usage_with_pagination(self):
        """Test memory usage with pagination."""
        # Get initial memory usage
        import psutil
        import os
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large dataset
        RequirementFactory.create_batch(5000)
        
        # Process data with pagination
        from requirements.models import Requirement  # Import here to avoid circular imports
        
        page_size = 50
        page_count = 0
        
        for page in range(0, 5000, page_size):
            requirements = Requirement.objects.all()[page:page + page_size]
            page_count += 1
            
            # Process requirements
            for requirement in requirements:
                # Access requirement data
                requirement.title
                requirement.description
                
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Check memory usage (should be reasonable with pagination)
        self.assertLess(memory_increase, 100)  # Less than 100MB increase
        self.assertEqual(page_count, 100)  # 5000 / 50


class DatabaseIndexPerformanceTest(TestCase, PerformanceTestMixin):
    """Performance tests for database indexes."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_search_performance_with_index(self):
        """Test search performance with database index."""
        # Create large dataset
        RequirementFactory.create_batch(5000)
        
        # Time search without index
        with connection.cursor() as cursor:
            # Drop index if it exists
            cursor.execute("DROP INDEX IF EXISTS idx_requirements_title ON requirements_requirement;")
            
        start_time = time.time()
        
        response = self.client.get(reverse('search:search'), {'q': 'Python'})
        
        end_time = time.time()
        search_time_without_index = end_time - start_time
        
        # Create index
        with connection.cursor() as cursor:
            cursor.execute("CREATE INDEX idx_requirements_title ON requirements_requirement (title);")
            
        # Time search with index
        start_time = time.time()
        
        response = self.client.get(reverse('search:search'), {'q': 'Python'})
        
        end_time = time.time()
        search_time_with_index = end_time - start_time
        
        # Check that search is faster with index
        self.assertLess(search_time_with_index, search_time_without_index)
        self.assertEqual(response.status_code, 200)
        
    def test_join_performance_with_index(self):
        """Test join performance with database index."""
        # Create large dataset
        users = UserFactory.create_batch(1000)
        tutors = [UserFactory.create(user_type='TUTOR') for _ in range(100)]
        tutor_profiles = [TutorProfileFactory.create(user=tutor) for tutor in tutors]
        
        categories = CategoryFactory.create_batch(10)
        subjects = []
        for category in categories:
            subjects.extend(SubjectFactory.create_batch(5, category=category))
            
        requirements = []
        for i in range(5000):
            requirement = RequirementFactory.create(
                subject=subjects[i % len(subjects)],
                created_by=users[i % len(users)]
            )
            requirements.append(requirement)
            
        # Time complex join without index
        with connection.cursor() as cursor:
            # Drop index if it exists
            cursor.execute("DROP INDEX IF EXISTS idx_proposals_requirement_id ON requirements_proposal;")
            
        start_time = time.time()
        
        from requirements.models import Requirement  # Import here to avoid circular imports
        requirements_with_proposals = Requirement.objects.annotate(
            proposal_count=Count('proposal')
        ).filter(proposal_count__gt=0)
        
        # Force evaluation
        list(requirements_with_proposals)
        
        end_time = time.time()
        join_time_without_index = end_time - start_time
        
        # Create index
        with connection.cursor() as cursor:
            cursor.execute("CREATE INDEX idx_proposals_requirement_id ON requirements_proposal (requirement_id);")
            
        # Time complex join with index
        start_time = time.time()
        
        requirements_with_proposals = Requirement.objects.annotate(
            proposal_count=Count('proposal')
        ).filter(proposal_count__gt=0)
        
        # Force evaluation
        list(requirements_with_proposals)
        
        end_time = time.time()
        join_time_with_index = end_time - start_time
        
        # Check that join is faster with index
        self.assertLess(join_time_with_index, join_time_without_index)