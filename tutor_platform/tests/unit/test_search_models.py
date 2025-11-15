"""
Unit tests for search app models.
"""
import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from tests.factories import (
    UserFactory, SearchQueryFactory, SearchResultFactory, SearchFilterFactory,
    SearchIndexFactory, SearchHistoryFactory
)
from tests.utils.helpers import TestMixin, DateTimeTestMixin


class SearchQueryModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for SearchQuery model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_search_query_creation(self):
        """Test SearchQuery model creation."""
        search_query = SearchQueryFactory.create(user=self.user)
        self.assertTrue(isinstance(search_query, SearchQueryFactory._meta.model))
        self.assertEqual(search_query.user, self.user)
        
    def test_search_query_string_representation(self):
        """Test SearchQuery string representation."""
        search_query = SearchQueryFactory.create(
            user=self.user,
            query="Python programming"
        )
        expected = f"Python programming"
        self.assertEqual(str(search_query), expected)
        
    def test_search_query_query_validation(self):
        """Test query field validation."""
        search_query = SearchQueryFactory.build(user=self.user)
        
        # Test empty query
        search_query.query = ""
        with self.assertRaises(ValidationError):
            search_query.full_clean()
            
    def test_search_query_ip_address_validation(self):
        """Test ip_address field validation."""
        search_query = SearchQueryFactory.build(user=self.user)
        
        # Test invalid IP address
        search_query.ip_address = "invalid-ip"
        with self.assertRaises(ValidationError):
            search_query.full_clean()
            
    def test_search_query_user_relationship(self):
        """Test SearchQuery-User relationship."""
        search_query = SearchQueryFactory.create(user=self.user)
        
        # Test reverse relationship
        self.assertIn(search_query, self.user.search_queries.all())
        
    def test_search_query_results_count_method(self):
        """Test results_count method."""
        search_query = SearchQueryFactory.create(user=self.user)
        
        # Create search results
        SearchResultFactory.create(search_query=search_query)
        SearchResultFactory.create(search_query=search_query)
        
        self.assertEqual(search_query.results_count(), 2)
        
    def test_search_query_has_results_method(self):
        """Test has_results method."""
        search_query = SearchQueryFactory.create(user=self.user)
        
        # Test without results
        self.assertFalse(search_query.has_results())
        
        # Create search result
        SearchResultFactory.create(search_query=search_query)
        
        # Test with results
        self.assertTrue(search_query.has_results())


class SearchResultModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for SearchResult model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        self.search_query = SearchQueryFactory.create(user=self.user)
        
    def test_search_result_creation(self):
        """Test SearchResult model creation."""
        search_result = SearchResultFactory.create(search_query=self.search_query)
        self.assertTrue(isinstance(search_result, SearchResultFactory._meta.model))
        self.assertEqual(search_result.search_query, self.search_query)
        
    def test_search_result_string_representation(self):
        """Test SearchResult string representation."""
        search_result = SearchResultFactory.create(
            search_query=self.search_query,
            title="Python Tutor"
        )
        expected = f"Python Tutor"
        self.assertEqual(str(search_result), expected)
        
    def test_search_result_title_validation(self):
        """Test title field validation."""
        search_result = SearchResultFactory.build(search_query=self.search_query)
        
        # Test empty title
        search_result.title = ""
        with self.assertRaises(ValidationError):
            search_result.full_clean()
            
    def test_search_result_content_type_validation(self):
        """Test content_type field validation."""
        search_result = SearchResultFactory.build(search_query=self.search_query)
        
        # Test invalid content type
        search_result.content_type = "invalid-type"
        with self.assertRaises(ValidationError):
            search_result.full_clean()
            
    def test_search_result_relevance_score_validation(self):
        """Test relevance_score field validation."""
        search_result = SearchResultFactory.build(search_query=self.search_query)
        
        # Test negative score
        search_result.relevance_score = -1.0
        with self.assertRaises(ValidationError):
            search_result.full_clean()
            
        # Test score above 1.0
        search_result.relevance_score = 1.5
        with self.assertRaises(ValidationError):
            search_result.full_clean()
            
    def test_search_result_search_query_relationship(self):
        """Test SearchResult-SearchQuery relationship."""
        search_result = SearchResultFactory.create(search_query=self.search_query)
        
        # Test reverse relationship
        self.assertIn(search_result, self.search_query.results.all())


class SearchFilterModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for SearchFilter model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        self.search_query = SearchQueryFactory.create(user=self.user)
        
    def test_search_filter_creation(self):
        """Test SearchFilter model creation."""
        search_filter = SearchFilterFactory.create(search_query=self.search_query)
        self.assertTrue(isinstance(search_filter, SearchFilterFactory._meta.model))
        self.assertEqual(search_filter.search_query, self.search_query)
        
    def test_search_filter_string_representation(self):
        """Test SearchFilter string representation."""
        search_filter = SearchFilterFactory.create(
            search_query=self.search_query,
            filter_type="SUBJECT",
            filter_value="Mathematics"
        )
        expected = f"SUBJECT: Mathematics"
        self.assertEqual(str(search_filter), expected)
        
    def test_search_filter_filter_type_choices(self):
        """Test filter_type field choices."""
        search_filter = SearchFilterFactory.build(search_query=self.search_query)
        
        valid_types = ['SUBJECT', 'PRICE', 'RATING', 'LOCATION', 'AVAILABILITY']
        for filter_type in valid_types:
            search_filter.filter_type = filter_type
            search_filter.full_clean()  # Should not raise
            
        # Test invalid type
        search_filter.filter_type = 'INVALID'
        with self.assertRaises(ValidationError):
            search_filter.full_clean()
            
    def test_search_filter_filter_value_validation(self):
        """Test filter_value field validation."""
        search_filter = SearchFilterFactory.build(search_query=self.search_query)
        
        # Test empty filter value
        search_filter.filter_value = ""
        with self.assertRaises(ValidationError):
            search_filter.full_clean()
            
    def test_search_filter_search_query_relationship(self):
        """Test SearchFilter-SearchQuery relationship."""
        search_filter = SearchFilterFactory.create(search_query=self.search_query)
        
        # Test reverse relationship
        self.assertIn(search_filter, self.search_query.filters.all())


class SearchIndexModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for SearchIndex model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_search_index_creation(self):
        """Test SearchIndex model creation."""
        search_index = SearchIndexFactory.create()
        self.assertTrue(isinstance(search_index, SearchIndexFactory._meta.model))
        
    def test_search_index_string_representation(self):
        """Test SearchIndex string representation."""
        search_index = SearchIndexFactory.create(
            title="Python Programming Tutorial"
        )
        expected = f"Python Programming Tutorial"
        self.assertEqual(str(search_index), expected)
        
    def test_search_index_title_validation(self):
        """Test title field validation."""
        search_index = SearchIndexFactory.build()
        
        # Test empty title
        search_index.title = ""
        with self.assertRaises(ValidationError):
            search_index.full_clean()
            
    def test_search_index_content_type_validation(self):
        """Test content_type field validation."""
        search_index = SearchIndexFactory.build()
        
        # Test invalid content type
        search_index.content_type = "invalid-type"
        with self.assertRaises(ValidationError):
            search_index.full_clean()
            
    def test_search_index_object_id_validation(self):
        """Test object_id field validation."""
        search_index = SearchIndexFactory.build()
        
        # Test negative object ID
        search_index.object_id = -1
        with self.assertRaises(ValidationError):
            search_index.full_clean()
            
    def test_search_index_search_vector_validation(self):
        """Test search_vector field validation."""
        search_index = SearchIndexFactory.build()
        
        # Test empty search vector
        search_index.search_vector = ""
        with self.assertRaises(ValidationError):
            search_index.full_clean()
            
    def test_search_index_is_indexed_default(self):
        """Test is_indexed defaults to True."""
        search_index = SearchIndexFactory.build()
        self.assertTrue(search_index.is_indexed)
        
    def test_search_index_search_vector_update_method(self):
        """Test update_search_vector method."""
        search_index = SearchIndexFactory.create(
            title="Python Programming",
            content="Learn Python programming from scratch"
        )
        
        # Update search vector
        search_index.update_search_vector()
        
        # Check that search vector is updated (implementation depends on actual method)
        self.assertIsNotNone(search_index.search_vector)
        
    def test_search_index_reindex_method(self):
        """Test reindex method."""
        search_index = SearchIndexFactory.create()
        
        # Reindex
        search_index.reindex()
        
        # Check that is_indexed is True (implementation depends on actual method)
        self.assertTrue(search_index.is_indexed)


class SearchHistoryModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for SearchHistory model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_search_history_creation(self):
        """Test SearchHistory model creation."""
        search_history = SearchHistoryFactory.create(user=self.user)
        self.assertTrue(isinstance(search_history, SearchHistoryFactory._meta.model))
        self.assertEqual(search_history.user, self.user)
        
    def test_search_history_string_representation(self):
        """Test SearchHistory string representation."""
        search_history = SearchHistoryFactory.create(
            user=self.user,
            query="Python tutor"
        )
        expected = f"Python tutor"
        self.assertEqual(str(search_history), expected)
        
    def test_search_history_query_validation(self):
        """Test query field validation."""
        search_history = SearchHistoryFactory.build(user=self.user)
        
        # Test empty query
        search_history.query = ""
        with self.assertRaises(ValidationError):
            search_history.full_clean()
            
    def test_search_history_user_relationship(self):
        """Test SearchHistory-User relationship."""
        search_history = SearchHistoryFactory.create(user=self.user)
        
        # Test reverse relationship
        self.assertIn(search_history, self.user.search_history.all())
        
    def test_search_history_results_count_validation(self):
        """Test results_count field validation."""
        search_history = SearchHistoryFactory.build(user=self.user)
        
        # Test negative results count
        search_history.results_count = -1
        with self.assertRaises(ValidationError):
            search_history.full_clean()


class SearchQueryQuerySetTest(TestCase, TestMixin):
    """Test cases for SearchQuery model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_by_user_queryset(self):
        """Test by_user queryset method."""
        # Create queries for different users
        user2 = UserFactory.create()
        
        query1 = SearchQueryFactory.create(user=self.user)
        query2 = SearchQueryFactory.create(user=user2)
        
        # Test filtering by user
        user_queries = SearchQuery.objects.by_user(self.user.id)
        self.assertEqual(user_queries.count(), 1)
        self.assertIn(query1, user_queries)
        self.assertNotIn(query2, user_queries)
        
    def test_popular_queryset(self):
        """Test popular queryset method."""
        # Create queries with different result counts
        popular_query = SearchQueryFactory.create(user=self.user)
        SearchResultFactory.create_batch(5, search_query=popular_query)
        
        unpopular_query = SearchQueryFactory.create(user=self.user)
        SearchResultFactory.create_batch(1, search_query=unpopular_query)
        
        # Test popular queries (with more than 3 results)
        popular_queries = SearchQuery.objects.popular(min_results=3)
        self.assertEqual(popular_queries.count(), 1)
        self.assertIn(popular_query, popular_queries)
        self.assertNotIn(unpopular_query, popular_queries)
        
    def test_recent_queryset(self):
        """Test recent queryset method."""
        # Create queries with different dates
        old_query = SearchQueryFactory.create(
            user=self.user,
            created_at=self.create_past_date(days=10)
        )
        recent_query = SearchQueryFactory.create(
            user=self.user,
            created_at=self.create_past_date(days=2)
        )
        future_query = SearchQueryFactory.create(
            user=self.user,
            created_at=self.create_future_date(days=5)
        )
        
        # Test recent queries (last 7 days)
        recent_queries = SearchQuery.objects.recent(days=7)
        self.assertEqual(recent_queries.count(), 2)
        self.assertIn(recent_query, recent_queries)
        self.assertIn(future_query, recent_queries)
        self.assertNotIn(old_query, recent_queries)


class SearchResultQuerySetTest(TestCase, TestMixin):
    """Test cases for SearchResult model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        self.search_query = SearchQueryFactory.create(user=self.user)
        
    def test_by_query_queryset(self):
        """Test by_query queryset method."""
        # Create results for different queries
        query2 = SearchQueryFactory.create(user=self.user)
        
        result1 = SearchResultFactory.create(search_query=self.search_query)
        result2 = SearchResultFactory.create(search_query=query2)
        
        # Test filtering by query
        query_results = SearchResult.objects.by_query(self.search_query.id)
        self.assertEqual(query_results.count(), 1)
        self.assertIn(result1, query_results)
        self.assertNotIn(result2, query_results)
        
    def test_by_content_type_queryset(self):
        """Test by_content_type queryset method."""
        # Create results with different content types
        tutor_result = SearchResultFactory.create(
            search_query=self.search_query,
            content_type="tutor"
        )
        requirement_result = SearchResultFactory.create(
            search_query=self.search_query,
            content_type="requirement"
        )
        
        # Test filtering by content type
        tutor_results = SearchResult.objects.by_content_type("tutor")
        self.assertEqual(tutor_results.count(), 1)
        self.assertIn(tutor_result, tutor_results)
        self.assertNotIn(requirement_result, tutor_results)
        
    def test_by_relevance_queryset(self):
        """Test by_relevance queryset method."""
        # Create results with different relevance scores
        high_relevance = SearchResultFactory.create(
            search_query=self.search_query,
            relevance_score=0.9
        )
        low_relevance = SearchResultFactory.create(
            search_query=self.search_query,
            relevance_score=0.3
        )
        
        # Test filtering by minimum relevance
        relevant_results = SearchResult.objects.by_relevance(min_score=0.5)
        self.assertEqual(relevant_results.count(), 1)
        self.assertIn(high_relevance, relevant_results)
        self.assertNotIn(low_relevance, relevant_results)


class SearchIndexQuerySetTest(TestCase, TestMixin):
    """Test cases for SearchIndex model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_indexed_queryset(self):
        """Test indexed queryset method."""
        # Create indices with different indexed status
        indexed = SearchIndexFactory.create(is_indexed=True)
        not_indexed = SearchIndexFactory.create(is_indexed=False)
        
        indexed_indices = SearchIndex.objects.indexed()
        self.assertEqual(indexed_indices.count(), 1)
        self.assertIn(indexed, indexed_indices)
        self.assertNotIn(not_indexed, indexed_indices)
        
    def test_by_content_type_queryset(self):
        """Test by_content_type queryset method."""
        # Create indices with different content types
        tutor_index = SearchIndexFactory.create(content_type="tutor")
        requirement_index = SearchIndexFactory.create(content_type="requirement")
        
        # Test filtering by content type
        tutor_indices = SearchIndex.objects.by_content_type("tutor")
        self.assertEqual(tutor_indices.count(), 1)
        self.assertIn(tutor_index, tutor_indices)
        self.assertNotIn(requirement_index, tutor_indices)
        
    def test_search_queryset(self):
        """Test search queryset method."""
        # Create indices with different content
        python_index = SearchIndexFactory.create(
            title="Python Programming",
            content="Learn Python programming from scratch"
        )
        math_index = SearchIndexFactory.create(
            title="Mathematics Tutor",
            content="Expert mathematics tutoring"
        )
        
        # Test searching for "Python"
        python_results = SearchIndex.objects.search("Python")
        self.assertEqual(python_results.count(), 1)
        self.assertIn(python_index, python_results)
        self.assertNotIn(math_index, python_results)


class SearchHistoryQuerySetTest(TestCase, TestMixin):
    """Test cases for SearchHistory model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_by_user_queryset(self):
        """Test by_user queryset method."""
        # Create history for different users
        user2 = UserFactory.create()
        
        history1 = SearchHistoryFactory.create(user=self.user)
        history2 = SearchHistoryFactory.create(user=user2)
        
        # Test filtering by user
        user_history = SearchHistory.objects.by_user(self.user.id)
        self.assertEqual(user_history.count(), 1)
        self.assertIn(history1, user_history)
        self.assertNotIn(history2, user_history)
        
    def test_recent_queryset(self):
        """Test recent queryset method."""
        # Create history with different dates
        old_history = SearchHistoryFactory.create(
            user=self.user,
            created_at=self.create_past_date(days=10)
        )
        recent_history = SearchHistoryFactory.create(
            user=self.user,
            created_at=self.create_past_date(days=2)
        )
        future_history = SearchHistoryFactory.create(
            user=self.user,
            created_at=self.create_future_date(days=5)
        )
        
        # Test recent history (last 7 days)
        recent_history_items = SearchHistory.objects.recent(days=7)
        self.assertEqual(recent_history_items.count(), 2)
        self.assertIn(recent_history, recent_history_items)
        self.assertIn(future_history, recent_history_items)
        self.assertNotIn(old_history, recent_history_items)


class SearchSignalTest(TestCase, TestMixin):
    """Test cases for search signals."""
    
    def test_search_query_created_signal(self):
        """Test SearchQuery creation signal."""
        # This would test that SearchQuery creation triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_search_index_updated_signal(self):
        """Test SearchIndex update signal."""
        # This would test that SearchIndex update triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic