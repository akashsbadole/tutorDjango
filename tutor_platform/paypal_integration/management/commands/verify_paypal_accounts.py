import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from paypal_integration.models import PayPalAccount
from paypal_integration.services import PayPalAccountService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Verify PayPal accounts and refresh tokens'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--account-id',
            type=str,
            help='Specific PayPal account ID to verify (optional)'
        )
        parser.add_argument(
            '--refresh-tokens',
            action='store_true',
            help='Refresh expired access tokens'
        )
        parser.add_argument(
            '--check-balance',
            action='store_true',
            help='Check account balances'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all accounts (default: only active accounts)'
        )
    
    def handle(self, *args, **options):
        account_id = options['account_id']
        refresh_tokens = options['refresh_tokens']
        check_balance = options['check_balance']
        process_all = options['all']
        
        self.stdout.write('Verifying PayPal accounts...')
        
        # Get accounts to verify
        if account_id:
            try:
                accounts = [PayPalAccount.objects.get(id=account_id)]
            except PayPalAccount.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'PayPal account with ID {account_id} not found')
                )
                return
        else:
            accounts = PayPalAccount.objects.all() if process_all else PayPalAccount.objects.filter(is_active=True)
        
        if not accounts:
            self.stdout.write(
                self.style.WARNING('No PayPal accounts found')
            )
            return
        
        total_verified = 0
        total_refreshed = 0
        total_balance_checked = 0
        total_failed = 0
        
        for i, account in enumerate(accounts, 1):
            self.stdout.write(
                f'Processing account {i}/{len(accounts)}: {account.paypal_email}'
            )
            
            try:
                service = PayPalAccountService(account)
                account_verified = False
                token_refreshed = False
                balance_checked = False
                
                # Check if account needs verification
                if account.verification_status != 'VERIFIED':
                    self.stdout.write('  Verifying account...')
                    result = service.verify_account(account)
                    
                    if result['success']:
                        account_verified = True
                        self.stdout.write(
                            self.style.SUCCESS('    ✓ Account verified')
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'    ✗ Verification failed: {result["error"]}'
                            )
                        )
                        total_failed += 1
                
                # Refresh expired tokens
                if refresh_tokens and account.is_token_expired():
                    self.stdout.write('  Refreshing access token...')
                    account.refresh_access_token()
                    token_refreshed = True
                    total_refreshed += 1
                    self.stdout.write(
                        self.style.SUCCESS('    ✓ Access token refreshed')
                    )
                
                # Check account balance
                if check_balance:
                    self.stdout.write('  Checking account balance...')
                    result = service.get_account_balance(account)
                    
                    if result['success']:
                        balance_checked = True
                        total_balance_checked += 1
                        
                        # Display balances
                        for balance in result['balances']:
                            self.stdout.write(
                                f'    {balance["currency"]}: '
                                f'{balance["available"]} available, '
                                f'{balance["held"]} held'
                            )
                    else:
                        self.stdout.write(
                            self.style.ERROR(
                                f'    ✗ Balance check failed: {result["error"]}'
                            )
                        )
                        total_failed += 1
                
                # Update account status
                if account_verified or token_refreshed or balance_checked:
                    account.updated_at = timezone.now()
                    account.save()
                
                # Mark as verified if any operation succeeded
                if account_verified or token_refreshed:
                    total_verified += 1
                
            except Exception as e:
                total_failed += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  ✗ Error processing account: {str(e)}'
                    )
                )
                logger.error(
                    f'Error verifying PayPal account {account.id}: {str(e)}',
                    exc_info=True
                )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Verification complete: {total_verified} accounts verified, '
                f'{total_refreshed} tokens refreshed, '
                f'{total_balance_checked} balances checked'
            )
        )
        
        if total_failed > 0:
            self.stdout.write(
                self.style.ERROR(f'{total_failed} operations failed')
            )
        
        # Check for accounts with expired tokens
        if not refresh_tokens:
            expired_accounts = PayPalAccount.objects.filter(
                is_active=True,
                access_token__isnull=False,
                token_expires_at__lt=timezone.now()
            )
            
            if expired_accounts.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f'Found {expired_accounts.count()} accounts with expired tokens. '
                        f'Run with --refresh-tokens to update them.'
                    )
                )