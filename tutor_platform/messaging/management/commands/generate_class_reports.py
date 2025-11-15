from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from datetime import timedelta
import csv
import io

from messaging.models import (
    OnlineClass, ClassRecording, ClassResource, ClassAttendance, ClassParticipant
)


class Command(BaseCommand):
    help = 'Generate reports for online classes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to include in report (default: 30)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (optional)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['csv', 'json'],
            default='csv',
            help='Output format (default: csv)'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        output_file = options.get('output')
        output_format = options['format']
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get classes in date range
        classes = OnlineClass.objects.filter(
            scheduled_start__gte=start_date,
            scheduled_start__lte=end_date
        ).select_related('host', 'session')
        
        # Generate report data
        report_data = []
        
        for online_class in classes:
            # Get statistics for this class
            participants_count = online_class.participants.count()
            attended_count = online_class.attendance_records.filter(
                attended=True
            ).count()
            
            # Get recording statistics
            recordings_count = online_class.recordings.count()
            total_views = online_class.recordings.aggregate(
                total_views=Sum('view_count')
            )['total_views'] or 0
            
            # Get resource statistics
            resources_count = online_class.resources.count()
            total_downloads = online_class.resources.aggregate(
                total_downloads=Sum('download_count')
            )['total_downloads'] or 0
            
            # Calculate revenue if applicable
            try:
                price = online_class.session.award.price if online_class.session and online_class.session.award else 0
                revenue = participants_count * price
            except:
                price = 0
                revenue = 0
            
            # Calculate attendance rate
            attendance_rate = (attended_count / participants_count * 100) if participants_count > 0 else 0
            
            # Get average engagement score
            avg_engagement = online_class.attendance_records.aggregate(
                avg_score=Avg('engagement_score')
            )['avg_score'] or 0
            
            report_data.append({
                'Class ID': online_class.id,
                'Title': online_class.title,
                'Host': online_class.host.username if online_class.host else 'N/A',
                'Platform': online_class.get_platform_display(),
                'Status': online_class.get_status_display(),
                'Scheduled Start': online_class.scheduled_start.strftime('%Y-%m-%d %H:%M:%S'),
                'Scheduled End': online_class.scheduled_end.strftime('%Y-%m-%d %H:%M:%S'),
                'Duration (minutes)': online_class.get_duration(),
                'Price': price,
                'Total Participants': participants_count,
                'Attended': attended_count,
                'Attendance Rate (%)': round(attendance_rate, 2),
                'Avg Engagement Score': round(avg_engagement, 2),
                'Recordings Count': recordings_count,
                'Total Recording Views': total_views,
                'Resources Count': resources_count,
                'Total Resource Downloads': total_downloads,
                'Revenue': revenue,
                'Created At': online_class.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        
        # Output report
        if output_format == 'csv':
            self._output_csv(report_data, output_file)
        else:
            self._output_json(report_data, output_file)
        
        self.stdout.write(
            self.style.SUCCESS(f"Generated report for {len(report_data)} classes")
        )
    
    def _output_csv(self, data, output_file=None):
        """Output data as CSV"""
        if not data:
            return
        
        if output_file:
            with open(output_file, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            self.stdout.write(
                self.style.SUCCESS(f"CSV report saved to {output_file}")
            )
        else:
            # Output to console
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            
            self.stdout.write(output.getvalue())
    
    def _output_json(self, data, output_file=None):
        """Output data as JSON"""
        import json
        
        if output_file:
            with open(output_file, 'w') as jsonfile:
                json.dump(data, jsonfile, indent=2, default=str)
            self.stdout.write(
                self.style.SUCCESS(f"JSON report saved to {output_file}")
            )
        else:
            # Output to console
            self.stdout.write(json.dumps(data, indent=2, default=str))