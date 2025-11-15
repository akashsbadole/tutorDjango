from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from messaging.models import OnlineClass, ClassRecording


class Command(BaseCommand):
    help = 'Clean up old online classes and recordings'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Number of days to keep classes (default: 90)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Find old classes
        old_classes = OnlineClass.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['COMPLETED', 'CANCELLED']
        )
        
        # Find old recordings
        old_recordings = ClassRecording.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['AVAILABLE', 'EXPIRED']
        )
        
        class_count = old_classes.count()
        recording_count = old_recordings.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would delete {class_count} old classes")
            )
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would delete {recording_count} old recordings")
            )
            return
        
        # Delete old classes
        deleted_classes, _ = old_classes.delete()
        
        # Delete old recordings
        deleted_recordings, _ = old_recordings.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted_classes} old classes")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted_recordings} old recordings")
        )