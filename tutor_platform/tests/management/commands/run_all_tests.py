"""
Django management command to run all tests.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
import os
import sys


class Command(BaseCommand):
    help = 'Run all tests for the Django tutoring platform'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--coverage',
            action='store_true',
            help='Run tests with coverage reporting'
        )
        parser.add_argument(
            '--parallel',
            type=int,
            default=1,
            help='Number of parallel processes to use'
        )
        parser.add_argument(
            '--failfast',
            action='store_true',
            help='Stop running tests on first failure'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output'
        )
        parser.add_argument(
            '--tag',
            type=str,
            help='Run tests with specific tag'
        )
        
    def handle(self, *args, **options):
        """Run all tests."""
        # Build test command arguments
        test_args = []
        
        # Add coverage if requested
        if options['coverage']:
            test_args.extend([
                '--cov=tutor_platform',
                '--cov-report=html',
                '--cov-report=term-missing'
            ])
            
        # Add parallel execution if requested
        if options['parallel'] > 1:
            test_args.append(f'--parallel={options["parallel"]}')
            
        # Add failfast if requested
        if options['failfast']:
            test_args.append('--failfast')
            
        # Add verbose if requested
        if options['verbose']:
            test_args.append('-v')
            
        # Add tag if specified
        if options['tag']:
            test_args.append(f'-m {options["tag"]}')
            
        # Define test modules to run
        test_modules = [
            'tests.unit',
            'tests.integration',
            'tests.api',
            'tests.performance',
            'tests.security',
            'tests.frontend',
            'tests.payment',
            'tests.email'
        ]
        
        # Run tests
        self.stdout.write(self.style.SUCCESS('Running all tests...'))
        
        try:
            # Call pytest with all test modules
            import subprocess
            cmd = [sys.executable, '-m', 'pytest'] + test_args + test_modules
            result = subprocess.run(cmd, cwd=settings.BASE_DIR)
            
            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS('All tests passed successfully!'))
            else:
                self.stdout.write(self.style.ERROR('Some tests failed.'))
                sys.exit(result.returncode)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error running tests: {e}'))
            sys.exit(1)