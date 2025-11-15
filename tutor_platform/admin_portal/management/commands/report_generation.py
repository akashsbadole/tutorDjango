"""
Django Tutor Platform Admin Portal Report Generation Command

This management command generates various system reports.
"""

import os
import json
import csv
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.conf import settings
from django.db.models import Count, Sum, Avg, Q
from django.template.loader import render_to_string
from django.core.mail import send_mail

from accounts.models import User, TutorProfile, StudentProfile
from requirements.models import Requirement, Proposal, Award, Session
from messaging.models import Conversation, Message
from notifications.models import Notification
from paymentsdetails.models import Payment, EscrowAccount, Payout, Transaction
from admin_portal.models import AdminActivityLog


class Command(BaseCommand):
    help = 'Generate system reports'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['daily', 'weekly', 'monthly', 'yearly', 'custom'],
            help='Report type',
            required=True
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output directory for reports',
            default=None
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'csv', 'html', 'all'],
            help='Report format',
            default='json'
        )
        parser.add_argument(
            '--email',
            action='store_true',
            help='Email report to administrators',
            default=False
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for custom reports (YYYY-MM-DD)',
            default=None
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for custom reports (YYYY-MM-DD)',
            default=None
        )
        parser.add_argument(
            '--recipients',
            type=str,
            help='Comma-separated list of email recipients',
            default=None
        )
    
    def handle(self, *args, **options):
        self.report_type = options['type']
        self.output_format = options['format']
        self.email_report = options['email']
        
        # Determine date range
        self.start_date, self.end_date = self._get_date_range(options)
        
        # Determine output directory
        self.output_dir = options['output'] or os.path.join(
            settings.MEDIA_ROOT, 'reports'
        )
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.stdout.write(self.style.SUCCESS('Generating system reports...'))
        self.stdout.write(f"Report type: {self.report_type}")
        self.stdout.write(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        
        try:
            # Generate report data
            report_data = self._generate_report_data()
            
            # Generate report files
            report_files = self._generate_report_files(report_data)
            
            # Email report if requested
            if self.email_report:
                self._email_report(report_data, report_files, options.get('recipients'))
            
            # Print summary
            self._print_summary(report_data, report_files)
            
            self.stdout.write(
                self.style.SUCCESS('Report generation completed successfully')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Report generation failed: {str(e)}')
            )
    
    def _get_date_range(self, options):
        """Get date range for report"""
        end_date = now()
        
        if self.report_type == 'daily':
            start_date = end_date - timedelta(days=1)
        elif self.report_type == 'weekly':
            start_date = end_date - timedelta(days=7)
        elif self.report_type == 'monthly':
            start_date = end_date - timedelta(days=30)
        elif self.report_type == 'yearly':
            start_date = end_date - timedelta(days=365)
        elif self.report_type == 'custom':
            if options['start_date']:
                start_date = datetime.strptime(options['start_date'], '%Y-%m-%d')
                start_date = now().replace(
                    year=start_date.year,
                    month=start_date.month,
                    day=start_date.day,
                    hour=0, minute=0, second=0, microsecond=0
                )
            else:
                start_date = end_date - timedelta(days=30)
            
            if options['end_date']:
                end_date = datetime.strptime(options['end_date'], '%Y-%m-%d')
                end_date = now().replace(
                    year=end_date.year,
                    month=end_date.month,
                    day=end_date.day,
                    hour=23, minute=59, second=59, microsecond=999999
                )
        else:
            start_date = end_date - timedelta(days=30)
        
        return start_date, end_date
    
    def _generate_report_data(self):
        """Generate report data"""
        report_data = {
            'metadata': {
                'report_type': self.report_type,
                'generated_at': now().isoformat(),
                'start_date': self.start_date.isoformat(),
                'end_date': self.end_date.isoformat(),
            },
            'users': self._get_user_stats(),
            'requirements': self._get_requirement_stats(),
            'sessions': self._get_session_stats(),
            'payments': self._get_payment_stats(),
            'communications': self._get_communication_stats(),
            'admin_activity': self._get_admin_activity_stats(),
        }
        
        return report_data
    
    def _get_user_stats(self):
        """Get user statistics"""
        users = User.objects.filter(
            date_joined__gte=self.start_date,
            date_joined__lte=self.end_date
        )
        
        return {
            'new_users': users.count(),
            'active_users': users.filter(
                last_login__gte=self.start_date
            ).count(),
            'tutors': TutorProfile.objects.filter(
                user__date_joined__gte=self.start_date,
                user__date_joined__lte=self.end_date
            ).count(),
            'students': StudentProfile.objects.filter(
                user__date_joined__gte=self.start_date,
                user__date_joined__lte=self.end_date
            ).count(),
            'verified_users': users.filter(is_verified=True).count(),
            'unverified_users': users.filter(is_verified=False).count(),
        }
    
    def _get_requirement_stats(self):
        """Get requirement statistics"""
        requirements = Requirement.objects.filter(
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )
        
        return {
            'total_requirements': requirements.count(),
            'open_requirements': requirements.filter(status='OPEN').count(),
            'in_progress': requirements.filter(status='IN_PROGRESS').count(),
            'completed': requirements.filter(status='COMPLETED').count(),
            'cancelled': requirements.filter(status='CANCELLED').count(),
            'total_proposals': Proposal.objects.filter(
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            ).count(),
            'accepted_proposals': Proposal.objects.filter(
                created_at__gte=self.start_date,
                created_at__lte=self.end_date,
                status='ACCEPTED'
            ).count(),
            'average_budget': requirements.aggregate(
                avg=Avg('budget')
            )['avg'] or 0,
        }
    
    def _get_session_stats(self):
        """Get session statistics"""
        sessions = Session.objects.filter(
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )
        
        return {
            'total_sessions': sessions.count(),
            'scheduled': sessions.filter(status='SCHEDULED').count(),
            'completed': sessions.filter(status='COMPLETED').count(),
            'cancelled': sessions.filter(status='CANCELLED').count(),
            'total_duration': sessions.aggregate(
                total=Sum('duration_minutes')
            )['total'] or 0,
            'average_duration': sessions.aggregate(
                avg=Avg('duration_minutes')
            )['avg'] or 0,
            'upcoming_sessions': Session.objects.filter(
                scheduled_start__gte=now(),
                scheduled_start__lte=self.end_date
            ).count(),
        }
    
    def _get_payment_stats(self):
        """Get payment statistics"""
        payments = Payment.objects.filter(
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )
        
        completed_payments = payments.filter(status='COMPLETED')
        
        return {
            'total_payments': payments.count(),
            'completed_payments': completed_payments.count(),
            'failed_payments': payments.filter(status='FAILED').count(),
            'pending_payments': payments.filter(status='PENDING').count(),
            'total_amount': completed_payments.aggregate(
                total=Sum('amount')
            )['total'] or 0,
            'average_amount': completed_payments.aggregate(
                avg=Avg('amount')
            )['avg'] or 0,
            'platform_fee': completed_payments.aggregate(
                total=Sum('platform_fee')
            )['total'] or 0,
            'tutor_earnings': completed_payments.aggregate(
                total=Sum('tutor_amount')
            )['total'] or 0,
            'payouts': Payout.objects.filter(
                created_at__gte=self.start_date,
                created_at__lte=self.end_date
            ).count(),
        }
    
    def _get_communication_stats(self):
        """Get communication statistics"""
        conversations = Conversation.objects.filter(
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )
        
        messages = Message.objects.filter(
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )
        
        return {
            'new_conversations': conversations.count(),
            'total_messages': messages.count(),
            'average_messages_per_conversation': (
                messages.count() / conversations.count() if conversations.count() > 0 else 0
            ),
            'messages_with_attachments': messages.filter(
                attachments__isnull=False
            ).distinct().count(),
        }
    
    def _get_admin_activity_stats(self):
        """Get admin activity statistics"""
        activities = AdminActivityLog.objects.filter(
            timestamp__gte=self.start_date,
            timestamp__lte=self.end_date
        )
        
        return {
            'total_activities': activities.count(),
            'login_activities': activities.filter(action_type='LOGIN').count(),
            'create_activities': activities.filter(action_type='CREATE').count(),
            'update_activities': activities.filter(action_type='UPDATE').count(),
            'delete_activities': activities.filter(action_type='DELETE').count(),
            'export_activities': activities.filter(action_type='EXPORT').count(),
            'unique_admins': activities.values('admin').distinct().count(),
        }
    
    def _generate_report_files(self, report_data):
        """Generate report files in specified formats"""
        timestamp = now().strftime('%Y%m%d_%H%M%S')
        report_name = f"report_{self.report_type}_{timestamp}"
        report_files = []
        
        if self.output_format in ['json', 'all']:
            json_file = os.path.join(self.output_dir, f"{report_name}.json")
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, default=str)
            report_files.append(json_file)
        
        if self.output_format in ['csv', 'all']:
            csv_file = os.path.join(self.output_dir, f"{report_name}.csv")
            self._write_csv_report(csv_file, report_data)
            report_files.append(csv_file)
        
        if self.output_format in ['html', 'all']:
            html_file = os.path.join(self.output_dir, f"{report_name}.html")
            self._write_html_report(html_file, report_data)
            report_files.append(html_file)
        
        return report_files
    
    def _write_csv_report(self, file_path, report_data):
        """Write CSV report"""
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Category', 'Metric', 'Value'])
            
            # Write data
            for category, metrics in report_data.items():
                if category == 'metadata':
                    continue
                
                for metric, value in metrics.items():
                    writer.writerow([category.title(), metric.replace('_', ' ').title(), value])
    
    def _write_html_report(self, file_path, report_data):
        """Write HTML report"""
        html_content = render_to_string(
            'admin_portal/reports/system_report.html',
            {'report_data': report_data}
        )
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _email_report(self, report_data, report_files, recipients):
        """Email report to administrators"""
        try:
            # Get recipients
            if recipients:
                recipient_list = [r.strip() for r in recipients.split(',')]
            else:
                # Get admin users
                from admin_portal.models import AdminProfile
                recipient_list = AdminProfile.objects.filter(
                    is_super_admin=True
                ).values_list('user__email', flat=True)
            
            if not recipient_list:
                self.stdout.write(
                    self.style.WARNING('No recipients specified for email report')
                )
                return
            
            # Prepare email
            subject = f'System Report - {self.report_type.title()} - {now().date()}'
            
            context = {
                'report_data': report_data,
                'report_type': self.report_type,
                'site_name': getattr(settings, 'SITE_NAME', 'Django Tutor Platform'),
            }
            
            message = render_to_string(
                'admin_portal/emails/report_email.html',
                context
            )
            
            # Attach files
            from django.core.mail import EmailMessage
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tutorplatform.com'),
                to=list(recipient_list),
            )
            email.content_subtype = 'html'
            
            # Attach report files
            for file_path in report_files:
                email.attach_file(file_path)
            
            email.send()
            
            self.stdout.write(f"  -> Report emailed to {len(recipient_list)} recipients")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to email report: {str(e)}")
            )
    
    def _print_summary(self, report_data, report_files):
        """Print report summary"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("REPORT SUMMARY")
        self.stdout.write("="*50)
        self.stdout.write(f"Report type: {report_data['metadata']['report_type']}")
        self.stdout.write(f"Generated at: {report_data['metadata']['generated_at']}")
        self.stdout.write(f"Date range: {report_data['metadata']['start_date']} to {report_data['metadata']['end_date']}")
        
        self.stdout.write("\nKey Metrics:")
        self.stdout.write(f"  - New users: {report_data['users']['new_users']}")
        self.stdout.write(f"  - New requirements: {report_data['requirements']['total_requirements']}")
        self.stdout.write(f"  - Total sessions: {report_data['sessions']['total_sessions']}")
        self.stdout.write(f"  - Total payments: ${report_data['payments']['total_amount']:.2f}")
        self.stdout.write(f"  - Total messages: {report_data['communications']['total_messages']}")
        
        self.stdout.write("\nGenerated Files:")
        for file_path in report_files:
            self.stdout.write(f"  - {file_path}")
        
        self.stdout.write("="*50)