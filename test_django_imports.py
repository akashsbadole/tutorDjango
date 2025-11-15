#!/usr/bin/env python
"""
Simple test script to verify Django imports work
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tutor_platform.settings')
sys.path.append(os.path.join(os.path.dirname(__file__), 'tutor_platform'))

try:
    django.setup()
    print("✓ Django setup successful")
    
    # Test basic Django imports
    from django.contrib import admin
    print("✓ django.contrib.admin imported successfully")
    
    from django.contrib.auth import get_user_model
    print("✓ django.contrib.auth imported successfully")
    
    from django import forms
    print("✓ django.forms imported successfully")
    
    # Test app imports
    from messaging.models import Message, Conversation
    print("✓ messaging.models imported successfully")
    
    from messaging.forms import MessageForm
    print("✓ messaging.forms imported successfully")
    
    from accounts.models import User
    print("✓ accounts.models imported successfully")
    
    print("\nAll core imports successful! ✓")
    
except Exception as e:
    print(f"\nError during import test: {e}")
    import traceback
    traceback.print_exc()