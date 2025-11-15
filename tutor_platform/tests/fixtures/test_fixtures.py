"""
Test data fixtures for Django tutoring platform.
"""
import json
import os
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


def create_user_fixtures():
    """Create user fixtures for different roles."""
    fixtures = {
        'students': [
            {
                'username': 'student1',
                'email': 'student1@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'password': 'testpass123',
                'user_type': 'STUDENT',
                'bio': 'Computer science student looking for tutoring help.',
                'phone': '+12345678901',
                'location': 'New York, USA'
            },
            {
                'username': 'student2',
                'email': 'student2@example.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'password': 'testpass123',
                'user_type': 'STUDENT',
                'bio': 'Mathematics student seeking help with calculus.',
                'phone': '+12345678902',
                'location': 'Los Angeles, USA'
            },
            {
                'username': 'student3',
                'email': 'student3@example.com',
                'first_name': 'Mike',
                'last_name': 'Johnson',
                'password': 'testpass123',
                'user_type': 'STUDENT',
                'bio': 'Physics student needing help with quantum mechanics.',
                'phone': '+12345678903',
                'location': 'Chicago, USA'
            }
        ],
        'tutors': [
            {
                'username': 'tutor1',
                'email': 'tutor1@example.com',
                'first_name': 'Dr. Sarah',
                'last_name': 'Williams',
                'password': 'testpass123',
                'user_type': 'TUTOR',
                'bio': 'PhD in Computer Science with 10 years of teaching experience.',
                'phone': '+12345678911',
                'location': 'Boston, USA',
                'hourly_rate': 50.00,
                'education': 'PhD in Computer Science, MIT',
                'experience': '10 years teaching programming and algorithms',
                'subjects': ['Python', 'Java', 'Data Structures', 'Algorithms']
            },
            {
                'username': 'tutor2',
                'email': 'tutor2@example.com',
                'first_name': 'Prof. Robert',
                'last_name': 'Brown',
                'password': 'testpass123',
                'user_type': 'TUTOR',
                'bio': 'Mathematics professor specializing in calculus and linear algebra.',
                'phone': '+12345678912',
                'location': 'San Francisco, USA',
                'hourly_rate': 60.00,
                'education': 'PhD in Mathematics, Stanford',
                'experience': '15 years teaching mathematics at university level',
                'subjects': ['Calculus', 'Linear Algebra', 'Statistics', 'Differential Equations']
            },
            {
                'username': 'tutor3',
                'email': 'tutor3@example.com',
                'first_name': 'Dr. Emily',
                'last_name': 'Davis',
                'password': 'testpass123',
                'user_type': 'TUTOR',
                'bio': 'Physics expert with research background in quantum mechanics.',
                'phone': '+12345678913',
                'location': 'Seattle, USA',
                'hourly_rate': 70.00,
                'education': 'PhD in Physics, Caltech',
                'experience': '12 years teaching physics and conducting research',
                'subjects': ['Quantum Mechanics', 'Thermodynamics', 'Electromagnetism', 'Relativity']
            }
        ],
        'admins': [
            {
                'username': 'admin1',
                'email': 'admin1@example.com',
                'first_name': 'Admin',
                'last_name': 'User',
                'password': 'testpass123',
                'user_type': 'ADMIN',
                'bio': 'System administrator',
                'phone': '+12345678921',
                'location': 'Remote'
            }
        ]
    }
    
    # Save fixtures to JSON file
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'json')
    os.makedirs(fixtures_dir, exist_ok=True)
    
    with open(os.path.join(fixtures_dir, 'users.json'), 'w') as f:
        json.dump(fixtures, f, indent=2)
    
    return fixtures


def create_subject_category_fixtures():
    """Create subject and category fixtures."""
    fixtures = {
        'categories': [
            {
                'name': 'Computer Science',
                'description': 'Programming, algorithms, and computer science concepts',
                'icon': 'computer'
            },
            {
                'name': 'Mathematics',
                'description': 'All levels of mathematics from basic to advanced',
                'icon': 'calculator'
            },
            {
                'name': 'Physics',
                'description': 'Classical and modern physics topics',
                'icon': 'atom'
            },
            {
                'name': 'Chemistry',
                'description': 'Organic, inorganic, and physical chemistry',
                'icon': 'flask'
            },
            {
                'name': 'Languages',
                'description': 'Foreign languages and literature',
                'icon': 'book'
            }
        ],
        'subjects': [
            {
                'name': 'Python Programming',
                'description': 'Learn Python from basics to advanced topics',
                'category': 'Computer Science',
                'difficulty': 'Beginner to Advanced'
            },
            {
                'name': 'Java Programming',
                'description': 'Object-oriented programming with Java',
                'category': 'Computer Science',
                'difficulty': 'Intermediate to Advanced'
            },
            {
                'name': 'Data Structures',
                'description': 'Arrays, linked lists, trees, and graphs',
                'category': 'Computer Science',
                'difficulty': 'Intermediate'
            },
            {
                'name': 'Algorithms',
                'description': 'Sorting, searching, and algorithmic complexity',
                'category': 'Computer Science',
                'difficulty': 'Advanced'
            },
            {
                'name': 'Calculus I',
                'description': 'Limits, derivatives, and basic integration',
                'category': 'Mathematics',
                'difficulty': 'Intermediate'
            },
            {
                'name': 'Calculus II',
                'description': 'Advanced integration techniques and series',
                'category': 'Mathematics',
                'difficulty': 'Advanced'
            },
            {
                'name': 'Linear Algebra',
                'description': 'Matrices, vectors, and linear transformations',
                'category': 'Mathematics',
                'difficulty': 'Intermediate'
            },
            {
                'name': 'Statistics',
                'description': 'Probability, distributions, and statistical analysis',
                'category': 'Mathematics',
                'difficulty': 'Intermediate'
            },
            {
                'name': 'Quantum Mechanics',
                'description': 'Wave functions, uncertainty principle, and quantum states',
                'category': 'Physics',
                'difficulty': 'Advanced'
            },
            {
                'name': 'Thermodynamics',
                'description': 'Heat, energy, and laws of thermodynamics',
                'category': 'Physics',
                'difficulty': 'Intermediate'
            },
            {
                'name': 'Spanish',
                'description': 'Learn Spanish from beginner to advanced level',
                'category': 'Languages',
                'difficulty': 'Beginner to Advanced'
            }
        ]
    }
    
    # Save fixtures to JSON file
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'json')
    os.makedirs(fixtures_dir, exist_ok=True)
    
    with open(os.path.join(fixtures_dir, 'subjects_categories.json'), 'w') as f:
        json.dump(fixtures, f, indent=2)
    
    return fixtures


def create_requirement_proposal_fixtures():
    """Create requirement and proposal fixtures."""
    fixtures = {
        'requirements': [
            {
                'title': 'Help with Python Data Structures',
                'description': 'I need help understanding linked lists, trees, and graphs in Python. Looking for someone who can explain concepts clearly and provide practical examples.',
                'budget': 50.00,
                'deadline': (timezone.now() + timedelta(days=7)).isoformat(),
                'status': 'open',
                'created_by': 'student1',
                'category': 'Computer Science',
                'subject': 'Data Structures',
                'difficulty': 'Intermediate',
                'duration_weeks': 2,
                'hours_per_week': 3
            },
            {
                'title': 'Calculus II Tutoring Needed',
                'description': 'Struggling with advanced integration techniques and series. Need help preparing for midterm exam in 3 weeks.',
                'budget': 60.00,
                'deadline': (timezone.now() + timedelta(days=21)).isoformat(),
                'status': 'open',
                'created_by': 'student2',
                'category': 'Mathematics',
                'subject': 'Calculus II',
                'difficulty': 'Advanced',
                'duration_weeks': 3,
                'hours_per_week': 4
            },
            {
                'title': 'Quantum Mechanics Problem Set',
                'description': 'Need help with problem set on wave functions and uncertainty principle. Looking for someone with strong physics background.',
                'budget': 70.00,
                'deadline': (timezone.now() + timedelta(days=5)).isoformat(),
                'status': 'open',
                'created_by': 'student3',
                'category': 'Physics',
                'subject': 'Quantum Mechanics',
                'difficulty': 'Advanced',
                'duration_weeks': 1,
                'hours_per_week': 5
            }
        ],
        'proposals': [
            {
                'title': 'Python Data Structures Tutoring',
                'description': 'I can help you understand data structures with clear explanations and practical coding examples. I have 10 years of experience teaching programming.',
                'hourly_rate': 50.00,
                'availability': 'Weekdays after 6 PM, weekends flexible',
                'teaching_style': 'Interactive with hands-on coding exercises',
                'tutor': 'tutor1',
                'requirement': 'Help with Python Data Structures',
                'status': 'pending'
            },
            {
                'title': 'Calculus II Expert Tutor',
                'description': 'PhD in Mathematics with 15 years teaching experience. I can help you master integration techniques and prepare for your exam.',
                'hourly_rate': 60.00,
                'availability': 'Evenings and weekends',
                'teaching_style': 'Problem-solving focused with step-by-step explanations',
                'tutor': 'tutor2',
                'requirement': 'Calculus II Tutoring Needed',
                'status': 'pending'
            },
            {
                'title': 'Quantum Physics Specialist',
                'description': 'I specialize in quantum mechanics and can help with wave functions and uncertainty principle. Research background in quantum computing.',
                'hourly_rate': 70.00,
                'availability': 'Flexible schedule',
                'teaching_style': 'Conceptual understanding with mathematical rigor',
                'tutor': 'tutor3',
                'requirement': 'Quantum Mechanics Problem Set',
                'status': 'pending'
            }
        ]
    }
    
    # Save fixtures to JSON file
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'json')
    os.makedirs(fixtures_dir, exist_ok=True)
    
    with open(os.path.join(fixtures_dir, 'requirements_proposals.json'), 'w') as f:
        json.dump(fixtures, f, indent=2)
    
    return fixtures


def create_payment_transaction_fixtures():
    """Create payment and transaction fixtures."""
    fixtures = {
        'payments': [
            {
                'student': 'student1',
                'tutor': 'tutor1',
                'amount': 300.00,
                'status': 'completed',
                'payment_method': 'paypal',
                'transaction_id': 'PAY-123456789',
                'created_at': (timezone.now() - timedelta(days=10)).isoformat(),
                'completed_at': (timezone.now() - timedelta(days=9)).isoformat()
            },
            {
                'student': 'student2',
                'tutor': 'tutor2',
                'amount': 720.00,
                'status': 'completed',
                'payment_method': 'credit_card',
                'transaction_id': 'TXN-987654321',
                'created_at': (timezone.now() - timedelta(days=5)).isoformat(),
                'completed_at': (timezone.now() - timedelta(days=4)).isoformat()
            },
            {
                'student': 'student3',
                'tutor': 'tutor3',
                'amount': 350.00,
                'status': 'pending',
                'payment_method': 'bank_transfer',
                'transaction_id': None,
                'created_at': (timezone.now() - timedelta(days=1)).isoformat(),
                'completed_at': None
            }
        ],
        'escrow_transactions': [
            {
                'payment': 'PAY-123456789',
                'transaction_type': 'funding',
                'amount': 300.00,
                'status': 'completed',
                'created_at': (timezone.now() - timedelta(days=9)).isoformat(),
                'completed_at': (timezone.now() - timedelta(days=8)).isoformat()
            },
            {
                'payment': 'PAY-123456789',
                'transaction_type': 'release',
                'amount': 270.00,
                'status': 'completed',
                'created_at': (timezone.now() - timedelta(days=2)).isoformat(),
                'completed_at': (timezone.now() - timedelta(days=1)).isoformat()
            },
            {
                'payment': 'TXN-987654321',
                'transaction_type': 'funding',
                'amount': 720.00,
                'status': 'completed',
                'created_at': (timezone.now() - timedelta(days=4)).isoformat(),
                'completed_at': (timezone.now() - timedelta(days=3)).isoformat()
            }
        ],
        'payouts': [
            {
                'tutor': 'tutor1',
                'amount': 270.00,
                'payout_method': 'bank_transfer',
                'status': 'completed',
                'transaction_id': 'PAYOUT-111111',
                'created_at': (timezone.now() - timedelta(days=1)).isoformat(),
                'completed_at': (timezone.now() - timedelta(days=1)).isoformat()
            },
            {
                'tutor': 'tutor2',
                'amount': 648.00,
                'payout_method': 'paypal',
                'status': 'pending',
                'transaction_id': None,
                'created_at': (timezone.now() - timedelta(days=1)).isoformat(),
                'completed_at': None
            }
        ]
    }
    
    # Save fixtures to JSON file
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'json')
    os.makedirs(fixtures_dir, exist_ok=True)
    
    with open(os.path.join(fixtures_dir, 'payments_transactions.json'), 'w') as f:
        json.dump(fixtures, f, indent=2)
    
    return fixtures


def create_message_notification_fixtures():
    """Create message and notification fixtures."""
    fixtures = {
        'conversations': [
            {
                'id': 1,
                'participants': ['student1', 'tutor1'],
                'created_at': (timezone.now() - timedelta(days=5)).isoformat(),
                'updated_at': (timezone.now() - timedelta(days=1)).isoformat()
            },
            {
                'id': 2,
                'participants': ['student2', 'tutor2'],
                'created_at': (timezone.now() - timedelta(days=3)).isoformat(),
                'updated_at': (timezone.now() - timedelta(days=2)).isoformat()
            },
            {
                'id': 3,
                'participants': ['student3', 'tutor3'],
                'created_at': (timezone.now() - timedelta(days=7)).isoformat(),
                'updated_at': (timezone.now() - timedelta(days=6)).isoformat()
            }
        ],
        'messages': [
            {
                'conversation': 1,
                'sender': 'student1',
                'content': 'Hi, I need help with Python data structures. Are you available this week?',
                'created_at': (timezone.now() - timedelta(days=5)).isoformat(),
                'is_read': True
            },
            {
                'conversation': 1,
                'sender': 'tutor1',
                'content': 'Hello! Yes, I\'m available to help with Python data structures. I can explain linked lists, trees, and graphs with practical examples.',
                'created_at': (timezone.now() - timedelta(days=4)).isoformat(),
                'is_read': True
            },
            {
                'conversation': 1,
                'sender': 'student1',
                'content': 'Great! What times work best for you? I\'m available weekday evenings.',
                'created_at': (timezone.now() - timedelta(days=3)).isoformat(),
                'is_read': True
            },
            {
                'conversation': 1,
                'sender': 'tutor1',
                'content': 'Weekday evenings after 6 PM work well for me. Shall we schedule a session for tomorrow at 7 PM?',
                'created_at': (timezone.now() - timedelta(days=2)).isoformat(),
                'is_read': True
            },
            {
                'conversation': 1,
                'sender': 'student1',
                'content': 'Perfect! Tomorrow at 7 PM works for me. Looking forward to the session.',
                'created_at': (timezone.now() - timedelta(days=1)).isoformat(),
                'is_read': True
            }
        ],
        'notifications': [
            {
                'user': 'student1',
                'notification_type': 'new_message',
                'title': 'New message from tutor1',
                'message': 'tutor1 sent you a message about Python data structures tutoring.',
                'is_read': False,
                'created_at': (timezone.now() - timedelta(hours=2)).isoformat()
            },
            {
                'user': 'tutor1',
                'notification_type': 'new_proposal',
                'title': 'New proposal received',
                'message': 'student1 has accepted your proposal for Python data structures tutoring.',
                'is_read': True,
                'created_at': (timezone.now() - timedelta(days=1)).isoformat()
            },
            {
                'user': 'student2',
                'notification_type': 'payment_required',
                'title': 'Payment required',
                'message': 'Please complete your payment for Calculus II tutoring sessions.',
                'is_read': False,
                'created_at': (timezone.now() - timedelta(hours=6)).isoformat()
            },
            {
                'user': 'tutor2',
                'notification_type': 'session_reminder',
                'title': 'Session reminder',
                'message': 'You have a tutoring session with student2 tomorrow at 5 PM.',
                'is_read': False,
                'created_at': (timezone.now() - timedelta(hours=12)).isoformat()
            }
        ]
    }
    
    # Save fixtures to JSON file
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'json')
    os.makedirs(fixtures_dir, exist_ok=True)
    
    with open(os.path.join(fixtures_dir, 'messages_notifications.json'), 'w') as f:
        json.dump(fixtures, f, indent=2)
    
    return fixtures


def create_session_fixtures():
    """Create online class session fixtures."""
    fixtures = {
        'sessions': [
            {
                'requirement': 'Help with Python Data Structures',
                'proposal': 'Python Data Structures Tutoring',
                'tutor': 'tutor1',
                'student': 'student1',
                'scheduled_time': (timezone.now() + timedelta(days=1)).isoformat(),
                'duration_minutes': 60,
                'status': 'scheduled',
                'platform': 'zoom',
                'meeting_url': 'https://zoom.us/j/123456789',
                'meeting_id': '123456789',
                'password': 'abc123'
            },
            {
                'requirement': 'Calculus II Tutoring Needed',
                'proposal': 'Calculus II Expert Tutor',
                'tutor': 'tutor2',
                'student': 'student2',
                'scheduled_time': (timezone.now() - timedelta(days=2)).isoformat(),
                'duration_minutes': 90,
                'status': 'completed',
                'platform': 'skype',
                'meeting_url': 'https://join.skype.com/987654321',
                'meeting_id': '987654321',
                'password': 'def456'
            },
            {
                'requirement': 'Quantum Mechanics Problem Set',
                'proposal': 'Quantum Physics Specialist',
                'tutor': 'tutor3',
                'student': 'student3',
                'scheduled_time': (timezone.now() + timedelta(days=3)).isoformat(),
                'duration_minutes': 120,
                'status': 'scheduled',
                'platform': 'google_meet',
                'meeting_url': 'https://meet.google.com/555666777',
                'meeting_id': '555666777',
                'password': 'ghi789'
            }
        ]
    }
    
    # Save fixtures to JSON file
    fixtures_dir = os.path.join(os.path.dirname(__file__), 'json')
    os.makedirs(fixtures_dir, exist_ok=True)
    
    with open(os.path.join(fixtures_dir, 'sessions.json'), 'w') as f:
        json.dump(fixtures, f, indent=2)
    
    return fixtures


def create_all_fixtures():
    """Create all test fixtures."""
    print("Creating user fixtures...")
    create_user_fixtures()
    
    print("Creating subject and category fixtures...")
    create_subject_category_fixtures()
    
    print("Creating requirement and proposal fixtures...")
    create_requirement_proposal_fixtures()
    
    print("Creating payment and transaction fixtures...")
    create_payment_transaction_fixtures()
    
    print("Creating message and notification fixtures...")
    create_message_notification_fixtures()
    
    print("Creating session fixtures...")
    create_session_fixtures()
    
    print("All fixtures created successfully!")


if __name__ == '__main__':
    create_all_fixtures()