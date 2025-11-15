"""
Django management command to check test coverage.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import sys
import subprocess


class Command(BaseCommand):
    help = 'Check test coverage for the Django tutoring platform'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--html',
            action='store_true',
            help='Generate HTML coverage report'
        )
        parser.add_argument(
            '--xml',
            action='store_true',
            help='Generate XML coverage report'
        )
        parser.add_argument(
            '--report',
            type=str,
            default='term',
            choices=['term', 'html', 'xml'],
            help='Coverage report format'
        )
        parser.add_argument(
            '--fail-under',
            type=int,
            default=80,
            help='Exit with failure status if coverage is below this percentage'
        )
        parser.add_argument(
            '--source',
            type=str,
            default='tutor_platform',
            help='Source code directory to measure coverage for'
        )
        parser.add_argument(
            '--omit',
            type=str,
            default='*/migrations/*,*/tests/*,*/venv/*,*/env/*',
            help='File patterns to omit from coverage'
        )
        
    def handle(self, *args, **options):
        """Check test coverage."""
        self.stdout.write(self.style.SUCCESS('Running test coverage check...'))
        
        # Build coverage command
        cmd = [sys.executable, '-m', 'pytest']
        
        # Add coverage options
        cmd.extend([
            f'--cov={options["source"]}',
            f'--cov-report={options["report"]}',
            f'--cov-fail-under={options["fail_under"]}',
            f'--cov-omit={options["omit"]}'
        ])
        
        # Add HTML report if requested
        if options['html']:
            cmd.append('--cov-report=html')
            
        # Add XML report if requested
        if options['xml']:
            cmd.append('--cov-report=xml')
            
        # Add test directory
        cmd.append('tests/')
        
        try:
            # Run coverage check
            result = subprocess.run(cmd, cwd=settings.BASE_DIR)
            
            if result.returncode == 0:
                self.stdout.write(self.style.SUCCESS(
                    f'Test coverage is above {options["fail_under"]}%'
                ))
                
                # Report file locations
                if options['html'] or options['report'] == 'html':
                    html_path = os.path.join(settings.BASE_DIR, 'htmlcov', 'index.html')
                    self.stdout.write(self.style.SUCCESS(
                        f'HTML coverage report generated at: {html_path}'
                    ))
                    
                if options['xml'] or options['report'] == 'xml':
                    xml_path = os.path.join(settings.BASE_DIR, 'coverage.xml')
                    self.stdout.write(self.style.SUCCESS(
                        f'XML coverage report generated at: {xml_path}'
                    ))
            else:
                self.stdout.write(self.style.ERROR(
                    f'Test coverage is below {options["fail_under"]}%'
                ))
                sys.exit(result.returncode)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error checking test coverage: {e}'))
            sys.exit(1)