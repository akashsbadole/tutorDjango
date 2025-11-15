"""
Django management command to generate test data.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tests.factories import (
    UserFactory, TutorProfileFactory, StudentProfileFactory, CategoryFactory,
    SubjectFactory, RequirementFactory, ProposalFactory, PaymentFactory,
    ConversationFactory, MessageFactory, NotificationFactory
)
from tests.fixtures.test_fixtures import (
    create_user_fixtures, create_subject_category_fixtures,
    create_requirement_proposal_fixtures, create_payment_transaction_fixtures,
    create_message_notification_fixtures, create_session_fixtures
)

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate test data for the Django tutoring platform'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users to create'
        )
        parser.add_argument(
            '--requirements',
            type=int,
            default=20,
            help='Number of requirements to create'
        )
        parser.add_argument(
            '--proposals',
            type=int,
            default=40,
            help='Number of proposals to create'
        )
        parser.add_argument(
            '--payments',
            type=int,
            default=30,
            help='Number of payments to create'
        )
        parser.add_argument(
            '--messages',
            type=int,
            default=100,
            help='Number of messages to create'
        )
        parser.add_argument(
            '--notifications',
            type=int,
            default=50,
            help='Number of notifications to create'
        )
        parser.add_argument(
            '--use-fixtures',
            action='store_true',
            help='Use predefined fixtures instead of random generation'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before generating new data'
        )
        
    def handle(self, *args, **options):
        """Generate test data."""
        if options['clear']:
            self.clear_existing_data()
            
        if options['use_fixtures']:
            self.generate_from_fixtures()
        else:
            self.generate_random_data(options)
            
    def clear_existing_data(self):
        """Clear existing test data."""
        self.stdout.write(self.style.WARNING('Clearing existing test data...'))
        
        # Clear data in reverse order of dependencies
        NotificationFactory._meta.model.objects.all().delete()
        MessageFactory._meta.model.objects.all().delete()
        ConversationFactory._meta.model.objects.all().delete()
        PaymentFactory._meta.model.objects.all().delete()
        ProposalFactory._meta.model.objects.all().delete()
        RequirementFactory._meta.model.objects.all().delete()
        SubjectFactory._meta.model.objects.all().delete()
        CategoryFactory._meta.model.objects.all().delete()
        TutorProfileFactory._meta.model.objects.all().delete()
        StudentProfileFactory._meta.model.objects.all().delete()
        User.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('Existing data cleared successfully'))
        
    def generate_from_fixtures(self):
        """Generate test data from predefined fixtures."""
        self.stdout.write(self.style.SUCCESS('Generating test data from fixtures...'))
        
        # Create all fixtures
        create_user_fixtures()
        create_subject_category_fixtures()
        create_requirement_proposal_fixtures()
        create_payment_transaction_fixtures()
        create_message_notification_fixtures()
        create_session_fixtures()
        
        self.stdout.write(self.style.SUCCESS('Test data generated from fixtures successfully'))
        
    def generate_random_data(self, options):
        """Generate random test data."""
        self.stdout.write(self.style.SUCCESS('Generating random test data...'))
        
        # Create categories and subjects
        self.stdout.write('Creating categories and subjects...')
        categories = CategoryFactory.create_batch(5)
        subjects = []
        for category in categories:
            subjects.extend(SubjectFactory.create_batch(3, category=category))
            
        # Create users
        self.stdout.write(f'Creating {options["users"]} users...')
        students = StudentProfileFactory.create_batch(options['users'] // 2)
        tutors = TutorProfileFactory.create_batch(options['users'] // 2)
        
        # Create requirements
        self.stdout.write(f'Creating {options["requirements"]} requirements...')
        requirements = RequirementFactory.create_batch(
            options['requirements'],
            created_by=lambda: students[0]  # Use first student for all requirements
        )
        
        # Create proposals
        self.stdout.write(f'Creating {options["proposals"]} proposals...')
        proposals = []
        for i in range(options['proposals']):
            requirement = requirements[i % len(requirements)]
            tutor = tutors[i % len(tutors)]
            proposals.append(ProposalFactory.create(requirement=requirement, tutor=tutor))
            
        # Create payments
        self.stdout.write(f'Creating {options["payments"]} payments...')
        for i in range(options['payments']):
            if i < len(proposals):
                PaymentFactory.create(
                    proposal=proposals[i],
                    student=proposals[i].requirement.created_by,
                    tutor=proposals[i].tutor
                )
                
        # Create conversations
        self.stdout.write(f'Creating conversations...')
        conversations = []
        for i in range(min(options['users'] // 4, len(proposals))):
            conversation = ConversationFactory.create()
            conversation.participants.add(
                proposals[i].requirement.created_by,
                proposals[i].tutor
            )
            conversations.append(conversation)
            
        # Create messages
        self.stdout.write(f'Creating {options["messages"]} messages...')
        for i in range(options['messages']):
            if conversations:
                conversation = conversations[i % len(conversations)]
                participants = list(conversation.participants.all())
                if participants:
                    sender = participants[i % len(participants)]
                    MessageFactory.create(conversation=conversation, sender=sender)
                    
        # Create notifications
        self.stdout.write(f'Creating {options["notifications"]} notifications...')
        users = list(User.objects.all())
        for i in range(options['notifications']):
            if users:
                user = users[i % len(users)]
                NotificationFactory.create(user=user)
                
        self.stdout.write(self.style.SUCCESS('Random test data generated successfully'))