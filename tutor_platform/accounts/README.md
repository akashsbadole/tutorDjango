# Django Tutor Platform - Accounts App

This app handles user authentication, authorization, and profile management for the Django Tutoring Platform.

## Features

### Authentication & Authorization
- Custom User model with role-based access (Student, Tutor, Admin)
- Email-based authentication with password validation
- Account verification via email
- Session management with remember me functionality
- Password reset functionality

### User Profiles
- **StudentProfile**: Educational information, learning goals, and preferences
- **TutorProfile**: Professional information, experience, rates, and availability
- **AdminProfile**: Department and permissions for platform administrators
- **UserPreferences**: Notification settings and localization preferences

### Subject Management
- Hierarchical subject structure (e.g., Math > Calculus > Integrals)
- Tutor-subject relationships with proficiency levels
- Subject-specific hourly rates

### Verification System
- Tutor credential verification (Identity, Education, Professional, Background Check)
- Document upload and review workflow
- Expiration tracking for verifications

### Rating System
- 5-star rating system for tutors
- Public/private review options
- Average rating calculations

## Models

### User (Custom AbstractUser)
- Extends Django's built-in User model
- Adds role-based access control
- Includes profile picture, phone number, timezone fields
- Helper methods for role checking (is_student(), is_tutor(), is_admin_user())

### Profile Models
- **StudentProfile**: Educational status, institution, learning style
- **TutorProfile**: Professional title, experience, rates, availability
- **AdminProfile**: Department, permissions (JSON field)

### Supporting Models
- **Subject**: Hierarchical subject organization
- **TutorSubject**: Many-to-many relationship with additional fields
- **TutorVerification**: Document verification workflow
- **TutorRating**: Review and rating system
- **UserPreferences**: User-specific settings

## Views

### Authentication Views
- `SignupView`: User registration with role selection
- `LoginView`: Email-based login with remember me
- `logout_view`: User logout functionality

### Profile Views
- `profile_view`: Display user profile based on role
- `edit_profile_view`: Update user and profile information
- `edit_preferences_view`: Update user preferences
- `upload_profile_picture_view`: Profile picture upload

### Dashboard Views
- `StudentDashboardView`: Student-specific dashboard
- `TutorDashboardView`: Tutor-specific dashboard
- `AdminDashboardView`: Admin-specific dashboard

### Subject & Tutor Views
- `SubjectListView`: List all available subjects
- `SubjectDetailView`: Subject details with associated tutors
- `TutorListView`: List all verified tutors with filtering
- `TutorDetailView`: Detailed tutor profile with ratings

## API Endpoints

### Authentication
- `api/login`: JWT token-based authentication
- `api/profile`: Get user profile information
- `api/tutors`: Get list of tutors with filtering

## Forms

### Authentication Forms
- `CustomSignupForm`: Registration with role selection
- `CustomLoginForm`: Email-based login with remember me

### Profile Forms
- `StudentProfileForm`: Student profile information
- `TutorProfileForm`: Tutor profile information
- `UserPreferencesForm`: User preference settings
- `UserUpdateForm`: Basic user information
- `ProfilePictureForm`: Profile picture upload

## Admin Configuration

### Custom Admin Classes
- Enhanced User admin with profile links
- Profile admins with role-specific fields
- Subject admin with hierarchy support
- Tutor verification admin with approval workflow
- Rating admin with filtering options

## URL Configuration

### Authentication URLs
- `/signup/`: User registration
- `/login/`: User login
- `/logout/`: User logout
- `/password_reset/`: Password reset

### Profile URLs
- `/accounts/profile/`: View profile
- `/accounts/profile/edit/`: Edit profile
- `/accounts/preferences/`: Edit preferences

### Dashboard URLs
- `/accounts/dashboard/student/`: Student dashboard
- `/accounts/dashboard/tutor/`: Tutor dashboard
- `/accounts/dashboard/admin/`: Admin dashboard

### Subject & Tutor URLs
- `/accounts/subjects/`: Subject list
- `/accounts/subjects/<slug>/`: Subject detail
- `/accounts/tutors/`: Tutor list
- `/accounts/tutors/<uuid>/`: Tutor detail

## Security Features

- Password validation with minimum length requirements
- Email verification for new accounts
- Rate limiting for login attempts
- CSRF protection on all forms
- Secure password hashing
- Session security settings

## Performance Optimizations

- Database indexes on frequently queried fields
- Select-related optimizations in views
- Pagination for list views
- Optimized queries for tutor listings
- Efficient profile completion calculations

## Installation & Setup

1. Add `accounts` to `INSTALLED_APPS` in settings.py
2. Configure `AUTH_USER_MODEL = 'accounts.User'`
3. Include accounts URLs in project urls.py
4. Run migrations: `python manage.py migrate`
5. Create superuser: `python manage.py createsuperuser`

## Dependencies

- Django 5.0+
- django-allauth for social authentication
- django-phonenumber-field for phone validation
- Pillow for image handling
- django-rest-framework for API endpoints
- django-simplejwt for token authentication