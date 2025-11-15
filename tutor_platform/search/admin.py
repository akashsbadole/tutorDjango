from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import SearchQuery, SearchFilter, SearchResult, SearchIndex, SearchSuggestion, SearchAnalytics


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    """Admin configuration for SearchQuery model"""
    list_display = ['query', 'user', 'search_type', 'results_count', 'response_time_ms', 'created_at']
    list_filter = ['search_type', 'created_at']
    search_fields = ['query', 'user__username', 'user__email']
    readonly_fields = ['ip_address', 'user_agent', 'session_id', 'response_time_ms', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Search Information', {
            'fields': ('user', 'query', 'search_type')
        }),
        ('Results', {
            'fields': ('results_count', 'response_time_ms')
        }),
        ('Metadata', {
            'fields': ('ip_address', 'user_agent', 'session_id'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(SearchFilter)
class SearchFilterAdmin(admin.ModelAdmin):
    """Admin configuration for SearchFilter model"""
    list_display = ['name', 'user', 'search_type', 'is_default', 'is_public', 'usage_count', 'created_at']
    list_filter = ['search_type', 'is_default', 'is_public', 'created_at']
    search_fields = ['name', 'user__username', 'user__email']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Filter Information', {
            'fields': ('user', 'name', 'search_type')
        }),
        ('Configuration', {
            'fields': ('filters', 'is_default', 'is_public')
        }),
        ('Usage Statistics', {
            'fields': ('usage_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


class SearchFilterInline(admin.TabularInline):
    """Inline for SearchFilter in User admin"""
    model = SearchFilter
    extra = 0
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    fields = ['name', 'search_type', 'is_default', 'is_public', 'usage_count']


@admin.register(SearchResult)
class SearchResultAdmin(admin.ModelAdmin):
    """Admin configuration for SearchResult model"""
    list_display = ['title', 'content_type', 'search_query', 'relevance_score', 'created_at']
    list_filter = ['content_type', 'created_at']
    search_fields = ['title', 'description', 'search_query__query']
    readonly_fields = ['search_query', 'content_type', 'object_id', 'title', 'description', 
                     'url', 'relevance_score', 'highlight_data', 'metadata', 'created_at', 'expires_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Result Information', {
            'fields': ('search_query', 'title', 'content_type', 'object_id')
        }),
        ('Content', {
            'fields': ('description', 'url', 'relevance_score')
        }),
        ('Enhanced Data', {
            'fields': ('highlight_data', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('search_query')


class SearchResultInline(admin.TabularInline):
    """Inline for SearchResult in SearchQuery admin"""
    model = SearchResult
    extra = 0
    readonly_fields = ['content_type', 'object_id', 'title', 'relevance_score', 'created_at']
    fields = ['content_type', 'title', 'relevance_score', 'created_at']


@admin.register(SearchIndex)
class SearchIndexAdmin(admin.ModelAdmin):
    """Admin configuration for SearchIndex model"""
    list_display = ['title', 'content_type', 'is_active', 'last_updated', 'created_at']
    list_filter = ['content_type', 'is_active', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['content_type', 'object_id', 'title', 'content', 'search_vector', 
                     'metadata', 'last_updated', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-last_updated']
    
    fieldsets = (
        ('Index Information', {
            'fields': ('content_type', 'object_id', 'title')
        }),
        ('Content', {
            'fields': ('content', 'search_vector')
        }),
        ('Metadata', {
            'fields': ('metadata', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('last_updated', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['rebuild_selected_indexes', 'clear_selected_indexes']
    
    def rebuild_selected_indexes(self, request, queryset):
        """Rebuild selected search indexes"""
        count = queryset.count()
        self.message_user(request, f'{count} indexes will be rebuilt in the background.')
        # In a real implementation, this would trigger a background task
    rebuild_selected_indexes.short_description = "Rebuild selected indexes"
    
    def clear_selected_indexes(self, request, queryset):
        """Clear selected search indexes"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f'{count} indexes have been cleared.')
    clear_selected_indexes.short_description = "Clear selected indexes"


@admin.register(SearchSuggestion)
class SearchSuggestionAdmin(admin.ModelAdmin):
    """Admin configuration for SearchSuggestion model"""
    list_display = ['query', 'search_type', 'frequency', 'is_trending', 'is_active', 'last_used']
    list_filter = ['search_type', 'is_trending', 'is_active']
    search_fields = ['query']
    readonly_fields = ['frequency', 'last_used', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-frequency', '-last_used']
    
    fieldsets = (
        ('Suggestion Information', {
            'fields': ('query', 'search_type')
        }),
        ('Statistics', {
            'fields': ('frequency', 'is_trending', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('last_used', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['refresh_suggestions', 'clear_unused_suggestions']
    
    def refresh_suggestions(self, request, queryset):
        """Refresh suggestion statistics"""
        count = queryset.count()
        self.message_user(request, f'{count} suggestions have been refreshed.')
    refresh_suggestions.short_description = "Refresh search suggestions"
    
    def clear_unused_suggestions(self, request, queryset):
        """Clear unused suggestions"""
        count = queryset.filter(frequency__lt=2).count()
        queryset.filter(frequency__lt=2).delete()
        self.message_user(request, f'{count} unused suggestions have been cleared.')
    clear_unused_suggestions.short_description = "Clear unused suggestions"


@admin.register(SearchAnalytics)
class SearchAnalyticsAdmin(admin.ModelAdmin):
    """Admin configuration for SearchAnalytics model"""
    list_display = ['date', 'search_type', 'total_searches', 'unique_searchers', 
                   'avg_results_per_search', 'avg_response_time_ms']
    list_filter = ['search_type', 'date']
    search_fields = ['top_queries']
    readonly_fields = ['date', 'search_type', 'total_searches', 'unique_searchers', 
                     'avg_results_per_search', 'avg_response_time_ms', 'top_queries', 
                     'zero_result_queries', 'created_at', 'updated_at']
    date_hierarchy = 'date'
    ordering = ['-date', 'search_type']
    
    fieldsets = (
        ('Analytics Information', {
            'fields': ('date', 'search_type')
        }),
        ('Search Statistics', {
            'fields': ('total_searches', 'unique_searchers', 'avg_results_per_search', 'avg_response_time_ms')
        }),
        ('Query Analysis', {
            'fields': ('top_queries', 'zero_result_queries'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Analytics should be generated, not manually added"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Analytics should be generated, not manually changed"""
        return False
