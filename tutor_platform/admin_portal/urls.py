"""
Django Tutor Platform Admin Portal URL Configuration

This module contains URL patterns for the admin portal.
"""

from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'admin_portal'

urlpatterns = [
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(
        template_name='admin_portal/auth/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        next_page='admin_portal:login'
    ), name='logout'),
    
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='admin_portal/auth/password_change.html',
        success_url='/admin-panel/password-change-done/'
    ), name='password_change'),
    
    path('password-change-done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='admin_portal/auth/password_change_done.html'
    ), name='password_change_done'),
    
    # Dashboard URLs
    path('', views.AdminDashboardView.as_view(), name='dashboard'),
    
    # User Management URLs
    path('users/', views.UserManagementView.as_view(), name='user_management'),
    path('users/bulk-action/', views.bulk_user_action, name='bulk_user_action'),
    
    # Requirement Management URLs
    path('requirements/', views.RequirementManagementView.as_view(), name='requirement_management'),
    
    # Payment and Escrow URLs
    path('payments/', views.PaymentEscrowView.as_view(), name='payment_management'),
    path('escrow/', views.PaymentEscrowView.as_view(), name='escrow_management'),
    
    # Communication Monitoring URLs
    path('communications/', views.CommunicationMonitoringView.as_view(), name='communication_monitoring'),
    path('messages/', views.CommunicationMonitoringView.as_view(), name='message_monitoring'),
    
    # System Analytics URLs
    path('analytics/', views.SystemAnalyticsView.as_view(), name='system_analytics'),
    path('health/', views.SystemAnalyticsView.as_view(), name='system_health'),
    
    # Data Export URLs
    path('export/', views.DataExportView.as_view(), name='data_export'),
    
    # Chart Data URLs (AJAX endpoints)
    path('api/chart-data/', views.get_chart_data, name='chart_data'),
    
    # Settings URLs
    # path('settings/', views.SystemSettingsView.as_view(), name='system_settings'),
    
    # Access Denied URL
    path('access-denied/', views.AccessDeniedView.as_view(), name='access_denied'),
    
    # Profile Management URLs
    # path('profile/', views.AdminProfileView.as_view(), name='profile'),
    # path('profile/edit/', views.AdminProfileEditView.as_view(), name='profile_edit'),
    
    # Activity Log URLs
    # path('activity/', views.AdminActivityLogView.as_view(), name='activity_log'),
    # path('activity/<int:pk>/', views.AdminActivityDetailView.as_view(), name='activity_detail'),
    
    # Session Management URLs
    # path('sessions/', views.AdminSessionListView.as_view(), name='session_list'),
    # path('sessions/<int:pk>/terminate/', views.TerminateSessionView.as_view(), name='terminate_session'),
    
    # System Settings URLs
    # path('system-settings/', views.SystemSettingListView.as_view(), name='system_setting_list'),
    # path('system-settings/create/', views.SystemSettingCreateView.as_view(), name='system_setting_create'),
    # path('system-settings/<int:pk>/edit/', views.SystemSettingUpdateView.as_view(), name='system_setting_edit'),
    # path('system-settings/<int:pk>/delete/', views.SystemSettingDeleteView.as_view(), name='system_setting_delete'),
    
    # Role Management URLs
    # path('roles/', views.AdminRoleListView.as_view(), name='role_list'),
    # path('roles/create/', views.AdminRoleCreateView.as_view(), name='role_create'),
    # path('roles/<int:pk>/edit/', views.AdminRoleUpdateView.as_view(), name='role_edit'),
    # path('roles/<int:pk>/delete/', views.AdminRoleDeleteView.as_view(), name='role_delete'),
    
    # Report URLs
    # path('reports/', views.ReportListView.as_view(), name='report_list'),
    # path('reports/generate/', views.ReportGenerateView.as_view(), name='report_generate'),
    # path('reports/<int:pk>/', views.ReportDetailView.as_view(), name='report_detail'),
    # path('reports/<int:pk>/download/', views.ReportDownloadView.as_view(), name='report_download'),
]