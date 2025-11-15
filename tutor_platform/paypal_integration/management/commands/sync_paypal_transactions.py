import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from paypal_integration.models import PayPalAccount, PayPalTransaction
from paypal_integration.services import PayPalAccountService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync PayPal transactions from PayPal API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to look back for transactions (default: 7)'
        )
        parser.add_argument(
            '--account-id',
            type=str,
            help='Specific PayPal account ID to sync (optional)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run in dry-run mode without making changes'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        account_id = options['account_id']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(f'Syncing PayPal transactions for the last {days} days...')
        )
        
        # Get accounts to sync
        if account_id:
            try:
                accounts = [PayPalAccount.objects.get(id=account_id)]
            except PayPalAccount.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'PayPal account with ID {account_id} not found')
                )
                return
        else:
            accounts = PayPalAccount.objects.filter(
                is_active=True,
                access_token__isnull=False
            )
        
        if not accounts:
            self.stdout.write(
                self.style.WARNING('No active PayPal accounts found')
            )
            return
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        total_transactions = 0
        total_accounts = len(accounts)
        
        for i, account in enumerate(accounts, 1):
            self.stdout.write(
                f'Processing account {i}/{total_accounts}: {account.paypal_email}'
            )
            
            try:
                # Get account service
                service = PayPalAccountService(account)
                
                # Sync transactions page by page
                page = 1
                account_transactions = 0
                
                while True:
                    result = service.get_transaction_history(
                        account,
                        start_date=start_date,
                        end_date=end_date,
                        page=page
                    )
                    
                    if not result['success']:
                        self.stdout.write(
                            self.style.ERROR(
                                f'Failed to get transactions for page {page}: '
                                f"{result['error']}"
                            )
                        )
                        break
                    
                    transactions = result['transactions']
                    if not transactions:
                        break
                    
                    if dry_run:
                        self.stdout.write(
                            f'  Would sync {len(transactions)} transactions '
                            f'on page {page}'
                        )
                    else:
                        # Process transactions
                        synced = self._process_transactions(
                            transactions, account
                        )
                        account_transactions += synced
                    
                    self.stdout.write(
                        f'  Processed {len(transactions)} transactions '
                        f'on page {page}'
                    )
                    
                    # Check if there are more pages
                    if page >= result['total_pages']:
                        break
                    
                    page += 1
                
                total_transactions += account_transactions
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Synced {account_transactions} transactions for '
                        f'{account.paypal_email}'
                    )
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error syncing account {account.paypal_email}: {str(e)}'
                    )
                )
                logger.error(
                    f'Error syncing PayPal account {account.id}: {str(e)}'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Total: Synced {total_transactions} transactions from '
                f'{total_accounts} accounts'
            )
        )
    
    def _process_transactions(self, transactions, paypal_account):
        """Process and save PayPal transactions"""
        synced_count = 0
        
        with transaction.atomic():
            for trans_data in transactions:
                # Check if transaction already exists
                transaction_id = trans_data['transaction_id']
                
                if PayPalTransaction.objects.filter(
                    paypal_transaction_id=transaction_id
                ).exists():
                    continue
                
                # Map PayPal status to our status
                status_map = {
                    'S': 'COMPLETED',
                    'P': 'PENDING',
                    'F': 'FAILED',
                    'D': 'CANCELLED',
                    'V': 'CANCELLED',
                    'R': 'REFUNDED'
                }
                
                paypal_status = status_map.get(
                    trans_data['type'], 'PENDING'
                )
                
                # Create transaction record
                PayPalTransaction.objects.create(
                    paypal_transaction_id=transaction_id,
                    paypal_status=paypal_status,
                    transaction_type=self._get_transaction_type(trans_data['type']),
                    amount=trans_data['amount'],
                    currency=trans_data['currency'],
                    net_amount=trans_data['amount'],  # Would calculate fees in real implementation
                    paypal_account=paypal_account,
                    paypal_response=trans_data
                )
                
                synced_count += 1
        
        return synced_count
    
    def _get_transaction_type(self, paypal_type):
        """Map PayPal transaction type to our types"""
        type_map = {
            'T': 'PAYMENT',      # Payment
            'C': 'PAYMENT',      # Credit
            'D': 'PAYOUT',       # Debit
            'W': 'PAYOUT',       # Withdrawal
            'R': 'REFUND',       # Refund
            'X': 'TRANSFER'       # Transfer
        }
        
        return type_map.get(paypal_type, 'PAYMENT')