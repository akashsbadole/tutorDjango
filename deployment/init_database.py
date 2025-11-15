#!/usr/bin/env python
"""
Database initialization script for Django Tutoring Platform.
This script sets up the initial database with required data.
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

# Add the project directory to the Python path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deployment.production_settings')

# Setup Django
django.setup()

# Import models after Django setup
try:
    # Try importing from the tutor_platform package
    from tutor_platform.accounts.models import StudentProfile, TutorProfile, Subject
    from tutor_platform.notifications.models import NotificationType
except ImportError:
    try:
        # Fallback for when running from the project root
        from accounts.models import StudentProfile, TutorProfile
        from requirements.models import Subject
        from notifications.models import NotificationType
    except ImportError as e:
        print(f"Error importing models: {e}")
        print("Please ensure you're running this script from the correct directory.")
        print("Current Python path:", sys.path)
        sys.exit(1)

User = get_user_model()


def create_superuser():
    """Create a superuser for admin access."""
    print("Creating superuser...")
    
    username = os.environ.get('SUPERUSER_USERNAME', 'admin')
    email = os.environ.get('SUPERUSER_EMAIL', 'admin@tutorplatform.com')
    password = os.environ.get('SUPERUSER_PASSWORD', 'admin123')
    
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            first_name='Admin',
            last_name='User'
        )
        print(f"Superuser '{username}' created successfully.")
    else:
        print(f"Superuser '{username}' already exists.")


def create_notification_types():
    """Create default notification types."""
    print("Creating notification types...")
    
    default_types = [
        {
            'name': 'new_proposal',
            'display_name': 'New Proposal',
            'description': 'A tutor has submitted a proposal for your requirement'
        },
        {
            'name': 'proposal_accepted',
            'display_name': 'Proposal Accepted',
            'description': 'Your proposal has been accepted by the student'
        },
        {
            'name': 'requirement_awarded',
            'display_name': 'Requirement Awarded',
            'description': 'Your requirement has been awarded to a tutor'
        },
        {
            'name': 'message_received',
            'display_name': 'New Message',
            'description': 'You have received a new message'
        },
        {
            'name': 'payment_received',
            'display_name': 'Payment Received',
            'description': 'A payment has been received for your tutoring session'
        },
        {
            'name': 'class_reminder',
            'display_name': 'Class Reminder',
            'description': 'Reminder about an upcoming tutoring session'
        },
        {
            'name': 'class_completed',
            'display_name': 'Class Completed',
            'description': 'A tutoring session has been completed'
        },
        {
            'name': 'profile_updated',
            'display_name': 'Profile Updated',
            'description': 'Your profile has been successfully updated'
        }
    ]
    
    for type_data in default_types:
        notification_type, created = NotificationType.objects.get_or_create(
            name=type_data['name'],
            defaults={
                'display_name': type_data['display_name'],
                'description': type_data['description']
            }
        )
        if created:
            print(f"Created notification type: {type_data['display_name']}")
        else:
            print(f"Notification type already exists: {type_data['display_name']}")


def create_subjects():
    """Create default subjects and categories."""
    print("Creating subjects...")
    
    subjects_data = [
        {
            'name': 'Mathematics',
            'description': 'Mathematics and related subjects',
            'children': [
                {
                    'name': 'Algebra',
                    'description': 'Algebraic concepts and problem solving',
                    'children': [
                        {'name': 'Linear Algebra', 'description': 'Linear equations and matrices'},
                        {'name': 'Abstract Algebra', 'description': 'Algebraic structures and theory'},
                        {'name': 'Elementary Algebra', 'description': 'Basic algebraic concepts'}
                    ]
                },
                {
                    'name': 'Calculus',
                    'description': 'Differential and integral calculus',
                    'children': [
                        {'name': 'Differential Calculus', 'description': 'Derivatives and rates of change'},
                        {'name': 'Integral Calculus', 'description': 'Integration and area'},
                        {'name': 'Multivariable Calculus', 'description': 'Calculus with multiple variables'}
                    ]
                },
                {
                    'name': 'Statistics',
                    'description': 'Statistical analysis and probability',
                    'children': [
                        {'name': 'Descriptive Statistics', 'description': 'Data summarization and visualization'},
                        {'name': 'Inferential Statistics', 'description': 'Hypothesis testing and inference'},
                        {'name': 'Probability Theory', 'description': 'Mathematical probability'}
                    ]
                },
                {
                    'name': 'Geometry',
                    'description': 'Geometric concepts and spatial reasoning',
                    'children': [
                        {'name': 'Euclidean Geometry', 'description': 'Classical geometry'},
                        {'name': 'Analytic Geometry', 'description': 'Coordinate geometry'},
                        {'name': 'Topology', 'description': 'Properties of space'}
                    ]
                }
            ]
        },
        {
            'name': 'Science',
            'description': 'Natural sciences',
            'children': [
                {
                    'name': 'Physics',
                    'description': 'Physical laws and phenomena',
                    'children': [
                        {'name': 'Classical Mechanics', 'description': 'Motion and forces'},
                        {'name': 'Quantum Mechanics', 'description': 'Atomic and subatomic physics'},
                        {'name': 'Thermodynamics', 'description': 'Heat and energy'},
                        {'name': 'Electromagnetism', 'description': 'Electricity and magnetism'}
                    ]
                },
                {
                    'name': 'Chemistry',
                    'description': 'Chemical reactions and properties',
                    'children': [
                        {'name': 'Organic Chemistry', 'description': 'Carbon-based compounds'},
                        {'name': 'Inorganic Chemistry', 'description': 'Non-organic compounds'},
                        {'name': 'Physical Chemistry', 'description': 'Chemical physics'},
                        {'name': 'Analytical Chemistry', 'description': 'Chemical analysis'}
                    ]
                },
                {
                    'name': 'Biology',
                    'description': 'Life sciences',
                    'children': [
                        {'name': 'Molecular Biology', 'description': 'Molecular processes in living organisms'},
                        {'name': 'Cell Biology', 'description': 'Cell structure and function'},
                        {'name': 'Genetics', 'description': 'Heredity and genetic variation'},
                        {'name': 'Ecology', 'description': 'Organisms and their environment'}
                    ]
                }
            ]
        },
        {
            'name': 'Computer Science',
            'description': 'Computer science and programming',
            'children': [
                {
                    'name': 'Programming Languages',
                    'description': 'Programming and software development',
                    'children': [
                        {'name': 'Python', 'description': 'Python programming language'},
                        {'name': 'JavaScript', 'description': 'JavaScript programming language'},
                        {'name': 'Java', 'description': 'Java programming language'},
                        {'name': 'C++', 'description': 'C++ programming language'}
                    ]
                },
                {
                    'name': 'Web Development',
                    'description': 'Web application development',
                    'children': [
                        {'name': 'Frontend Development', 'description': 'Client-side web development'},
                        {'name': 'Backend Development', 'description': 'Server-side web development'},
                        {'name': 'Full Stack Development', 'description': 'End-to-end web development'}
                    ]
                },
                {
                    'name': 'Data Science',
                    'description': 'Data analysis and machine learning',
                    'children': [
                        {'name': 'Machine Learning', 'description': 'Algorithms and models for learning from data'},
                        {'name': 'Data Analysis', 'description': 'Processing and analyzing data'},
                        {'name': 'Data Visualization', 'description': 'Visual representation of data'}
                    ]
                }
            ]
        },
        {
            'name': 'Languages',
            'description': 'Language learning and communication',
            'children': [
                {
                    'name': 'English',
                    'description': 'English language learning',
                    'children': [
                        {'name': 'English Grammar', 'description': 'English grammar and syntax'},
                        {'name': 'English Writing', 'description': 'English writing skills'},
                        {'name': 'English Speaking', 'description': 'English speaking and pronunciation'}
                    ]
                },
                {
                    'name': 'Spanish',
                    'description': 'Spanish language learning',
                    'children': [
                        {'name': 'Spanish Grammar', 'description': 'Spanish grammar and syntax'},
                        {'name': 'Spanish Writing', 'description': 'Spanish writing skills'},
                        {'name': 'Spanish Speaking', 'description': 'Spanish speaking and pronunciation'}
                    ]
                },
                {
                    'name': 'French',
                    'description': 'French language learning',
                    'children': [
                        {'name': 'French Grammar', 'description': 'French grammar and syntax'},
                        {'name': 'French Writing', 'description': 'French writing skills'},
                        {'name': 'French Speaking', 'description': 'French speaking and pronunciation'}
                    ]
                }
            ]
        },
        {
            'name': 'Business',
            'description': 'Business and management studies',
            'children': [
                {
                    'name': 'Finance',
                    'description': 'Financial management and analysis',
                    'children': [
                        {'name': 'Corporate Finance', 'description': 'Corporate financial management'},
                        {'name': 'Investment Analysis', 'description': 'Investment strategies and analysis'},
                        {'name': 'Financial Accounting', 'description': 'Financial reporting and accounting'}
                    ]
                },
                {
                    'name': 'Marketing',
                    'description': 'Marketing and brand management',
                    'children': [
                        {'name': 'Digital Marketing', 'description': 'Online marketing strategies'},
                        {'name': 'Brand Management', 'description': 'Brand development and management'},
                        {'name': 'Market Research', 'description': 'Market analysis and research'}
                    ]
                },
                {
                    'name': 'Management',
                    'description': 'Business management and leadership',
                    'children': [
                        {'name': 'Strategic Management', 'description': 'Business strategy and planning'},
                        {'name': 'Project Management', 'description': 'Project planning and execution'},
                        {'name': 'Human Resources', 'description': 'People management and HR'}
                    ]
                }
            ]
        }
    ]
    
    def create_subject_hierarchy(subject_data, parent=None):
        """Recursively create subject hierarchy."""
        subject, created = Subject.objects.get_or_create(
            name=subject_data['name'],
            defaults={
                'description': subject_data['description'],
                'parent': parent
            }
        )
        
        if created:
            print(f"Created subject: {subject_data['name']}")
        else:
            print(f"Subject already exists: {subject_data['name']}")
        
        if 'children' in subject_data:
            for child_data in subject_data['children']:
                create_subject_hierarchy(child_data, subject)
    
    for subject_data in subjects_data:
        create_subject_hierarchy(subject_data)


def run_migrations():
    """Run Django migrations."""
    print("Running database migrations...")
    execute_from_command_line(['manage.py', 'migrate', '--settings=deployment.production_settings'])
    print("Migrations completed.")


def collect_static():
    """Collect static files."""
    print("Collecting static files...")
    execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--settings=deployment.production_settings'])
    print("Static files collected.")


def main():
    """Main function to initialize the database."""
    print("Initializing Django Tutoring Platform database...")
    
    try:
        with transaction.atomic():
            # Run migrations first
            run_migrations()
            
            # Create initial data
            create_superuser()
            create_notification_types()
            create_subjects()
            
            # Collect static files
            collect_static()
            
            print("\nDatabase initialization completed successfully!")
            print("You can now access the admin panel at /admin/")
            
    except Exception as e:
        print(f"\nError during database initialization: {str(e)}")
        sys.exit(1)


if __name__ == '__main__':
    main()