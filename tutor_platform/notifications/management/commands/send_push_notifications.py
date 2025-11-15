from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from tutor_platform.notifications.models import PushMessage, PushDevice
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send pending push notifications to devices'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of push notifications to process in one run'
        )
        parser.add_argument(
            '--device-type',
            type=str,
            choices=['IOS', 'ANDROID', 'WEB'],
            help='Process only specific device type'
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Also process push notifications that have failed and can be retried'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Provide verbose output'
        )
    
    def handle(self, *args, **options):
        limit = options['limit']
        device_type = options.get('device_type')
        retry_failed = options['retry_failed']
        verbose = options['verbose']
        
        # Get push messages to process
        push_messages = PushMessage.objects.filter(
            status=PushMessage.Status.PENDING
        )
        
        if device_type:
            push_messages = push_messages.filter(
                device__device_type=device_type
            )
        
        if retry_failed:
            # Add failed messages that can be retried
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(hours=1)
            failed_messages = PushMessage.objects.filter(
                status=PushMessage.Status.FAILED,
                failed_at__gte=cutoff,
                retry_count__lt=3
            )
            
            if device_type:
                failed_messages = failed_messages.filter(
                    device__device_type=device_type
                )
            
            push_messages = push_messages | failed_messages
        
        push_messages = push_messages.order_by('created_at')[:limit]
        
        if not push_messages.exists():
            if verbose:
                self.stdout.write(self.style.WARNING('No push notifications to send'))
            return
        
        processed_count = 0
        success_count = 0
        failed_count = 0
        
        self.stdout.write(f'Processing {push_messages.count()} push notifications...')
        
        for push_message in push_messages:
            with transaction.atomic():
                try:
                    # Update status to processing
                    push_message.status = PushMessage.Status.SENT
                    push_message.sent_at = timezone.now()
                    push_message.save(update_fields=['status', 'sent_at'])
                    
                    # Here you would integrate with actual push notification service
                    # For now, we'll simulate the send and mark as delivered
                    
                    # Create delivery record
                    from tutor_platform.notifications.models import NotificationDelivery
                    NotificationDelivery.objects.create(
                        notification=push_message.notification,
                        channel='PUSH',
                        status='DELIVERED',
                        recipient_address=push_message.device.device_token,
                        sent_at=timezone.now(),
                        delivered_at=timezone.now(),
                        delivery_provider='MockProvider'
                    )
                    
                    # Update message status to delivered
                    push_message.status = PushMessage.Status.DELIVERED
                    push_message.delivered_at = timezone.now()
                    push_message.save(update_fields=['status', 'delivered_at'])
                    
                    # Update device last used time
                    push_message.device.last_used_at = timezone.now()
                    push_message.device.save(update_fields=['last_used_at'])
                    
                    success_count += 1
                    if verbose:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Push notification sent to {push_message.device.device_type} device: {push_message.title}'
                            )
                        )
                    
                    processed_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    push_message.status = PushMessage.Status.FAILED
                    push_message.failed_at = timezone.now()
                    push_message.failure_reason = str(e)
                    push_message.save(update_fields=['status', 'failed_at', 'failure_reason'])
                    
                    if verbose:
                        self.stdout.write(
                            self.style.ERROR(
                                f'✗ Failed to send push notification: {str(e)}'
                            )
                        )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Processed {processed_count} push notifications: {success_count} sent, {failed_count} failed'
            )
        )
        
        # Clean up old messages
        self.cleanup_old_messages(verbose)
    
    def cleanup_old_messages(self, verbose=False):
        """Clean up old delivered messages"""
        from datetime import timedelta
        cutoff = timezone.now() - timedelta(days=7)
        
        old_messages = PushMessage.objects.filter(
            status__in=['DELIVERED', 'FAILED'],
            created_at__lt=cutoff
        )
        
        count = old_messages.count()
        if count > 0:
            old_messages.delete()
            if verbose:
                self.stdout.write(
                    self.style.NOTICE(
                        f'Cleaned up {count} old push messages'
                    )
                )