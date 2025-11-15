import uuid
import json
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q
from django.contrib.postgres.search import SearchVector, SearchQuery as PGSearchQuery, SearchRank
from django.contrib.postgres.indexes import GinIndex

User = get_user_model()


class SearchQuery(models.Model):
    """Store search history for analytics and improvements"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='search_queries',
        help_text="User who performed the search (null for anonymous)"
    )
    query = models.CharField(
        max_length=500,
        help_text="Search query string"
    )
    search_type = models.CharField(
        max_length=20,
        choices=[
            ('GLOBAL', 'Global Search'),
            ('TUTOR', 'Tutor Search'),
            ('REQUIREMENT', 'Requirement Search'),
            ('MESSAGE', 'Message Search'),
            ('PAYMENT', 'Payment Search'),
        ],
        default='GLOBAL',
        help_text="Type of search performed"
    )
    filters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Filters applied to the search"
    )
    results_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of results returned"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the searcher"
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text="User agent string"
    )
    session_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Session identifier for anonymous users"
    )
    response_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Search response time in milliseconds"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Search Query'
        verbose_name_plural = 'Search Queries'
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['search_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['query']),
            models.Index(fields=['session_id']),
            GinIndex(fields=['filters']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Search: {self.query} by {self.user.get_full_name() if self.user else 'Anonymous'}"


class SearchFilter(models.Model):
    """Store saved search filters for users"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_search_filters',
        help_text="User who saved this filter"
    )
    name = models.CharField(
        max_length=100,
        help_text="Name for this saved filter"
    )
    search_type = models.CharField(
        max_length=20,
        choices=[
            ('GLOBAL', 'Global Search'),
            ('TUTOR', 'Tutor Search'),
            ('REQUIREMENT', 'Requirement Search'),
            ('MESSAGE', 'Message Search'),
            ('PAYMENT', 'Payment Search'),
        ],
        help_text="Type of search this filter applies to"
    )
    filters = models.JSONField(
        help_text="Filter configuration in JSON format"
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default filter for this search type"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this filter is publicly visible"
    )
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this filter has been used"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Search Filter'
        verbose_name_plural = 'Search Filters'
        unique_together = ['user', 'name']
        indexes = [
            models.Index(fields=['user_id']),
            models.Index(fields=['search_type']),
            models.Index(fields=['is_default']),
            models.Index(fields=['is_public']),
            GinIndex(fields=['filters']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default filter per search type per user
        if self.is_default:
            SearchFilter.objects.filter(
                user=self.user,
                search_type=self.search_type,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class SearchResult(models.Model):
    """Cache search results for performance"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search_query = models.ForeignKey(
        SearchQuery,
        on_delete=models.CASCADE,
        related_name='cached_results',
        help_text="Related search query"
    )
    content_type = models.CharField(
        max_length=50,
        help_text="Content type of the result (e.g., 'tutor', 'requirement')"
    )
    object_id = models.UUIDField(
        help_text="Primary key of the result object"
    )
    title = models.CharField(
        max_length=200,
        help_text="Title of the search result"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description/preview of the search result"
    )
    url = models.CharField(
        max_length=500,
        help_text="URL to the result object"
    )
    relevance_score = models.FloatField(
        default=0.0,
        help_text="Relevance score for ranking"
    )
    highlight_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Highlighted search terms in the result"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata about the result"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this cached result expires"
    )
    
    class Meta:
        verbose_name = 'Search Result'
        verbose_name_plural = 'Search Results'
        unique_together = ['search_query', 'content_type', 'object_id']
        indexes = [
            models.Index(fields=['search_query_id']),
            models.Index(fields=['content_type']),
            models.Index(fields=['relevance_score']),
            models.Index(fields=['created_at']),
            models.Index(fields=['expires_at']),
            GinIndex(fields=['highlight_data']),
            GinIndex(fields=['metadata']),
        ]
        ordering = ['-relevance_score', '-created_at']
    
    def __str__(self):
        return f"Result: {self.title} ({self.content_type})"
    
    def is_expired(self):
        """Check if the cached result has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at


class SearchIndex(models.Model):
    """Manage search indexes for different content types"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_type = models.CharField(
        max_length=50,
        help_text="Content type being indexed (e.g., 'tutor', 'requirement')"
    )
    object_id = models.UUIDField(
        help_text="Primary key of the indexed object"
    )
    title = models.CharField(
        max_length=200,
        help_text="Title of the indexed object"
    )
    content = models.TextField(
        help_text="Full text content for searching"
    )
    search_vector = models.TextField(
        blank=True,
        null=True,
        help_text="Processed search vector for full-text search"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional searchable metadata"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this index entry is active"
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="When this index was last updated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Search Index'
        verbose_name_plural = 'Search Indexes'
        unique_together = ['content_type', 'object_id']
        indexes = [
            models.Index(fields=['content_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_updated']),
            GinIndex(fields=['search_vector']),
            GinIndex(fields=['metadata']),
        ]
        ordering = ['-last_updated']
    
    def __str__(self):
        return f"Index: {self.title} ({self.content_type})"
    
    @classmethod
    def update_index(cls, content_type, object_id, title, content, metadata=None):
        """Update or create an index entry"""
        defaults = {
            'title': title,
            'content': content,
            'search_vector': cls._process_content(content),
            'metadata': metadata or {},
            'is_active': True,
        }
        
        obj, created = cls.objects.update_or_create(
            content_type=content_type,
            object_id=object_id,
            defaults=defaults
        )
        
        return obj, created
    
    @classmethod
    def _process_content(cls, content):
        """Process content for search indexing"""
        if not content:
            return ""
        
        # Basic processing - in production, this would be more sophisticated
        # with stemming, stop words, etc.
        processed = content.lower()
        # Remove extra whitespace
        processed = ' '.join(processed.split())
        
        return processed
    
    @classmethod
    def search(cls, query, content_types=None, filters=None):
        """Perform search on indexed content"""
        if not query:
            return cls.objects.none()
        
        queryset = cls.objects.filter(is_active=True)
        
        # Filter by content types if specified
        if content_types:
            queryset = queryset.filter(content_type__in=content_types)
        
        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if key == 'title_contains':
                    queryset = queryset.filter(title__icontains=value)
                elif key == 'metadata_contains':
                    queryset = queryset.filter(metadata__contains=value)
        
        # Perform full-text search
        search_query = PGSearchQuery(query)
        queryset = queryset.annotate(
            rank=SearchRank(models.F('search_vector'), search_query)
        ).filter(search_vector=search_query).order_by('-rank')
        
        return queryset


class SearchSuggestion(models.Model):
    """Store search suggestions and autocomplete data"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.CharField(
        max_length=200,
        help_text="Suggested search query"
    )
    frequency = models.PositiveIntegerField(
        default=1,
        help_text="How often this query has been searched"
    )
    search_type = models.CharField(
        max_length=20,
        choices=[
            ('GLOBAL', 'Global Search'),
            ('TUTOR', 'Tutor Search'),
            ('REQUIREMENT', 'Requirement Search'),
            ('MESSAGE', 'Message Search'),
            ('PAYMENT', 'Payment Search'),
        ],
        default='GLOBAL',
        help_text="Type of search this suggestion applies to"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this suggestion is active"
    )
    is_trending = models.BooleanField(
        default=False,
        help_text="Whether this is a trending search"
    )
    last_used = models.DateTimeField(
        auto_now=True,
        help_text="When this suggestion was last used"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Search Suggestion'
        verbose_name_plural = 'Search Suggestions'
        unique_together = ['query', 'search_type']
        indexes = [
            models.Index(fields=['query']),
            models.Index(fields=['search_type']),
            models.Index(fields=['frequency']),
            models.Index(fields=['is_trending']),
            models.Index(fields=['last_used']),
        ]
        ordering = ['-frequency', '-last_used']
    
    def __str__(self):
        return f"Suggestion: {self.query} ({self.frequency} uses)"
    
    @classmethod
    def add_suggestion(cls, query, search_type='GLOBAL'):
        """Add or update a search suggestion"""
        obj, created = cls.objects.get_or_create(
            query=query.lower(),
            search_type=search_type,
            defaults={'frequency': 1}
        )
        
        if not created:
            obj.frequency += 1
            obj.save(update_fields=['frequency', 'last_used'])
        
        return obj


class SearchAnalytics(models.Model):
    """Store aggregated search analytics data"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(
        help_text="Date for this analytics record"
    )
    search_type = models.CharField(
        max_length=20,
        choices=[
            ('GLOBAL', 'Global Search'),
            ('TUTOR', 'Tutor Search'),
            ('REQUIREMENT', 'Requirement Search'),
            ('MESSAGE', 'Message Search'),
            ('PAYMENT', 'Payment Search'),
        ],
        help_text="Type of search"
    )
    total_searches = models.PositiveIntegerField(
        default=0,
        help_text="Total number of searches"
    )
    unique_searchers = models.PositiveIntegerField(
        default=0,
        help_text="Number of unique searchers"
    )
    avg_results_per_search = models.FloatField(
        default=0.0,
        help_text="Average number of results per search"
    )
    avg_response_time_ms = models.FloatField(
        default=0.0,
        help_text="Average response time in milliseconds"
    )
    top_queries = models.JSONField(
        default=list,
        blank=True,
        help_text="Top search queries for this period"
    )
    zero_result_queries = models.JSONField(
        default=list,
        blank=True,
        help_text="Queries that returned no results"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Search Analytics'
        verbose_name_plural = 'Search Analytics'
        unique_together = ['date', 'search_type']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['search_type']),
            models.Index(fields=['total_searches']),
        ]
        ordering = ['-date', 'search_type']
    
    def __str__(self):
        return f"Analytics for {self.search_type} on {self.date}"
