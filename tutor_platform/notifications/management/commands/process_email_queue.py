from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from notifications.models import EmailQueue


class Command(BaseCommand):
    help = 'Process email queue for pending emails'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of emails to process in one run'
        )
        parser.add_argument(
            '--retry-failed',
            action='store_true',
            help='Also process emails that have failed and can be retried'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Provide verbose output'
        )
    
    def handle(self, *args, **options):
        limit = options['limit']
        retry_failed = options['retry_failed']
        verbose = options['verbose']
        
        # Get emails to process
        emails_to_process = EmailQueue.objects.filter(
            status=EmailQueue.Status.PENDING
        )
        
        if retry_failed:
            emails_to_process = emails_to_process | EmailQueue.objects.filter(
                status=EmailQueue.Status.FAILED
            ).filter(
                next_retry_at__lte=timezone.now()
            )
        
        emails_to_process = emails_to_process.order_by('created_at')[:limit]
        
        if not emails_to_process.exists():
            if verbose:
                self.stdout.write(self.style.WARNING('No emails to process'))
            return
        
        processed_count = 0
        success_count = 0
        failed_count = 0
        
        self.stdout.write(f'Processing {emails_to_process.count()} emails...')
        
        for email_queue in emails_to_process:
            with transaction.atomic():
                try:
                    if email_queue.send():
                        success_count += 1
                        if verbose:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'✓ Email sent to {email_queue.recipient.email}: {email_queue.subject}'
                                )
                            )
                    else:
                        failed_count += 1
                        if verbose:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'✗ Failed to send email to {email_queue.recipient.email}: {email_queue.subject}'
                                )
                            )
                    
                    processed_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    if verbose:
                        self.stdout.write(
                            self.style.ERROR(
                                f'✗ Error processing email: {str(e)}'
                            )
                        )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Processed {processed_count} emails: {success_count} sent, {failed_count} failed'
            )
        )
        
        # Clean up old sent emails
        self.cleanup_old_emails(verbose)
    
    def cleanup_old_emails(self, verbose=False):
        """Clean up old sent emails from queue"""
        cutoff_date = timezone.now() - timezone.timedelta(days=30)
        
        old_emails = EmailQueue.objects.filter(
            status=EmailQueue.Status.SENT,
            sent_at__lt=cutoff_date
        )
        
        count = old_emails.count()
        if count > 0:
            old_emails.delete()
            if verbose:
                self.stdout.write(
                    self.style.NOTICE(
                        f'Cleaned up {count} old sent emails'
                    )
                )