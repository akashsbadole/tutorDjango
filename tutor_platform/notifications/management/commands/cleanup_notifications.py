from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications.models import Notification, NotificationPreference


class Command(BaseCommand):
    help = 'Clean up expired and old notifications'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Provide verbose output'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        # Clean up expired notifications
        expired_count = self.cleanup_expired_notifications(dry_run, verbose)
        
        # Clean up old read notifications based on user preferences
        old_read_count = self.cleanup_old_read_notifications(dry_run, verbose)
        
        # Summary
        total_count = expired_count + old_read_count
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {total_count} notifications '
                    f'({expired_count} expired, {old_read_count} old read)'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Cleaned up {total_count} notifications '
                    f'({expired_count} expired, {old_read_count} old read)'
                )
            )
    
    def cleanup_expired_notifications(self, dry_run=False, verbose=False):
        """Clean up expired notifications"""
        expired_notifications = Notification.objects.filter(
            expires_at__lt=timezone.now()
        )
        
        count = expired_notifications.count()
        
        if count > 0:
            if verbose:
                self.stdout.write(f'Found {count} expired notifications')
                if dry_run:
                    for notification in expired_notifications:
                        self.stdout.write(f'  - {notification.title} (expired: {notification.expires_at})')
            
            if not dry_run:
                expired_notifications.delete()
                if verbose:
                    self.stdout.write(self.style.SUCCESS(f'Deleted {count} expired notifications'))
        
        return count
    
    def cleanup_old_read_notifications(self, dry_run=False, verbose=False):
        """Clean up old read notifications based on user preferences"""
        deleted_count = 0
        
        for preference in NotificationPreference.objects.filter(auto_delete_read=True):
            cutoff_date = timezone.now() - timezone.timedelta(days=preference.auto_delete_days)
            
            old_notifications = Notification.objects.filter(
                recipient=preference.user,
                is_read=True,
                read_at__lt=cutoff_date
            )
            
            count = old_notifications.count()
            
            if count > 0:
                if verbose:
                    self.stdout.write(
                        f'Found {count} old read notifications for {preference.user.username} '
                        f'(older than {preference.auto_delete_days} days)'
                    )
                    if dry_run:
                        for notification in old_notifications:
                            self.stdout.write(f'  - {notification.title} (read: {notification.read_at})')
                
                if not dry_run:
                    old_notifications.delete()
                    if verbose:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'Deleted {count} old read notifications for {preference.user.username}'
                            )
                        )
                
                deleted_count += count
        
        return deleted_count