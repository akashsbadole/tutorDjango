from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction, models
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
import time

from search.models import SearchQuery, SearchResult, SearchIndex, SearchAnalytics, SearchSuggestion


class Command(BaseCommand):
    help = 'Optimize search performance and clean up old data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Run VACUUM on database tables (requires exclusive access)',
        )
        parser.add_argument(
            '--analyze',
            action='store_true',
            default=True,
            help='Run ANALYZE on database tables to update statistics',
        )
        parser.add_argument(
            '--cleanup-days',
            type=int,
            default=30,
            help='Number of days to keep search history (default: 30)',
        )
        parser.add_argument(
            '--cleanup-suggestions',
            action='store_true',
            help='Clean up unused search suggestions',
        )
        parser.add_argument(
            '--rebuild-cache',
            action='store_true',
            help='Rebuild search-related cache',
        )
        parser.add_argument(
            '--update-stats',
            action='store_true',
            default=True,
            help='Update search analytics statistics',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting search optimization...'))
        start_time = time.time()
        
        cleanup_days = options.get('cleanup_days')
        vacuum = options.get('vacuum')
        analyze = options.get('analyze')
        cleanup_suggestions = options.get('cleanup_suggestions')
        rebuild_cache = options.get('rebuild_cache')
        update_stats = options.get('update_stats')
        
        # Clean up old search queries
        if cleanup_days > 0:
            self.cleanup_old_queries(cleanup_days)
        
        # Clean up expired search results
        self.cleanup_expired_results()
        
        # Clean up search suggestions if requested
        if cleanup_suggestions:
            self.cleanup_suggestions()
        
        # Rebuild cache if requested
        if rebuild_cache:
            self.rebuild_cache()
        
        # Update analytics statistics if requested
        if update_stats:
            self.update_analytics_stats()
        
        # Run ANALYZE on tables if requested
        if analyze:
            self.analyze_tables()
        
        # Run VACUUM on tables if requested
        if vacuum:
            self.vacuum_tables()
        
        # Optimize search indexes
        self.optimize_search_indexes()
        
        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f'Search optimization completed in {elapsed_time:.2f} seconds'))

    def cleanup_old_queries(self, days):
        """Clean up old search queries"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        with transaction.atomic():
            # Count queries to be deleted
            count = SearchQuery.objects.filter(created_at__lt=cutoff_date).count()
            
            if count > 0:
                # Delete old queries
                SearchQuery.objects.filter(created_at__lt=cutoff_date).delete()
                self.stdout.write(self.style.SUCCESS(f'Cleaned up {count} old search queries (older than {days} days)'))
            else:
                self.stdout.write('No old search queries to clean up')

    def cleanup_expired_results(self):
        """Clean up expired search results"""
        with transaction.atomic():
            # Count expired results
            count = SearchResult.objects.filter(expires_at__lt=timezone.now()).count()
            
            if count > 0:
                # Delete expired results
                SearchResult.objects.filter(expires_at__lt=timezone.now()).delete()
                self.stdout.write(self.style.SUCCESS(f'Cleaned up {count} expired search results'))
            else:
                self.stdout.write('No expired search results to clean up')

    def cleanup_suggestions(self):
        """Clean up unused search suggestions"""
        with transaction.atomic():
            # Get suggestions that haven't been used recently
            cutoff_date = timezone.now() - timedelta(days=90)
            unused_suggestions = SearchSuggestion.objects.filter(
                last_used__lt=cutoff_date,
                use_count__lt=5
            )
            
            count = unused_suggestions.count()
            if count > 0:
                unused_suggestions.delete()
                self.stdout.write(self.style.SUCCESS(f'Cleaned up {count} unused search suggestions'))
            else:
                self.stdout.write('No unused search suggestions to clean up')

    def rebuild_cache(self):
        """Rebuild search-related cache"""
        self.stdout.write('Rebuilding search cache...')
        
        # Clear existing cache keys
        cache_keys_to_clear = [
            'search_trending_queries',
            'search_popular_filters',
            'search_facets_tutors',
            'search_facets_requirements',
            'search_suggestions_popular',
        ]
        
        for key in cache_keys_to_clear:
            cache.delete(key)
        
        # Pre-populate some cache data
        self.prepopulate_popular_queries()
        self.prepopulate_popular_filters()
        
        self.stdout.write(self.style.SUCCESS('Search cache rebuilt'))

    def prepopulate_popular_queries(self):
        """Pre-populate cache with popular queries"""
        # Get recent popular queries
        recent_queries = SearchQuery.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        ).values('query').annotate(
            count=models.Count('id')
        ).order_by('-count')[:20]
        
        popular_queries = [q['query'] for q in recent_queries if q['query']]
        cache.set('search_trending_queries', popular_queries, 3600)  # 1 hour

    def prepopulate_popular_filters(self):
        """Pre-populate cache with popular filters"""
        # Get popular tutor filters
        tutor_filters = SearchQuery.objects.filter(
            content_type__model='user',
            filters__isnull=False
        ).values('filters').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10]
        
        # Get popular requirement filters
        req_filters = SearchQuery.objects.filter(
            content_type__model='requirement',
            filters__isnull=False
        ).values('filters').annotate(
            count=models.Count('id')
        ).order_by('-count')[:10]
        
        cache.set('search_popular_filters_tutors', list(tutor_filters), 3600)
        cache.set('search_popular_filters_requirements', list(req_filters), 3600)

    def update_analytics_stats(self):
        """Update search analytics statistics"""
        self.stdout.write('Updating search analytics statistics...')
        
        # Calculate statistics for the last 30 days
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Update or create analytics records for missing dates
        current_date = start_date
        while current_date <= end_date:
            SearchAnalytics.objects.get_or_create(
                date=current_date,
                defaults={
                    'total_searches': 0,
                    'unique_searchers': 0,
                    'avg_results_per_search': 0,
                    'top_queries': '{}',
                    'no_result_queries': '{}',
                    'search_type_stats': '{}',
                }
            )
            current_date += timedelta(days=1)
        
        # Calculate aggregated statistics
        total_searches = SearchQuery.objects.filter(
            created_at__date__gte=start_date
        ).count()
        
        unique_searchers = SearchQuery.objects.filter(
            created_at__date__gte=start_date
        ).values('user').distinct().count()
        
        avg_results = SearchResult.objects.filter(
            created_at__date__gte=start_date
        ).aggregate(avg=models.Avg('result_count'))['avg'] or 0
        
        self.stdout.write(self.style.SUCCESS(
            f'Updated analytics: {total_searches} searches, '
            f'{unique_searchers} unique searchers, '
            f'{avg_results:.1f} avg results'
        ))

    def analyze_tables(self):
        """Run ANALYZE on search-related tables"""
        self.stdout.write('Running ANALYZE on search tables...')
        
        tables = [
            'search_searchquery',
            'search_searchresult',
            'search_searchindex',
            'search_searchfilter',
            'search_searchsuggestion',
            'search_searchanalytics',
        ]
        
        with connection.cursor() as cursor:
            for table in tables:
                try:
                    cursor.execute(f'ANALYZE {table};')
                    self.stdout.write(f'  ANALYZE completed for {table}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error analyzing {table}: {str(e)}'))

    def vacuum_tables(self):
        """Run VACUUM on search-related tables"""
        self.stdout.write('Running VACUUM on search tables...')
        self.stdout.write(self.style.WARNING('Note: VACUUM requires exclusive access to tables'))
        
        tables = [
            'search_searchquery',
            'search_searchresult',
            'search_searchindex',
            'search_searchfilter',
            'search_searchsuggestion',
            'search_searchanalytics',
        ]
        
        with connection.cursor() as cursor:
            for table in tables:
                try:
                    cursor.execute(f'VACUUM ANALYZE {table};')
                    self.stdout.write(f'  VACUUM completed for {table}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error vacuuming {table}: {str(e)}'))

    def optimize_search_indexes(self):
        """Optimize search indexes"""
        self.stdout.write('Optimizing search indexes...')
        
        # Rebuild search suggestions based on recent queries
        self.rebuild_search_suggestions()
        
        # Update search index statistics
        self.update_index_statistics()
        
        self.stdout.write(self.style.SUCCESS('Search indexes optimized'))

    def rebuild_search_suggestions(self):
        """Rebuild search suggestions based on recent queries"""
        # Clear existing suggestions
        SearchSuggestion.objects.all().delete()
        
        # Get recent queries
        recent_queries = SearchQuery.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=90)
        ).values('query').annotate(
            count=models.Count('id'),
            last_used=models.Max('created_at')
        ).filter(
            query__isnull=False,
            query__len__gt=2  # Only include queries longer than 2 characters
        ).order_by('-count')[:500]
        
        # Create new suggestions
        suggestions = []
        for query_data in recent_queries:
            suggestions.append(SearchSuggestion(
                query=query_data['query'],
                frequency=query_data['count'],
                last_used=query_data['last_used']
            ))
        
        if suggestions:
            SearchSuggestion.objects.bulk_create(suggestions)
            self.stdout.write(self.style.SUCCESS(f'Created {len(suggestions)} search suggestions'))

    def update_index_statistics(self):
        """Update search index statistics"""
        # Count indexed objects by type
        from django.contrib.contenttypes.models import ContentType
        
        content_types = ContentType.objects.filter(
            model__in=['user', 'requirement', 'message', 'payment']
        )
        
        for ct in content_types:
            count = SearchIndex.objects.filter(content_type=ct).count()
            self.stdout.write(f'  Indexed {ct.model}: {count} objects')