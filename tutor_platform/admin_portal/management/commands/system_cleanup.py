"""
Django Tutor Platform Admin Portal System Cleanup Command

This management command performs system cleanup tasks.
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.conf import settings
from django.core.cache import cache

from accounts.models import User
from messaging.models import Message, Conversation
from notifications.models import Notification
from admin_portal.models import AdminActivityLog, AdminSession, DataExport


class Command(BaseCommand):
    help = 'Perform system cleanup tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
            default=False
        )
        parser.add_argument(
            '--days',
            type=int,
            help='Number of days to keep records (default: 90)',
            default=90
        )
        parser.add_argument(
            '--cleanup-logs',
            action='store_true',
            help='Clean up admin activity logs',
            default=False
        )
        parser.add_argument(
            '--cleanup-sessions',
            action='store_true',
            help='Clean up expired admin sessions',
            default=False
        )
        parser.add_argument(
            '--cleanup-exports',
            action='store_true',
            help='Clean up expired data exports',
            default=False
        )
        parser.add_argument(
            '--cleanup-notifications',
            action='store_true',
            help='Clean up old notifications',
            default=False
        )
        parser.add_argument(
            '--cleanup-messages',
            action='store_true',
            help='Clean up old messages',
            default=False
        )
        parser.add_argument(
            '--cleanup-cache',
            action='store_true',
            help='Clear application cache',
            default=False
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all cleanup tasks',
            default=False
        )
    
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.days = options['days']
        self.cutoff_date = now() - timedelta(days=self.days)
        
        self.stdout.write(self.style.SUCCESS('Starting system cleanup...'))
        self.stdout.write(f"Cutoff date: {self.cutoff_date}")
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be deleted'))
        
        cleanup_stats = {
            'logs': 0,
            'sessions': 0,
            'exports': 0,
            'notifications': 0,
            'messages': 0,
        }
        
        try:
            # Run cleanup tasks
            if options['all'] or options['cleanup_logs']:
                cleanup_stats['logs'] = self._cleanup_activity_logs()
            
            if options['all'] or options['cleanup_sessions']:
                cleanup_stats['sessions'] = self._cleanup_sessions()
            
            if options['all'] or options['cleanup_exports']:
                cleanup_stats['exports'] = self._cleanup_exports()
            
            if options['all'] or options['cleanup_notifications']:
                cleanup_stats['notifications'] = self._cleanup_notifications()
            
            if options['all'] or options['cleanup_messages']:
                cleanup_stats['messages'] = self._cleanup_messages()
            
            if options['all'] or options['cleanup_cache']:
                self._cleanup_cache()
            
            # Print summary
            self._print_summary(cleanup_stats)
            
            self.stdout.write(
                self.style.SUCCESS('System cleanup completed successfully')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Cleanup failed: {str(e)}')
            )
    
    def _cleanup_activity_logs(self):
        """Clean up old admin activity logs"""
        self.stdout.write("Cleaning up admin activity logs...")
        
        queryset = AdminActivityLog.objects.filter(
            timestamp__lt=self.cutoff_date
        )
        count = queryset.count()
        
        if self.dry_run:
            self.stdout.write(f"  -> Would delete {count} activity logs")
        else:
            queryset.delete()
            self.stdout.write(f"  -> Deleted {count} activity logs")
        
        return count
    
    def _cleanup_sessions(self):
        """Clean up expired admin sessions"""
        self.stdout.write("Cleaning up admin sessions...")
        
        # Clean up expired sessions
        expired_sessions = AdminSession.objects.filter(
            expires_at__lt=now()
        )
        expired_count = expired_sessions.count()
        
        if self.dry_run:
            self.stdout.write(f"  -> Would delete {expired_count} expired sessions")
        else:
            expired_sessions.delete()
            self.stdout.write(f"  -> Deleted {expired_count} expired sessions")
        
        # Clean up old inactive sessions
        inactive_sessions = AdminSession.objects.filter(
            last_activity__lt=self.cutoff_date,
            is_active=False
        )
        inactive_count = inactive_sessions.count()
        
        if self.dry_run:
            self.stdout.write(f"  -> Would delete {inactive_count} inactive sessions")
        else:
            inactive_sessions.delete()
            self.stdout.write(f"  -> Deleted {inactive_count} inactive sessions")
        
        return expired_count + inactive_count
    
    def _cleanup_exports(self):
        """Clean up expired data exports"""
        self.stdout.write("Cleaning up data exports...")
        
        # Clean up expired exports
        expired_exports = DataExport.objects.filter(
            expires_at__lt=now()
        )
        expired_count = expired_exports.count()
        
        if self.dry_run:
            self.stdout.write(f"  -> Would delete {expired_count} expired exports")
        else:
            # Delete files before deleting records
            for export in expired_exports:
                if export.file_path:
                    try:
                        import os
                        if os.path.exists(export.file_path):
                            os.remove(export.file_path)
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  -> Could not delete file {export.file_path}: {str(e)}"
                            )
                        )
            
            expired_exports.delete()
            self.stdout.write(f"  -> Deleted {expired_count} expired exports")
        
        # Clean up old failed exports
        failed_exports = DataExport.objects.filter(
            status='FAILED',
            created_at__lt=self.cutoff_date
        )
        failed_count = failed_exports.count()
        
        if self.dry_run:
            self.stdout.write(f"  -> Would delete {failed_count} failed exports")
        else:
            failed_exports.delete()
            self.stdout.write(f"  -> Deleted {failed_count} failed exports")
        
        return expired_count + failed_count
    
    def _cleanup_notifications(self):
        """Clean up old notifications"""
        self.stdout.write("Cleaning up notifications...")
        
        # Clean up read notifications older than cutoff
        read_notifications = Notification.objects.filter(
            is_read=True,
            created_at__lt=self.cutoff_date
        )
        read_count = read_notifications.count()
        
        if self.dry_run:
            self.stdout.write(f"  -> Would delete {read_count} read notifications")
        else:
            read_notifications.delete()
            self.stdout.write(f"  -> Deleted {read_count} read notifications")
        
        # Clean up very old unread notifications (older than 1 year)
        year_ago = now() - timedelta(days=365)
        old_notifications = Notification.objects.filter(
            is_read=False,
            created_at__lt=year_ago
        )
        old_count = old_notifications.count()
        
        if self.dry_run:
            self.stdout.write(f"  -> Would delete {old_count} old unread notifications")
        else:
            old_notifications.delete()
            self.stdout.write(f"  -> Deleted {old_count} old unread notifications")
        
        return read_count + old_count
    
    def _cleanup_messages(self):
        """Clean up old messages"""
        self.stdout.write("Cleaning up messages...")
        
        # Clean up messages from deleted conversations
        orphaned_messages = Message.objects.filter(
            conversation__isnull=True
        )
        orphaned_count = orphaned_messages.count()
        
        if self.dry_run:
            self.stdout.write(f"  -> Would delete {orphaned_count} orphaned messages")
        else:
            orphaned_messages.delete()
            self.stdout.write(f"  -> Deleted {orphaned_count} orphaned messages")
        
        # Clean up very old messages (older than 2 years)
        two_years_ago = now() - timedelta(days=730)
        old_messages = Message.objects.filter(
            created_at__lt=two_years_ago
        )
        old_count = old_messages.count()
        
        if self.dry_run:
            self.stdout.write(f"  -> Would delete {old_count} old messages")
        else:
            old_messages.delete()
            self.stdout.write(f"  -> Deleted {old_count} old messages")
        
        return orphaned_count + old_count
    
    def _cleanup_cache(self):
        """Clear application cache"""
        self.stdout.write("Clearing application cache...")
        
        if self.dry_run:
            self.stdout.write("  -> Would clear application cache")
        else:
            try:
                cache.clear()
                self.stdout.write("  -> Application cache cleared")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  -> Failed to clear cache: {str(e)}")
                )
    
    def _print_summary(self, stats):
        """Print cleanup summary"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("CLEANUP SUMMARY")
        self.stdout.write("="*50)
        self.stdout.write(f"Admin activity logs: {stats['logs']}")
        self.stdout.write(f"Admin sessions: {stats['sessions']}")
        self.stdout.write(f"Data exports: {stats['exports']}")
        self.stdout.write(f"Notifications: {stats['notifications']}")
        self.stdout.write(f"Messages: {stats['messages']}")
        self.stdout.write(f"Total records deleted: {sum(stats.values())}")
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("\nDRY RUN MODE - No data was actually deleted")
            )
        
        self.stdout.write("="*50)