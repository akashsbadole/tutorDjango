from django.core.management.base import BaseCommand, CommandError
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import time

from accounts.models import User, TutorProfile
from requirements.models import Requirement
from messaging.models import Message
from paymentsdetails.models import Payment
from search.models import SearchIndex, SearchResult
from search.utils import DatabaseSearchBackend, ElasticsearchBackend, HybridSearchBackend


class Command(BaseCommand):
    help = 'Rebuild search index for all content types'

    def add_arguments(self, parser):
        parser.add_argument(
            '--models',
            type=str,
            help='Comma-separated list of models to index (e.g., "User,Requirement,Message")',
        )
        parser.add_argument(
            '--backend',
            type=str,
            default='hybrid',
            choices=['database', 'elasticsearch', 'hybrid'],
            help='Search backend to use for indexing',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of objects to process in each batch',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild even if index is recent',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Remove stale index entries before rebuilding',
        )

    def handle(self, *args, **options):
        models_to_index = self.get_models_to_index(options.get('models'))
        backend_type = options.get('backend')
        batch_size = options.get('batch_size')
        force = options.get('force')
        cleanup = options.get('cleanup')

        self.stdout.write(self.style.SUCCESS(f'Starting search index rebuild using {backend_type} backend'))
        
        # Initialize search backend
        if backend_type == 'database':
            backend = DatabaseSearchBackend()
        elif backend_type == 'elasticsearch':
            backend = ElasticsearchBackend()
        else:
            backend = HybridSearchBackend()

        # Check if index rebuild is needed
        if not force and not self.should_rebuild_index():
            self.stdout.write(self.style.WARNING('Index is recent. Use --force to rebuild anyway.'))
            return

        # Clean up stale entries if requested
        if cleanup:
            self.cleanup_stale_entries()

        total_indexed = 0
        start_time = time.time()

        for model in models_to_index:
            self.stdout.write(f'Indexing {model.__name__}...')
            
            # Get content type for this model
            try:
                content_type = ContentType.objects.get_for_model(model)
            except ContentType.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Content type not found for {model.__name__}'))
                continue

            # Count total objects
            total_objects = model.objects.count()
            self.stdout.write(f'Found {total_objects} {model.__name__} objects to index')

            if total_objects == 0:
                continue

            # Process in batches
            indexed_count = 0
            for offset in range(0, total_objects, batch_size):
                batch = model.objects.all()[offset:offset + batch_size]
                
                with transaction.atomic():
                    for obj in batch:
                        try:
                            # Index the object
                            backend.index_object(obj, content_type)
                            indexed_count += 1
                            
                            # Update progress
                            if indexed_count % 100 == 0:
                                progress = (indexed_count / total_objects) * 100
                                self.stdout.write(f'  Progress: {indexed_count}/{total_objects} ({progress:.1f}%)')
                        
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'Error indexing {model.__name__} {obj.id}: {str(e)}'))

            total_indexed += indexed_count
            self.stdout.write(self.style.SUCCESS(f'Indexed {indexed_count} {model.__name__} objects'))

        # Optimize the index if backend supports it
        if hasattr(backend, 'optimize_index'):
            self.stdout.write('Optimizing search index...')
            backend.optimize_index()

        # Calculate statistics
        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f'Index rebuild completed in {elapsed_time:.2f} seconds'))
        self.stdout.write(self.style.SUCCESS(f'Total objects indexed: {total_indexed}'))
        
        # Update index metadata
        self.update_index_metadata(backend_type, total_indexed, elapsed_time)

    def get_models_to_index(self, models_string):
        """Get list of models to index based on input string"""
        if not models_string:
            return [User, TutorProfile, Requirement, Message, Payment]
        
        model_names = [name.strip() for name in models_string.split(',')]
        available_models = {
            'User': User,
            'TutorProfile': TutorProfile,
            'Requirement': Requirement,
            'Message': Message,
            'Payment': Payment,
        }
        
        models = []
        for name in model_names:
            if name in available_models:
                models.append(available_models[name])
            else:
                self.stdout.write(self.style.WARNING(f'Unknown model: {name}'))
        
        return models if models else list(available_models.values())

    def should_rebuild_index(self):
        """Check if index rebuild is needed based on last update time"""
        try:
            last_index = SearchIndex.objects.latest('updated_at')
            # Rebuild if index is older than 24 hours
            return last_index.updated_at < timezone.now() - timedelta(hours=24)
        except SearchIndex.DoesNotExist:
            return True

    def cleanup_stale_entries(self):
        """Remove stale search index entries"""
        self.stdout.write('Cleaning up stale search index entries...')
        
        # Remove entries for deleted objects
        deleted_count = 0
        
        # Check Users
        user_content_type = ContentType.objects.get_for_model(User)
        deleted_count += SearchIndex.objects.filter(
            content_type=user_content_type
        ).exclude(
            object_id__in=User.objects.values_list('id', flat=True)
        ).delete()[0]
        
        # Check Requirements
        req_content_type = ContentType.objects.get_for_model(Requirement)
        deleted_count += SearchIndex.objects.filter(
            content_type=req_content_type
        ).exclude(
            object_id__in=Requirement.objects.values_list('id', flat=True)
        ).delete()[0]
        
        # Check Messages
        msg_content_type = ContentType.objects.get_for_model(Message)
        deleted_count += SearchIndex.objects.filter(
            content_type=msg_content_type
        ).exclude(
            object_id__in=Message.objects.values_list('id', flat=True)
        ).delete()[0]
        
        # Check Payments
        pay_content_type = ContentType.objects.get_for_model(Payment)
        deleted_count += SearchIndex.objects.filter(
            content_type=pay_content_type
        ).exclude(
            object_id__in=Payment.objects.values_list('id', flat=True)
        ).delete()[0]
        
        # Check TutorProfiles
        tutor_content_type = ContentType.objects.get_for_model(TutorProfile)
        deleted_count += SearchIndex.objects.filter(
            content_type=tutor_content_type
        ).exclude(
            object_id__in=TutorProfile.objects.values_list('id', flat=True)
        ).delete()[0]
        
        # Clean up expired search results
        expired_count = SearchResult.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]
        
        self.stdout.write(self.style.SUCCESS(f'Cleaned up {deleted_count} stale index entries and {expired_count} expired results'))

    def update_index_metadata(self, backend_type, total_indexed, elapsed_time):
        """Update metadata about the search index"""
        # Create or update analytics record
        from search.models import SearchAnalytics
        
        today = timezone.now().date()
        analytics, created = SearchAnalytics.objects.get_or_create(
            date=today,
            defaults={
                'total_searches': 0,
                'unique_searchers': 0,
                'avg_results_per_search': 0,
                'top_queries': '{}',
                'no_result_queries': '{}',
                'search_type_stats': '{}',
            }
        )
        
        # Update index statistics
        index_stats = {
            'backend': backend_type,
            'total_indexed': total_indexed,
            'rebuild_time': elapsed_time,
            'last_rebuild': timezone.now().isoformat(),
        }
        
        # Store in a separate model or as part of analytics
        # For now, we'll just log it
        self.stdout.write(f'Index statistics: {index_stats}')