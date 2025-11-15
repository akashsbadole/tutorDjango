from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from messaging.models import OnlineClass
from messaging.utils import sync_calendar_event

User = get_user_model()


class Command(BaseCommand):
    help = 'Sync online classes with user calendars'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look ahead for classes (default: 7)'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username to sync calendar for (optional)'
        )
        parser.add_argument(
            '--calendar-type',
            type=str,
            choices=['google', 'outlook'],
            default='google',
            help='Calendar type to sync with (default: google)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without actually syncing'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        username = options.get('user')
        calendar_type = options['calendar_type']
        dry_run = options['dry_run']
        
        # Get date range
        end_date = timezone.now() + timedelta(days=days)
        start_date = timezone.now()
        
        # Filter classes
        classes = OnlineClass.objects.filter(
            scheduled_start__gte=start_date,
            scheduled_start__lte=end_date,
            status__in=['SCHEDULED', 'IN_PROGRESS']
        ).select_related('host')
        
        if username:
            # Sync for specific user
            try:
                user = User.objects.get(username=username)
                user_classes = classes.filter(host=user)
                self._sync_user_classes(user, user_classes, calendar_type, dry_run)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User '{username}' not found")
                )
                return
        else:
            # Sync for all users
            users = User.objects.filter(
                id__in=classes.values_list('host_id', distinct=True)
            ).distinct()
            
            for user in users:
                user_classes = classes.filter(host=user)
                self._sync_user_classes(user, user_classes, calendar_type, dry_run)
    
    def _sync_user_classes(self, user, classes, calendar_type, dry_run):
        """Sync classes for a specific user"""
        if not classes:
            self.stdout.write(f"No upcoming classes for {user.username}")
            return
        
        self.stdout.write(
            self.style.SUCCESS(f"Syncing {len(classes)} classes for {user.username}")
        )
        
        synced_count = 0
        failed_count = 0
        
        for online_class in classes:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"DRY RUN: Would sync '{online_class.title}' to {calendar_type} calendar")
                )
                synced_count += 1
                continue
            
            # Sync with calendar
            result = sync_calendar_event(online_class, user, calendar_type)
            
            if result.get('success'):
                synced_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Synced '{online_class.title}' to {calendar_type} calendar")
                )
            else:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f"Failed to sync '{online_class.title}': {result.get('error')}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(f"Synced {synced_count} classes, {failed_count} failed")
        )