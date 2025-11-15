from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.utils import timezone
from datetime import timedelta, date
import json
import csv
import os

from search.models import SearchQuery, SearchResult, SearchAnalytics, SearchFilter
from accounts.models import User


class Command(BaseCommand):
    help = 'Generate search analytics reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to analyze (default: 30)',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path for CSV report',
        )
        parser.add_argument(
            '--report-type',
            type=str,
            default='summary',
            choices=['summary', 'detailed', 'queries', 'filters', 'users'],
            help='Type of report to generate',
        )
        parser.add_argument(
            '--update-analytics',
            action='store_true',
            help='Update SearchAnalytics records with new data',
        )
        parser.add_argument(
            '--top-count',
            type=int,
            default=20,
            help='Number of top items to include in reports (default: 20)',
        )

    def handle(self, *args, **options):
        days = options.get('days')
        output_file = options.get('output')
        report_type = options.get('report_type')
        update_analytics = options.get('update_analytics')
        top_count = options.get('top_count')
        
        self.stdout.write(self.style.SUCCESS(f'Generating search analytics for the last {days} days...'))
        
        # Calculate date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days or 30)
        
        # Generate report based on type
        report_data = {}
        if report_type == 'summary':
            report_data = self.generate_summary_report(start_date, end_date)
        elif report_type == 'detailed':
            report_data = self.generate_detailed_report(start_date, end_date)
        elif report_type == 'queries':
            report_data = self.generate_queries_report(start_date, end_date, top_count)
        elif report_type == 'filters':
            report_data = self.generate_filters_report(start_date, end_date, top_count)
        elif report_type == 'users':
            report_data = self.generate_users_report(start_date, end_date, top_count)
        
        # Update analytics records if requested
        if update_analytics:
            self.update_analytics_records(start_date, end_date)
        
        # Output report
        if output_file:
            self.save_report_to_csv(report_data, output_file, report_type)
            self.stdout.write(self.style.SUCCESS(f'Report saved to {output_file}'))
        else:
            self.print_report(report_data, report_type)
        
        self.stdout.write(self.style.SUCCESS('Analytics generation completed'))

    def generate_summary_report(self, start_date, end_date):
        """Generate a summary report of search activity"""
        # Basic statistics
        total_searches = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).count()
        
        unique_searchers = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values('user').distinct().count()
        
        # Average results per search
        avg_results = SearchResult.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).aggregate(avg=models.Avg('result_count'))['avg'] or 0
        
        # Searches with no results
        no_result_count = SearchResult.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            result_count=0
        ).count()
        
        # Top search types
        search_types = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values('content_type__model').annotate(
            count=models.Count('id')
        ).order_by('-count')
        
        # Daily search trends
        daily_trends = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).extra(
            {'day': 'date(created_at)'}
        ).values('day').annotate(
            count=models.Count('id')
        ).order_by('day')
        
        return {
            'total_searches': total_searches,
            'unique_searchers': unique_searchers,
            'avg_results_per_search': round(avg_results, 2),
            'no_result_searches': no_result_count,
            'no_result_percentage': round((no_result_count / total_searches * 100), 2) if total_searches > 0 else 0,
            'search_types': list(search_types),
            'daily_trends': list(daily_trends),
        }

    def generate_detailed_report(self, start_date, end_date):
        """Generate a detailed report with more metrics"""
        summary = self.generate_summary_report(start_date, end_date)
        
        # Top queries
        top_queries = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            query__isnull=False
        ).values('query').annotate(
            count=models.Count('id'),
            avg_results=models.Avg('searchresult__result_count')
        ).order_by('-count')[:20]
        
        # Queries with no results
        no_result_queries = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            query__isnull=False
        ).filter(
            searchresult__result_count=0
        ).values('query').annotate(
            count=models.Count('id')
        ).order_by('-count')[:20]
        
        # Most active searchers
        top_searchers = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            user__isnull=False
        ).values('user__username', 'user__email').annotate(
            count=models.Count('id')
        ).order_by('-count')[:20]
        
        # Search result distribution
        result_distribution = SearchResult.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).extra(
            {'range': "CASE "
                    "WHEN result_count = 0 THEN 'No results' "
                    "WHEN result_count <= 5 THEN '1-5 results' "
                    "WHEN result_count <= 10 THEN '6-10 results' "
                    "WHEN result_count <= 20 THEN '11-20 results' "
                    "ELSE 'More than 20 results' END"}
        ).values('range').annotate(
            count=models.Count('id')
        ).order_by('range')
        
        summary.update({
            'top_queries': list(top_queries),
            'no_result_queries': list(no_result_queries),
            'top_searchers': list(top_searchers),
            'result_distribution': list(result_distribution),
        })
        
        return summary

    def generate_queries_report(self, start_date, end_date, top_count):
        """Generate a detailed report about search queries"""
        # Top queries
        top_queries = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            query__isnull=False
        ).values('query').annotate(
            count=models.Count('id'),
            unique_users=models.Count('user', distinct=True),
            avg_results=models.Avg('searchresult__result_count'),
            first_searched=models.Min('created_at'),
            last_searched=models.Max('created_at')
        ).order_by('-count')[:top_count]
        
        # Queries with improving results (over time)
        # This is complex and would require more detailed analysis
        
        # Query length distribution
        length_distribution = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            query__isnull=False
        ).extra(
            {'length': "LENGTH(query)"}
        ).extra(
            {'category': "CASE "
                       "WHEN LENGTH(query) <= 3 THEN 'Very short (1-3)' "
                       "WHEN LENGTH(query) <= 6 THEN 'Short (4-6)' "
                       "WHEN LENGTH(query) <= 10 THEN 'Medium (7-10)' "
                       "WHEN LENGTH(query) <= 15 THEN 'Long (11-15)' "
                       "ELSE 'Very long (15+)' END"}
        ).values('category').annotate(
            count=models.Count('id')
        ).order_by('category')
        
        return {
            'top_queries': list(top_queries),
            'length_distribution': list(length_distribution),
        }

    def generate_filters_report(self, start_date, end_date, top_count):
        """Generate a report about filter usage"""
        # Most used filters
        top_filters = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            filters__isnull=False
        ).values('filters').annotate(
            count=models.Count('id'),
            unique_users=models.Count('user', distinct=True)
        ).order_by('-count')[:top_count]
        
        # Filter usage by content type
        filters_by_type = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            filters__isnull=False
        ).values('content_type__model').annotate(
            with_filters=models.Count('id', filter=models.Q(filters__isnull=False)),
            without_filters=models.Count('id', filter=models.Q(filters__isnull=True)),
            total=models.Count('id')
        ).order_by('-total')
        
        # Saved filters usage
        saved_filters_usage = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            saved_filter__isnull=False
        ).values('saved_filter__name', 'saved_filter__user__username').annotate(
            usage_count=models.Count('id')
        ).order_by('-usage_count')[:top_count]
        
        return {
            'top_filters': list(top_filters),
            'filters_by_type': list(filters_by_type),
            'saved_filters_usage': list(saved_filters_usage),
        }

    def generate_users_report(self, start_date, end_date, top_count):
        """Generate a report about user search behavior"""
        # Most active searchers
        top_searchers = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            user__isnull=False
        ).values('user__username', 'user__email').annotate(
            search_count=models.Count('id'),
            unique_queries=models.Count('query', distinct=True),
            avg_results=models.Avg('searchresult__result_count'),
            first_search=models.Min('created_at'),
            last_search=models.Max('created_at')
        ).order_by('-search_count')[:top_count]
        
        # Users who save searches
        users_with_saved_searches = SearchFilter.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).values('user__username').annotate(
            saved_searches_count=models.Count('id')
        ).order_by('-saved_searches_count')[:top_count]
        
        # User search frequency distribution
        search_frequency = SearchQuery.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            user__isnull=False
        ).values('user').annotate(
            search_count=models.Count('id')
        ).extra(
            {'frequency': "CASE "
                         "WHEN COUNT(id) = 1 THEN 'One-time searcher' "
                         "WHEN COUNT(id) <= 5 THEN 'Occasional searcher (2-5)' "
                         "WHEN COUNT(id) <= 10 THEN 'Regular searcher (6-10)' "
                         "WHEN COUNT(id) <= 20 THEN 'Frequent searcher (11-20)' "
                         "ELSE 'Power searcher (20+)' END"}
        ).values('frequency').annotate(
            user_count=models.Count('user', distinct=True)
        ).order_by('user_count')
        
        return {
            'top_searchers': list(top_searchers),
            'users_with_saved_searches': list(users_with_saved_searches),
            'search_frequency': list(search_frequency),
        }

    def update_analytics_records(self, start_date, end_date):
        """Update SearchAnalytics records with new data"""
        self.stdout.write('Updating analytics records...')
        
        current_date = start_date
        while current_date <= end_date:
            # Get data for this date
            day_start = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.min.time()))
            day_end = day_start + timedelta(days=1)
            
            # Calculate statistics
            total_searches = SearchQuery.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            ).count()
            
            unique_searchers = SearchQuery.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            ).values('user').distinct().count()
            
            avg_results = SearchResult.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            ).aggregate(avg=models.Avg('result_count'))['avg'] or 0
            
            # Get top queries
            top_queries = list(SearchQuery.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end,
                query__isnull=False
            ).values('query').annotate(
                count=models.Count('id')
            ).order_by('-count')[:10])
            
            # Get queries with no results
            no_result_queries = list(SearchQuery.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end,
                query__isnull=False
            ).filter(
                searchresult__result_count=0
            ).values('query').annotate(
                count=models.Count('id')
            ).order_by('-count')[:10])
            
            # Get search type statistics
            search_type_stats = list(SearchQuery.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            ).values('content_type__model').annotate(
                count=models.Count('id')
            ).order_by('-count'))
            
            # Update or create analytics record
            analytics, created = SearchAnalytics.objects.update_or_create(
                date=current_date,
                defaults={
                    'total_searches': total_searches,
                    'unique_searchers': unique_searchers,
                    'avg_results_per_search': avg_results,
                    'top_queries': json.dumps({q['query']: q['count'] for q in top_queries}),
                    'no_result_queries': json.dumps({q['query']: q['count'] for q in no_result_queries}),
                    'search_type_stats': json.dumps({s['content_type__model']: s['count'] for s in search_type_stats}),
                }
            )
            
            if created:
                self.stdout.write(f'  Created analytics record for {current_date}')
            else:
                self.stdout.write(f'  Updated analytics record for {current_date}')
            
            current_date += timedelta(days=1)

    def save_report_to_csv(self, report_data, output_file, report_type):
        """Save report data to CSV file"""
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            if report_type == 'summary':
                writer.writerow(['Metric', 'Value'])
                writer.writerow(['Total Searches', report_data['total_searches']])
                writer.writerow(['Unique Searchers', report_data['unique_searchers']])
                writer.writerow(['Average Results per Search', report_data['avg_results_per_search']])
                writer.writerow(['No Result Searches', report_data['no_result_searches']])
                writer.writerow(['No Result Percentage', f"{report_data['no_result_percentage']}%"])
                
                writer.writerow([])
                writer.writerow(['Search Types'])
                writer.writerow(['Content Type', 'Count'])
                for item in report_data['search_types']:
                    writer.writerow([item['content_type__model'], item['count']])
                
                writer.writerow([])
                writer.writerow(['Daily Trends'])
                writer.writerow(['Date', 'Search Count'])
                for item in report_data['daily_trends']:
                    writer.writerow([item['day'], item['count']])
            
            elif report_type == 'queries':
                writer.writerow(['Top Queries'])
                writer.writerow(['Query', 'Count', 'Unique Users', 'Average Results', 'First Searched', 'Last Searched'])
                for item in report_data['top_queries']:
                    writer.writerow([
                        item['query'], item['count'], item['unique_users'],
                        item['avg_results'], item['first_searched'], item['last_searched']
                    ])
                
                writer.writerow([])
                writer.writerow(['Query Length Distribution'])
                writer.writerow(['Category', 'Count'])
                for item in report_data['length_distribution']:
                    writer.writerow([item['category'], item['count']])
            
            # Add more report types as needed

    def print_report(self, report_data, report_type):
        """Print report data to console"""
        if report_type == 'summary':
            self.stdout.write("=== SEARCH ANALYTICS SUMMARY ===")
            self.stdout.write(f"Total Searches: {report_data['total_searches']}")
            self.stdout.write(f"Unique Searchers: {report_data['unique_searchers']}")
            self.stdout.write(f"Average Results per Search: {report_data['avg_results_per_search']}")
            self.stdout.write(f"No Result Searches: {report_data['no_result_searches']}")
            self.stdout.write(f"No Result Percentage: {report_data['no_result_percentage']}%")
            
            self.stdout.write("\n=== SEARCH TYPES ===")
            for item in report_data['search_types']:
                self.stdout.write(f"{item['content_type__model']}: {item['count']}")
            
            self.stdout.write("\n=== DAILY TRENDS ===")
            for item in report_data['daily_trends']:
                self.stdout.write(f"{item['day']}: {item['count']} searches")
        
        elif report_type == 'queries':
            self.stdout.write("=== TOP QUERIES ===")
            for item in report_data['top_queries']:
                self.stdout.write(
                    f"{item['query']}: {item['count']} searches, "
                    f"{item['unique_users']} users, "
                    f"{item['avg_results']:.1f} avg results"
                )
            
            self.stdout.write("\n=== QUERY LENGTH DISTRIBUTION ===")
            for item in report_data['length_distribution']:
                self.stdout.write(f"{item['category']}: {item['count']} queries")
        
        # Add more report types as needed