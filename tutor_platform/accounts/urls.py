from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Home URL
    path('', views.home_view, name='home'),
    # Authentication URLs
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password reset URLs
    path('password_reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt'
         ), 
         name='password_reset'),
    path('password_reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # Profile URLs
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('profile/picture/', views.upload_profile_picture_view, name='upload_profile_picture'),
    path('preferences/', views.edit_preferences_view, name='edit_preferences'),
    
    # Dashboard URLs
    path('dashboard/student/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('dashboard/tutor/', views.TutorDashboardView.as_view(), name='tutor_dashboard'),
    path('dashboard/admin/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Subject URLs
    path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
    path('subjects/<slug:slug>/', views.SubjectDetailView.as_view(), name='subject_detail'),
    
    # Tutor URLs
    path('tutors/', views.TutorListView.as_view(), name='tutor_list'),
    path('tutors/<uuid:pk>/', views.TutorDetailView.as_view(), name='tutor_detail'),
    
    # API URLs
    path('api/login/', views.CustomAuthToken.as_view(), name='api_login'),
    path('api/profile/', views.user_profile_api, name='api_profile'),
    path('api/tutors/', views.tutors_api, name='api_tutors'),
]