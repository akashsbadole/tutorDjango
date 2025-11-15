"""
Django Tutor Platform Admin Portal Data Backup Command

This management command creates backups of the platform data.
"""

import os
import json
import zipfile
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django.core import serializers
from django.utils.timezone import now

from accounts.models import User, TutorProfile, StudentProfile
from requirements.models import Requirement, Proposal, Award, Session
from messaging.models import Conversation, Message
from notifications.models import Notification
from paymentsdetails.models import Payment, EscrowAccount, Payout, Transaction
from admin_portal.models import AdminRole, AdminProfile, AdminActivityLog, SystemSetting


class Command(BaseCommand):
    help = 'Create a backup of platform data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            help='Output directory for backup files',
            default=None
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            help='Compress backup files into a ZIP archive',
            default=False
        )
        parser.add_argument(
            '--include-media',
            action='store_true',
            help='Include media files in backup',
            default=False
        )
        parser.add_argument(
            '--models',
            type=str,
            help='Comma-separated list of models to backup (default: all)',
            default=None
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data backup...'))
        
        # Determine output directory
        output_dir = options['output'] or os.path.join(settings.MEDIA_ROOT, 'backups')
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate backup filename
        timestamp = now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"platform_backup_{timestamp}"
        
        backup_dir = None
        if options['compress']:
            backup_path = os.path.join(output_dir, f"{backup_name}.zip")
            backup_dir = os.path.join(output_dir, backup_name)
            os.makedirs(backup_dir, exist_ok=True)
        else:
            backup_path = os.path.join(output_dir, backup_name)
            backup_dir = backup_path
            os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # Get models to backup
            models_to_backup = self._get_models_to_backup(options['models'])
            
            # Backup data
            backup_info = {
                'timestamp': now().isoformat(),
                'models_backed_up': [],
                'file_count': 0,
                'total_size': 0,
            }
            
            for model in models_to_backup:
                self._backup_model(model, backup_dir, backup_info)
            
            # Include media files if requested
            if options['include_media']:
                self._backup_media_files(backup_dir, backup_info)
            
            # Create metadata file
            self._create_metadata_file(backup_dir, backup_info)
            
            # Compress if requested
            if options['compress']:
                self._compress_backup(backup_dir, backup_path)
                backup_info['backup_path'] = backup_path
                # Remove uncompressed directory
                import shutil
                shutil.rmtree(backup_dir)
            else:
                backup_info['backup_path'] = backup_path
            
            # Print summary
            self._print_summary(backup_info)
            
            self.stdout.write(
                self.style.SUCCESS(f'Backup completed successfully: {backup_info["backup_path"]}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Backup failed: {str(e)}')
            )
            # Clean up on failure
            if os.path.exists(backup_path):
                os.remove(backup_path)
            if options['compress'] and os.path.exists(backup_dir):
                import shutil
                shutil.rmtree(backup_dir)
    
    def _get_models_to_backup(self, models_str):
        """Get list of models to backup"""
        all_models = [
            User, TutorProfile, StudentProfile,
            Requirement, Proposal, Award, Session,
            Conversation, Message,
            Notification,
            Payment, EscrowAccount, Payout, Transaction,
            AdminRole, AdminProfile, AdminActivityLog, SystemSetting,
        ]
        
        if not models_str:
            return all_models
        
        model_names = [name.strip() for name in models_str.split(',')]
        models_to_backup = []
        
        for model in all_models:
            if model.__name__ in model_names:
                models_to_backup.append(model)
        
        return models_to_backup
    
    def _backup_model(self, model, backup_dir, backup_info):
        """Backup a single model"""
        model_name = f"{model._meta.app_label}.{model.__name__}"
        self.stdout.write(f"Backing up {model_name}...")
        
        try:
            # Serialize model data
            queryset = model.objects.all()
            serialized_data = serializers.serialize('json', queryset)
            
            # Write to file
            filename = f"{model_name.replace('.', '_')}.json"
            file_path = os.path.join(backup_dir, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(serialized_data)
            
            # Update backup info
            backup_info['models_backed_up'].append({
                'model': model_name,
                'count': queryset.count(),
                'file': filename,
                'size': os.path.getsize(file_path),
            })
            backup_info['file_count'] += 1
            backup_info['total_size'] += os.path.getsize(file_path)
            
            self.stdout.write(f"  -> {queryset.count()} records backed up")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to backup {model_name}: {str(e)}")
            )
    
    def _backup_media_files(self, backup_dir, backup_info):
        """Backup media files"""
        self.stdout.write("Backing up media files...")
        
        media_dir = settings.MEDIA_ROOT
        if not os.path.exists(media_dir):
            self.stdout.write("  -> No media directory found")
            return
        
        backup_media_dir = os.path.join(backup_dir, 'media')
        
        try:
            import shutil
            shutil.copytree(media_dir, backup_media_dir)
            
            # Calculate media size
            media_size = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, dirnames, filenames in os.walk(backup_media_dir)
                for filename in filenames
            )
            
            backup_info['media_size'] = media_size
            backup_info['total_size'] += media_size
            
            self.stdout.write(f"  -> Media files backed up ({self._format_size(media_size)})")
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to backup media files: {str(e)}")
            )
    
    def _create_metadata_file(self, backup_dir, backup_info):
        """Create metadata file for backup"""
        metadata = {
            'backup_info': backup_info,
            'django_settings': {
                'DEBUG': settings.DEBUG,
                'DATABASES': {
                    'default': {
                        'ENGINE': settings.DATABASES['default']['ENGINE'],
                        'NAME': settings.DATABASES['default']['NAME'],
                    }
                },
                'INSTALLED_APPS': settings.INSTALLED_APPS,
                'TIME_ZONE': settings.TIME_ZONE,
            },
            'schema_info': self._get_schema_info(),
        }
        
        metadata_path = os.path.join(backup_dir, 'metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, default=str)
        
        backup_info['file_count'] += 1
        backup_info['total_size'] += os.path.getsize(metadata_path)
    
    def _get_schema_info(self):
        """Get database schema information"""
        schema_info = {}
        
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            for table_name, in tables:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                schema_info[table_name] = [
                    {
                        'name': col[1],
                        'type': col[2],
                        'notnull': bool(col[3]),
                        'default': col[4],
                        'pk': bool(col[5]),
                    }
                    for col in columns
                ]
        
        return schema_info
    
    def _compress_backup(self, backup_dir, backup_path):
        """Compress backup directory into ZIP file"""
        self.stdout.write("Compressing backup...")
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, backup_dir)
                    zipf.write(file_path, arcname)
        
        self.stdout.write(f"  -> Backup compressed: {self._format_size(os.path.getsize(backup_path))}")
    
    def _format_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f}{size_names[i]}"
    
    def _print_summary(self, backup_info):
        """Print backup summary"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("BACKUP SUMMARY")
        self.stdout.write("="*50)
        self.stdout.write(f"Timestamp: {backup_info['timestamp']}")
        self.stdout.write(f"Models backed up: {len(backup_info['models_backed_up'])}")
        self.stdout.write(f"Files created: {backup_info['file_count']}")
        self.stdout.write(f"Total size: {self._format_size(backup_info['total_size'])}")
        
        if 'media_size' in backup_info:
            self.stdout.write(f"Media size: {self._format_size(backup_info['media_size'])}")
        
        self.stdout.write("\nModels:")
        for model_info in backup_info['models_backed_up']:
            self.stdout.write(
                f"  - {model_info['model']}: {model_info['count']} records"
            )
        
        self.stdout.write("="*50)