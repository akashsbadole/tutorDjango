"""
Django Tutor Platform Admin Portal User Verification Command

This management command handles user verification tasks.
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

from accounts.models import User, TutorProfile, StudentProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Handle user verification tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verify-tutors',
            action='store_true',
            help='Verify pending tutor applications',
            default=False
        )
        parser.add_argument(
            '--send-reminders',
            action='store_true',
            help='Send verification reminders to unverified users',
            default=False
        )
        parser.add_argument(
            '--cleanup-inactive',
            action='store_true',
            help='Clean up inactive unverified users',
            default=False
        )
        parser.add_argument(
            '--auto-verify',
            action='store_true',
            help='Auto-verify users with complete profiles',
            default=False
        )
        parser.add_argument(
            '--days',
            type=int,
            help='Number of days for inactivity threshold (default: 30)',
            default=30
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
            default=False
        )
    
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.days = options['days']
        self.inactivity_cutoff = now() - timedelta(days=self.days)
        
        self.stdout.write(self.style.SUCCESS('Starting user verification tasks...'))
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        verification_stats = {
            'tutors_verified': 0,
            'reminders_sent': 0,
            'users_cleaned': 0,
            'auto_verified': 0,
        }
        
        try:
            # Verify pending tutor applications
            if options['verify_tutors']:
                verification_stats['tutors_verified'] = self._verify_pending_tutors()
            
            # Send verification reminders
            if options['send_reminders']:
                verification_stats['reminders_sent'] = self._send_verification_reminders()
            
            # Clean up inactive users
            if options['cleanup_inactive']:
                verification_stats['users_cleaned'] = self._cleanup_inactive_users()
            
            # Auto-verify users
            if options['auto_verify']:
                verification_stats['auto_verified'] = self._auto_verify_users()
            
            # Print summary
            self._print_summary(verification_stats)
            
            self.stdout.write(
                self.style.SUCCESS('User verification tasks completed successfully')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Verification tasks failed: {str(e)}')
            )
    
    def _verify_pending_tutors(self):
        """Verify pending tutor applications"""
        self.stdout.write("Verifying pending tutor applications...")
        
        # Get tutors with pending verification
        pending_tutors = TutorProfile.objects.filter(
            verification_status='PENDING',
            is_verified=False
        ).select_related('user')
        
        verified_count = 0
        
        for tutor_profile in pending_tutors:
            # Check if tutor profile is complete
            if self._is_tutor_profile_complete(tutor_profile):
                if self.dry_run:
                    self.stdout.write(
                        f"  -> Would verify tutor: {tutor_profile.user.username}"
                    )
                else:
                    # Verify tutor
                    tutor_profile.is_verified = True
                    tutor_profile.verification_status = 'VERIFIED'
                    tutor_profile.verified_at = now()
                    tutor_profile.save()
                    
                    # Send verification email
                    self._send_tutor_verification_email(tutor_profile)
                    
                    self.stdout.write(
                        f"  -> Verified tutor: {tutor_profile.user.username}"
                    )
                
                verified_count += 1
            else:
                self.stdout.write(
                    f"  -> Tutor profile incomplete: {tutor_profile.user.username}"
                )
        
        self.stdout.write(f"  -> Verified {verified_count} tutors")
        return verified_count
    
    def _send_verification_reminders(self):
        """Send verification reminders to unverified users"""
        self.stdout.write("Sending verification reminders...")
        
        reminders_sent = 0
        
        # Get unverified users who haven't received a reminder recently
        reminder_cutoff = now() - timedelta(days=7)
        unverified_users = User.objects.filter(
            is_active=True,
            is_verified=False,
            last_login__gte=self.inactivity_cutoff
        ).exclude(
            id__in=User.objects.filter(
                notifications__type='VERIFICATION_REMINDER',
                notifications__created_at__gte=reminder_cutoff
            )
        )
        
        for user in unverified_users:
            if self.dry_run:
                self.stdout.write(
                    f"  -> Would send reminder to: {user.email}"
                )
            else:
                # Send reminder email
                self._send_verification_reminder_email(user)
                
                # Create notification record (simplified)
                # In a real implementation, you would use your notification system
                
                self.stdout.write(
                    f"  -> Sent reminder to: {user.email}"
                )
            
            reminders_sent += 1
        
        self.stdout.write(f"  -> Sent {reminders_sent} reminders")
        return reminders_sent
    
    def _cleanup_inactive_users(self):
        """Clean up inactive unverified users"""
        self.stdout.write("Cleaning up inactive unverified users...")
        
        # Get inactive unverified users
        inactive_users = User.objects.filter(
            is_verified=False,
            last_login__lt=self.inactivity_cutoff
        )
        
        cleaned_count = inactive_users.count()
        
        if self.dry_run:
            self.stdout.write(
                f"  -> Would delete {cleaned_count} inactive unverified users"
            )
        else:
            # Soft delete by deactivating
            inactive_users.update(is_active=False)
            
            self.stdout.write(
                f"  -> Deactivated {cleaned_count} inactive unverified users"
            )
        
        return cleaned_count
    
    def _auto_verify_users(self):
        """Auto-verify users with complete profiles"""
        self.stdout.write("Auto-verifying users with complete profiles...")
        
        auto_verified = 0
        
        # Get students with complete profiles
        students = StudentProfile.objects.filter(
            user__is_verified=False,
            user__is_active=True
        ).select_related('user')
        
        for student in students:
            if self._is_student_profile_complete(student):
                if self.dry_run:
                    self.stdout.write(
                        f"  -> Would auto-verify student: {student.user.username}"
                    )
                else:
                    # Verify student
                    student.user.is_verified = True
                    student.user.save()
                    
                    # Send verification email
                    self._send_auto_verification_email(student.user, 'student')
                    
                    self.stdout.write(
                        f"  -> Auto-verified student: {student.user.username}"
                    )
                
                auto_verified += 1
        
        # Get tutors with complete profiles
        tutors = TutorProfile.objects.filter(
            user__is_verified=False,
            user__is_active=True,
            verification_status='PENDING'
        ).select_related('user')
        
        for tutor in tutors:
            if self._is_tutor_profile_complete(tutor):
                if self.dry_run:
                    self.stdout.write(
                        f"  -> Would auto-verify tutor: {tutor.user.username}"
                    )
                else:
                    # Verify tutor
                    tutor.is_verified = True
                    tutor.verification_status = 'VERIFIED'
                    tutor.verified_at = now()
                    tutor.save()
                    
                    tutor.user.is_verified = True
                    tutor.user.save()
                    
                    # Send verification email
                    self._send_auto_verification_email(tutor.user, 'tutor')
                    
                    self.stdout.write(
                        f"  -> Auto-verified tutor: {tutor.user.username}"
                    )
                
                auto_verified += 1
        
        self.stdout.write(f"  -> Auto-verified {auto_verified} users")
        return auto_verified
    
    def _is_tutor_profile_complete(self, tutor_profile):
        """Check if tutor profile is complete"""
        required_fields = [
            tutor_profile.bio,
            tutor_profile.education,
            tutor_profile.experience,
            tutor_profile.hourly_rate,
            tutor_profile.user.first_name,
            tutor_profile.user.last_name,
        ]
        
        # Check if all required fields are filled
        if not all(required_fields):
            return False
        
        # Check if tutor has at least one subject
        if not tutor_profile.subjects.exists():
            return False
        
        # Check if tutor has profile picture (optional but recommended)
        # if not tutor_profile.profile_picture:
        #     return False
        
        return True
    
    def _is_student_profile_complete(self, student_profile):
        """Check if student profile is complete"""
        required_fields = [
            student_profile.user.first_name,
            student_profile.user.last_name,
        ]
        
        # Check if all required fields are filled
        if not all(required_fields):
            return False
        
        return True
    
    def _send_tutor_verification_email(self, tutor_profile):
        """Send tutor verification email"""
        try:
            subject = 'Tutor Application Approved'
            
            context = {
                'user': tutor_profile.user,
                'tutor_profile': tutor_profile,
                'site_name': getattr(settings, 'SITE_NAME', 'Django Tutor Platform'),
            }
            
            message = render_to_string(
                'admin_portal/emails/tutor_verified.html',
                context
            )
            
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tutorplatform.com'),
                recipient_list=[tutor_profile.user.email],
                html_message=message,
                fail_silently=False
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to send verification email to {tutor_profile.user.email}: {str(e)}"
                )
            )
    
    def _send_verification_reminder_email(self, user):
        """Send verification reminder email"""
        try:
            subject = 'Complete Your Profile Verification'
            
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'Django Tutor Platform'),
            }
            
            message = render_to_string(
                'admin_portal/emails/verification_reminder.html',
                context
            )
            
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tutorplatform.com'),
                recipient_list=[user.email],
                html_message=message,
                fail_silently=False
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to send reminder email to {user.email}: {str(e)}"
                )
            )
    
    def _send_auto_verification_email(self, user, user_type):
        """Send auto-verification email"""
        try:
            subject = f'Your {user_type.title()} Profile Has Been Verified'
            
            context = {
                'user': user,
                'user_type': user_type,
                'site_name': getattr(settings, 'SITE_NAME', 'Django Tutor Platform'),
            }
            
            message = render_to_string(
                'admin_portal/emails/auto_verified.html',
                context
            )
            
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tutorplatform.com'),
                recipient_list=[user.email],
                html_message=message,
                fail_silently=False
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to send auto-verification email to {user.email}: {str(e)}"
                )
            )
    
    def _print_summary(self, stats):
        """Print verification summary"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("VERIFICATION SUMMARY")
        self.stdout.write("="*50)
        self.stdout.write(f"Tutors verified: {stats['tutors_verified']}")
        self.stdout.write(f"Reminders sent: {stats['reminders_sent']}")
        self.stdout.write(f"Users cleaned up: {stats['users_cleaned']}")
        self.stdout.write(f"Auto-verified: {stats['auto_verified']}")
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING("\nDRY RUN MODE - No actual changes were made")
            )
        
        self.stdout.write("="*50)