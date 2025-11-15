from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import TemplateView, ListView, DetailView, UpdateView, CreateView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, Http404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken

from .models import (
    User, StudentProfile, TutorProfile, AdminProfile, 
    Subject, TutorSubject, TutorVerification, UserPreferences
)
from .forms import (
    CustomSignupForm, CustomLoginForm, StudentProfileForm, 
    TutorProfileForm, UserPreferencesForm, UserUpdateForm, ProfilePictureForm
)


# Home View
def home_view(request):
    """Home page view"""
    if request.user.is_authenticated:
        if request.user.is_student():
            return redirect('accounts:student_dashboard')
        elif request.user.is_tutor():
            return redirect('accounts:tutor_dashboard')
        elif request.user.is_admin_user():
            return redirect('accounts:admin_dashboard')
    
    # Show public home page for non-authenticated users
    context = {
        'featured_tutors': TutorProfile.objects.filter(
            user__is_active=True,
            user__is_verified=True,
            is_featured=True
        ).select_related('user')[:6],
        'subjects': Subject.objects.filter(is_active=True, parent=None)[:8],
    }
    return render(request, 'accounts/home.html', context)


# Authentication Views
class SignupView(CreateView):
    """View for user registration"""
    template_name = 'accounts/signup.html'
    form_class = CustomSignupForm
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            'Your account has been created successfully! Please check your email to verify your account.'
        )
        return response


class LoginView(TemplateView):
    """View for user login"""
    template_name = 'accounts/login.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CustomLoginForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = CustomLoginForm(request=request, data=request.POST)
        
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name()}!')
            
            # Redirect based on user type
            if user.is_student():
                return redirect('accounts:student_dashboard')
            elif user.is_tutor():
                return redirect('accounts:tutor_dashboard')
            elif user.is_admin_user():
                return redirect('accounts:admin_dashboard')
            else:
                return redirect('home')
        
        context = self.get_context_data(**kwargs)
        context['form'] = form
        return self.render_to_response(context)


@login_required
def logout_view(request):
    """View for user logout"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('accounts:login')


# Profile Views
@login_required
def profile_view(request):
    """View for user profile"""
    user = request.user
    
    if user.is_student():
        profile = get_object_or_404(StudentProfile, user=user)
        template = 'accounts/student_profile.html'
    elif user.is_tutor():
        profile = get_object_or_404(TutorProfile, user=user)
        template = 'accounts/tutor_profile.html'
    elif user.is_admin_user():
        profile = get_object_or_404(AdminProfile, user=user)
        template = 'accounts/admin_profile.html'
    else:
        raise PermissionDenied("Invalid user type")
    
    context = {
        'user': user,
        'profile': profile,
        'preferences': UserPreferences.objects.get_or_create(user=user)[0]
    }
    
    return render(request, template, context)


@login_required
def edit_profile_view(request):
    """View for editing user profile"""
    user = request.user
    
    if user.is_student():
        profile = get_object_or_404(StudentProfile, user=user)
        profile_form_class = StudentProfileForm
        template = 'accounts/edit_student_profile.html'
    elif user.is_tutor():
        profile = get_object_or_404(TutorProfile, user=user)
        profile_form_class = TutorProfileForm
        template = 'accounts/edit_tutor_profile.html'
    else:
        raise PermissionDenied("Invalid user type")
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = profile_form_class(request.POST, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()
                messages.success(request, 'Your profile has been updated successfully!')
                return redirect('accounts:profile')
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = profile_form_class(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    
    return render(request, template, context)


@login_required
def edit_preferences_view(request):
    """View for editing user preferences"""
    user = request.user
    preferences = UserPreferences.objects.get_or_create(user=user)[0]
    
    if request.method == 'POST':
        form = UserPreferencesForm(request.POST, instance=preferences)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your preferences have been updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserPreferencesForm(instance=preferences)
    
    return render(request, 'accounts/edit_preferences.html', {'form': form})


@login_required
def upload_profile_picture_view(request):
    """View for uploading profile picture"""
    user = request.user
    
    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile picture has been updated!')
            return redirect('accounts:profile')
    else:
        form = ProfilePictureForm(instance=user)
    
    return render(request, 'accounts/upload_profile_picture.html', {'form': form})


# Dashboard Views
class StudentDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view for students"""
    template_name = 'accounts/student_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if not user.is_student():
            raise PermissionDenied("Access denied. This page is for students only.")
        
        try:
            profile = StudentProfile.objects.get(user=user)
            context['profile'] = profile
        except StudentProfile.DoesNotExist:
            profile = StudentProfile.objects.create(user=user)
            context['profile'] = profile
        
        # Add dashboard data here (e.g., upcoming sessions, recent tutors, etc.)
        return context


class TutorDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view for tutors"""
    template_name = 'accounts/tutor_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if not user.is_tutor():
            raise PermissionDenied("Access denied. This page is for tutors only.")
        
        try:
            profile = TutorProfile.objects.get(user=user)
            context['profile'] = profile
            context['average_rating'] = profile.get_average_rating()
            context['completed_sessions'] = profile.get_completed_sessions()
        except TutorProfile.DoesNotExist:
            profile = TutorProfile.objects.create(user=user)
            context['profile'] = profile
        
        # Add dashboard data here (e.g., upcoming sessions, earnings, etc.)
        return context


class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard view for administrators"""
    template_name = 'accounts/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if not user.is_admin_user():
            raise PermissionDenied("Access denied. This page is for administrators only.")
        
        try:
            profile = AdminProfile.objects.get(user=user)
            context['profile'] = profile
        except AdminProfile.DoesNotExist:
            profile = AdminProfile.objects.create(user=user)
            context['profile'] = profile
        
        # Add admin dashboard data here
        context['total_users'] = User.objects.count()
        context['total_students'] = User.objects.filter(user_type=User.UserType.STUDENT).count()
        context['total_tutors'] = User.objects.filter(user_type=User.UserType.TUTOR).count()
        context['pending_verifications'] = TutorVerification.objects.filter(
            status=TutorVerification.VerificationStatus.PENDING
        ).count()
        
        return context


# Subject Views
class SubjectListView(ListView):
    """List all available subjects"""
    model = Subject
    template_name = 'accounts/subject_list.html'
    context_object_name = 'subjects'
    paginate_by = 20
    
    def get_queryset(self):
        return Subject.objects.filter(is_active=True, parent=None).order_by('order', 'name')


class SubjectDetailView(DetailView):
    """Detail view for a subject"""
    model = Subject
    template_name = 'accounts/subject_detail.html'
    context_object_name = 'subject'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = self.get_object()
        
        # Get tutors for this subject
        tutor_subjects = TutorSubject.objects.filter(
            subject=subject,
            tutor__user__is_active=True,
            tutor__user__is_verified=True
        ).select_related('tutor', 'tutor__user')
        
        context['tutor_subjects'] = tutor_subjects
        context['child_subjects'] = subject.get_children()
        
        return context


# Tutor Views
class TutorListView(ListView):
    """List all verified tutors"""
    model = TutorProfile
    template_name = 'accounts/tutor_list.html'
    context_object_name = 'tutors'
    paginate_by = 12
    
    def get_queryset(self):
        from django.db.models import Avg, Count, Q
        
        queryset = TutorProfile.objects.filter(
            user__is_active=True,
            user__is_verified=True
        ).select_related('user').prefetch_related('tutor_subjects__subject', 'ratings')
        
        # Annotate with average rating and completed sessions count
        queryset = queryset.annotate(
            average_rating=Avg('ratings__rating'),
            completed_sessions=Count('ratings')
        )
        
        # Search functionality - integrate with search app
        search = self.request.GET.get('search')
        if search:
            # Use the search app for more advanced search
            try:
                from search.utils import get_search_backend
                
                # Record search query for analytics
                from search.models import SearchQuery
                search_query = SearchQuery.objects.create(
                    user=self.request.user if self.request.user.is_authenticated else None,
                    query=search,
                    search_type='TUTOR',
                    filters=self.request.GET.dict(),
                    ip_address=self.get_client_ip(self.request),
                    user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                )
                
                # Perform search using search backend
                backend = get_search_backend()
                search_results = backend.search(
                    query=search,
                    content_types=['tutor'],
                    filters=self.request.GET.dict(),
                    user=self.request.user if self.request.user.is_authenticated else None
                )
                
                # Extract tutor IDs from search results
                tutor_ids = [result.get('object_id') for result in search_results if result.get('content_type') == 'tutor']
                
                # Filter queryset by searched tutor IDs
                if tutor_ids:
                    queryset = queryset.filter(user__id__in=tutor_ids)
                else:
                    # Fallback to basic search if no results from search app
                    queryset = queryset.filter(
                        Q(user__first_name__icontains=search) |
                        Q(user__last_name__icontains=search) |
                        Q(user__username__icontains=search) |
                        Q(professional_title__icontains=search) |
                        Q(bio__icontains=search)
                    )
            except ImportError:
                # Fallback to basic search if search app is not available
                queryset = queryset.filter(
                    Q(user__first_name__icontains=search) |
                    Q(user__last_name__icontains=search) |
                    Q(user__username__icontains=search) |
                    Q(professional_title__icontains=search) |
                    Q(bio__icontains=search)
                )
        
        # Filter by subject if provided
        subject_id = self.request.GET.get('subject')
        if subject_id:
            queryset = queryset.filter(tutor_subjects__subject_id=subject_id)
        
        # Filter by experience years if provided
        experience = self.request.GET.get('experience')
        if experience:
            queryset = queryset.filter(experience_years__gte=int(experience))
        
        # Filter by education level if provided
        education = self.request.GET.get('education')
        if education:
            queryset = queryset.filter(education=education)
        
        # Filter by price range if provided
        min_rate = self.request.GET.get('min_rate')
        if min_rate:
            queryset = queryset.filter(hourly_rate_min__gte=float(min_rate))
        
        max_rate = self.request.GET.get('max_rate')
        if max_rate:
            queryset = queryset.filter(hourly_rate_max__lte=float(max_rate))
        
        # Filter by availability if provided
        availability = self.request.GET.get('availability')
        if availability and availability != '':
            queryset = queryset.filter(availability_status=availability)
        
        # Filter by teaching style if provided
        style = self.request.GET.get('style')
        if style and style != '':
            queryset = queryset.filter(teaching_style=style)
        
        # Sort by various options
        sort = self.request.GET.get('sort', 'rating')
        if sort == 'rating':
            queryset = queryset.order_by('-average_rating', '-is_featured')
        elif sort == 'experience':
            queryset = queryset.order_by('-experience_years', '-is_featured')
        elif sort == 'rate_low':
            queryset = queryset.order_by('hourly_rate_min', '-is_featured')
        elif sort == 'rate_high':
            queryset = queryset.order_by('-hourly_rate_min', '-is_featured')
        elif sort == 'sessions':
            queryset = queryset.order_by('-completed_sessions', '-is_featured')
        else:
            queryset = queryset.order_by('-is_featured', '-profile_completion_score')
        
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subjects'] = Subject.objects.filter(is_active=True, parent=None)
        return context
    
    def get_client_ip(self, request):
        """Helper method to get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class TutorDetailView(DetailView):
    """Detail view for a tutor"""
    model = TutorProfile
    template_name = 'accounts/tutor_detail.html'
    context_object_name = 'tutor'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tutor = self.get_object()
        
        context['tutor_subjects'] = tutor.tutor_subjects.select_related('subject')
        context['ratings'] = tutor.ratings.filter(is_public=True).order_by('-created_at')[:5]
        context['average_rating'] = tutor.get_average_rating()
        context['verifications'] = tutor.verifications.filter(
            status=TutorVerification.VerificationStatus.APPROVED
        )
        
        return context


# API Views
class CustomAuthToken(ObtainAuthToken):
    """Custom API authentication view"""
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'user_type': user.user_type,
            'first_name': user.first_name,
            'last_name': user.last_name,
        })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_profile_api(request):
    """API endpoint to get user profile"""
    user = request.user
    data = {
        'id': str(user.id),
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'user_type': user.user_type,
        'is_verified': user.is_verified,
        'profile_picture': user.profile_picture.url if user.profile_picture else None,
    }
    
    if user.is_student():
        try:
            profile = user.studentprofile
            data['profile'] = {
                'educational_status': profile.educational_status,
                'institution': profile.institution,
                'grade_level': profile.grade_level,
                'major_field': profile.major_field,
                'bio': profile.bio,
            }
        except StudentProfile.DoesNotExist:
            data['profile'] = None
    elif user.is_tutor():
        try:
            profile = user.tutorprofile
            data['profile'] = {
                'professional_title': profile.professional_title,
                'experience_years': profile.experience_years,
                'education': profile.education,
                'bio': profile.bio,
                'hourly_rate_min': str(profile.hourly_rate_min) if profile.hourly_rate_min else None,
                'hourly_rate_max': str(profile.hourly_rate_max) if profile.hourly_rate_max else None,
                'availability_status': profile.availability_status,
                'languages': profile.languages,
                'profile_completion_score': profile.profile_completion_score,
                'is_featured': profile.is_featured,
                'average_rating': profile.get_average_rating(),
            }
        except TutorProfile.DoesNotExist:
            data['profile'] = None
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def tutors_api(request):
    """API endpoint to get list of tutors"""
    tutors = TutorProfile.objects.filter(
        user__is_active=True,
        user__is_verified=True
    ).select_related('user')
    
    # Apply filters
    subject_id = request.GET.get('subject')
    if subject_id:
        tutors = tutors.filter(tutor_subjects__subject_id=subject_id).distinct()
    
    availability = request.GET.get('availability')
    if availability == 'available':
        tutors = tutors.filter(availability_status=TutorProfile.AvailabilityStatus.AVAILABLE)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(tutors, 12)
    tutors_page = paginator.get_page(page)
    
    data = []
    for tutor in tutors_page:
        data.append({
            'id': str(tutor.user.id),
            'username': tutor.user.username,
            'first_name': tutor.user.first_name,
            'last_name': tutor.user.last_name,
            'profile_picture': tutor.user.profile_picture.url if tutor.user.profile_picture else None,
            'professional_title': tutor.professional_title,
            'experience_years': tutor.experience_years,
            'bio': tutor.bio,
            'hourly_rate_min': str(tutor.hourly_rate_min) if tutor.hourly_rate_min else None,
            'hourly_rate_max': str(tutor.hourly_rate_max) if tutor.hourly_rate_max else None,
            'availability_status': tutor.availability_status,
            'average_rating': tutor.get_average_rating(),
            'profile_completion_score': tutor.profile_completion_score,
            'is_featured': tutor.is_featured,
        })
    
    return Response({
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': tutors_page.number,
        'results': data,
    })
