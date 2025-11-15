#!/usr/bin/env python
"""
Final test script to verify all admin interfaces are working correctly.
"""
import os
import sys
import django

# Add the tutor_platform directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tutor_platform'))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tutor_platform.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()

def test_admin_interfaces():
    """Test all admin interfaces"""
    print("=" * 60)
    print("Testing Django Tutor Platform Admin Interfaces")
    print("=" * 60)
    
    # Create test admin user if it doesn't exist
    try:
        admin_user = User.objects.get(username='admin')
        print(f"[OK] Admin user exists: {admin_user.username}")
    except User.DoesNotExist:
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123',
            first_name='Admin',
            last_name='User'
        )
        print(f"[OK] Created admin user: {admin_user.username}")
    
    # Create test client and login
    client = Client()
    client.login(username='admin', password='admin123')
    print("[OK] Logged in as admin user")
    
    # Test default admin site
    print("\n" + "-" * 40)
    print("Testing Default Admin Site")
    print("-" * 40)
    
    try:
        response = client.get('/admin/')
        if response.status_code == 200:
            print("[OK] Default admin site accessible at /admin/")
        else:
            print(f"[ERROR] Default admin site error: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Default admin site error: {str(e)}")
    
    # Test custom admin site
    print("\n" + "-" * 40)
    print("Testing Custom Admin Site")
    print("-" * 40)
    
    try:
        response = client.get('/admin-panel/')
        if response.status_code == 200:
            print("[OK] Custom admin site accessible at /admin-panel/")
        else:
            print(f"[ERROR] Custom admin site error: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Custom admin site error: {str(e)}")
    
    # Test individual admin model pages
    print("\n" + "-" * 40)
    print("Testing Individual Admin Model Pages")
    print("-" * 40)
    
    admin_models = [
        # Accounts app
        ('/admin/accounts/user/', 'User'),
        ('/admin/accounts/studentprofile/', 'StudentProfile'),
        ('/admin/accounts/tutorprofile/', 'TutorProfile'),
        ('/admin/accounts/adminprofile/', 'AdminProfile'),
        ('/admin/accounts/subject/', 'Subject'),
        ('/admin/accounts/tutorsubject/', 'TutorSubject'),
        ('/admin/accounts/tutorverification/', 'TutorVerification'),
        ('/admin/accounts/tutorrating/', 'TutorRating'),
        
        # Requirements app
        ('/admin/requirements/requirement/', 'Requirement'),
        ('/admin/requirements/proposal/', 'Proposal'),
        ('/admin/requirements/award/', 'Award'),
        ('/admin/requirements/session/', 'Session'),
        ('/admin/requirements/review/', 'Review'),
        ('/admin/requirements/milestone/', 'Milestone'),
        ('/admin/requirements/savedrequirement/', 'SavedRequirement'),
        ('/admin/requirements/favoritetutor/', 'FavoriteTutor'),
        
        # Messaging app
        ('/admin/messaging/conversation/', 'Conversation'),
        ('/admin/messaging/message/', 'Message'),
        ('/admin/messaging/maskedemail/', 'MaskedEmail'),
        ('/admin/messaging/onlineclass/', 'OnlineClass'),
        ('/admin/messaging/communicationpreference/', 'CommunicationPreference'),
        ('/admin/messaging/blockeduser/', 'BlockedUser'),
        
        # Notifications app
        ('/admin/notifications/notification/', 'Notification'),
        ('/admin/notifications/notificationtemplate/', 'NotificationTemplate'),
        ('/admin/notifications/emailqueue/', 'EmailQueue'),
        ('/admin/notifications/notificationpreference/', 'NotificationPreference'),
        
        # Payments app
        ('/admin/paymentsdetails/payment/', 'Payment'),
        ('/admin/paymentsdetails/escrowaccount/', 'EscrowAccount'),
        ('/admin/paymentsdetails/transaction/', 'Transaction'),
        ('/admin/paymentsdetails/paymentmethod/', 'PaymentMethod'),
        ('/admin/paymentsdetails/commission/', 'Commission'),
        ('/admin/paymentsdetails/refund/', 'Refund'),
        ('/admin/paymentsdetails/payout/', 'Payout'),
    ]
    
    success_count = 0
    total_count = len(admin_models)
    
    for url, model_name in admin_models:
        try:
            response = client.get(url)
            if response.status_code == 200:
                print(f"[OK] {model_name} admin page accessible")
                success_count += 1
            else:
                print(f"[ERROR] {model_name} admin page error: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] {model_name} admin page error: {str(e)}")
    
    # Test home page
    print("\n" + "-" * 40)
    print("Testing Home Page")
    print("-" * 40)
    
    try:
        response = client.get('/')
        if response.status_code == 200:
            print("[OK] Home page accessible at /")
        else:
            print(f"[ERROR] Home page error: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Home page error: {str(e)}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Admin models tested: {total_count}")
    print(f"Successfully accessible: {success_count}")
    print(f"Failed: {total_count - success_count}")
    print(f"Success rate: {success_count/total_count*100:.1f}%")
    
    if success_count == total_count:
        print("\n[SUCCESS] All admin interfaces are working correctly!")
    else:
        print(f"\n[WARNING] {total_count - success_count} admin interfaces have issues.")
    
    return success_count == total_count

if __name__ == '__main__':
    success = test_admin_interfaces()
    sys.exit(0 if success else 1)