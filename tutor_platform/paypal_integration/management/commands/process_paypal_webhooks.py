import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from paypal_integration.models import PayPalWebhook
from paypal_integration.services import PayPalWebhookService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process pending PayPal webhooks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Retry processing failed webhooks'
        )
        parser.add_argument(
            '--max-attempts',
            type=int,
            default=3,
            help='Maximum processing attempts (default: 3)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of webhooks to process in one batch (default: 50)'
        )
    
    def handle(self, *args, **options):
        retry_failed = options['retry_failed']
        max_attempts = options['max_attempts']
        batch_size = options['batch_size']
        
        self.stdout.write('Processing PayPal webhooks...')
        
        # Get webhooks to process
        if retry_failed:
            webhooks = PayPalWebhook.objects.filter(
                status__in=[PayPalWebhook.WebhookStatus.FAILED],
                processing_attempts__lt=max_attempts
            ).order_by('created_at')
            
            self.stdout.write(f'Found {webhooks.count()} failed webhooks to retry')
        else:
            webhooks = PayPalWebhook.objects.filter(
                status=PayPalWebhook.WebhookStatus.PENDING,
                processing_attempts__lt=max_attempts
            ).order_by('created_at')
            
            self.stdout.write(f'Found {webhooks.count()} pending webhooks')
        
        if not webhooks.exists():
            self.stdout.write(self.style.SUCCESS('No webhooks to process'))
            return
        
        # Process webhooks in batches
        total_processed = 0
        total_failed = 0
        webhook_service = PayPalWebhookService()
        
        while webhooks.exists():
            batch = webhooks[:batch_size]
            batch_size_actual = len(batch)
            
            self.stdout.write(f'Processing batch of {batch_size_actual} webhooks...')
            
            for webhook in batch:
                try:
                    with transaction.atomic():
                        # Increment processing attempts
                        webhook.processing_attempts += 1
                        webhook.save()
                        
                        # Process the webhook
                        success = webhook_service.process_webhook(webhook)
                        
                        if success:
                            webhook.mark_processed()
                            total_processed += 1
                            self.stdout.write(
                                f'  ✓ Processed webhook {webhook.event_id} '
                                f'({webhook.event_type})'
                            )
                        else:
                            total_failed += 1
                            self.stdout.write(
                                self.style.ERROR(
                                    f'  ✗ Failed to process webhook '
                                    f'{webhook.event_id}'
                                )
                            )
                
                except Exception as e:
                    total_failed += 1
                    webhook.mark_failed(str(e))
                    
                    self.stdout.write(
                        self.style.ERROR(
                            f'  ✗ Error processing webhook '
                            f'{webhook.event_id}: {str(e)}'
                        )
                    )
                    
                    logger.error(
                        f'Error processing webhook {webhook.id}: {str(e)}',
                        exc_info=True
                    )
            
            # Get next batch
            if retry_failed:
                webhooks = PayPalWebhook.objects.filter(
                    status__in=[PayPalWebhook.WebhookStatus.FAILED],
                    processing_attempts__lt=max_attempts
                ).order_by('created_at')
            else:
                webhooks = PayPalWebhook.objects.filter(
                    status=PayPalWebhook.WebhookStatus.PENDING,
                    processing_attempts__lt=max_attempts
                ).order_by('created_at')
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Processing complete: {total_processed} processed, '
                f'{total_failed} failed'
            )
        )
        
        # Clean up old processed webhooks
        self._cleanup_old_webhooks()
    
    def _cleanup_old_webhooks(self):
        """Clean up old processed webhooks"""
        try:
            # Delete webhooks older than 30 days
            cutoff_date = timezone.now() - timedelta(days=30)
            
            deleted_count = PayPalWebhook.objects.filter(
                status=PayPalWebhook.WebhookStatus.PROCESSED,
                processed_at__lt=cutoff_date
            ).delete()[0]
            
            if deleted_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Cleaned up {deleted_count} old processed webhooks'
                    )
                )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error cleaning up webhooks: {str(e)}')
            )
            logger.error(f'Error cleaning up webhooks: {str(e)}', exc_info=True)