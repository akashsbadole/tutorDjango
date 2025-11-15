"""
Unit tests for admin_portal app models.
"""
import pytest
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from tests.factories import (
    UserFactory, AdminUserFactory, AdminRoleFactory, AdminPermissionFactory,
    AdminLogFactory, AdminReportFactory, AdminSettingFactory
)
from tests.utils.helpers import TestMixin, DateTimeTestMixin


class AdminUserModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for AdminUser model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        
    def test_admin_user_creation(self):
        """Test AdminUser model creation."""
        admin_user = AdminUserFactory.create(user=self.user)
        self.assertTrue(isinstance(admin_user, AdminUserFactory._meta.model))
        self.assertEqual(admin_user.user, self.user)
        self.assertTrue(admin_user.is_active)
        
    def test_admin_user_string_representation(self):
        """Test AdminUser string representation."""
        admin_user = AdminUserFactory.create(user=self.user)
        expected = f"Admin: {self.user.get_full_name() or self.user.username}"
        self.assertEqual(str(admin_user), expected)
        
    def test_admin_user_role_relationship(self):
        """Test AdminUser-AdminRole relationship."""
        role = AdminRoleFactory.create()
        admin_user = AdminUserFactory.create(user=self.user, role=role)
        
        self.assertEqual(admin_user.role, role)
        
        # Test reverse relationship
        self.assertIn(admin_user, role.admin_users.all())
        
    def test_admin_user_permissions_relationship(self):
        """Test AdminUser-AdminPermission relationship."""
        permission = AdminPermissionFactory.create()
        admin_user = AdminUserFactory.create(user=self.user)
        admin_user.permissions.add(permission)
        
        self.assertIn(permission, admin_user.permissions.all())
        
        # Test reverse relationship
        self.assertIn(admin_user, permission.admin_users.all())
        
    def test_admin_user_is_active_default(self):
        """Test is_active defaults to True."""
        admin_user = AdminUserFactory.build(user=self.user)
        self.assertTrue(admin_user.is_active)
        
    def test_admin_user_last_login_validation(self):
        """Test last_login field validation."""
        admin_user = AdminUserFactory.build(user=self.user)
        
        # Test with future date
        admin_user.last_login = self.create_future_date(hours=1)
        with self.assertRaises(ValidationError):
            admin_user.full_clean()
            
    def test_admin_user_user_relationship(self):
        """Test AdminUser-User relationship."""
        admin_user = AdminUserFactory.create(user=self.user)
        
        # Test reverse relationship
        self.assertEqual(admin_user, self.user.admin_user)


class AdminRoleModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for AdminRole model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_admin_role_creation(self):
        """Test AdminRole model creation."""
        role = AdminRoleFactory.create()
        self.assertTrue(isinstance(role, AdminRoleFactory._meta.model))
        self.assertTrue(role.is_active)
        
    def test_admin_role_string_representation(self):
        """Test AdminRole string representation."""
        role = AdminRoleFactory.create(name="Super Admin")
        self.assertEqual(str(role), "Super Admin")
        
    def test_admin_role_name_validation(self):
        """Test name field validation."""
        role = AdminRoleFactory.build()
        
        # Test empty name
        role.name = ""
        with self.assertRaises(ValidationError):
            role.full_clean()
            
    def test_admin_role_slug_validation(self):
        """Test slug field validation."""
        role = AdminRoleFactory.build()
        
        # Test empty slug
        role.slug = ""
        with self.assertRaises(ValidationError):
            role.full_clean()
            
    def test_admin_role_is_active_default(self):
        """Test is_active defaults to True."""
        role = AdminRoleFactory.build()
        self.assertTrue(role.is_active)
        
    def test_admin_role_permissions_relationship(self):
        """Test AdminRole-AdminPermission relationship."""
        permission = AdminPermissionFactory.create()
        role = AdminRoleFactory.create()
        role.permissions.add(permission)
        
        self.assertIn(permission, role.permissions.all())
        
        # Test reverse relationship
        self.assertIn(role, permission.roles.all())
        
    def test_admin_role_description_validation(self):
        """Test description field validation."""
        role = AdminRoleFactory.build()
        
        # Test too long description
        role.description = "x" * 1001  # Assuming max_length is 1000
        with self.assertRaises(ValidationError):
            role.full_clean()


class AdminPermissionModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for AdminPermission model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_admin_permission_creation(self):
        """Test AdminPermission model creation."""
        permission = AdminPermissionFactory.create()
        self.assertTrue(isinstance(permission, AdminPermissionFactory._meta.model))
        self.assertTrue(permission.is_active)
        
    def test_admin_permission_string_representation(self):
        """Test AdminPermission string representation."""
        permission = AdminPermissionFactory.create(
            name="User Management",
            code="user_management"
        )
        self.assertEqual(str(permission), "User Management")
        
    def test_admin_permission_name_validation(self):
        """Test name field validation."""
        permission = AdminPermissionFactory.build()
        
        # Test empty name
        permission.name = ""
        with self.assertRaises(ValidationError):
            permission.full_clean()
            
    def test_admin_permission_code_validation(self):
        """Test code field validation."""
        permission = AdminPermissionFactory.build()
        
        # Test empty code
        permission.code = ""
        with self.assertRaises(ValidationError):
            permission.full_clean()
            
        # Test invalid code format (spaces)
        permission.code = "invalid code"
        with self.assertRaises(ValidationError):
            permission.full_clean()
            
    def test_admin_permission_is_active_default(self):
        """Test is_active defaults to True."""
        permission = AdminPermissionFactory.build()
        self.assertTrue(permission.is_active)
        
    def test_admin_permission_description_validation(self):
        """Test description field validation."""
        permission = AdminPermissionFactory.build()
        
        # Test too long description
        permission.description = "x" * 1001  # Assuming max_length is 1000
        with self.assertRaises(ValidationError):
            permission.full_clean()


class AdminLogModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for AdminLog model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        self.admin_user = AdminUserFactory.create(user=self.user)
        
    def test_admin_log_creation(self):
        """Test AdminLog model creation."""
        log = AdminLogFactory.create(admin_user=self.admin_user)
        self.assertTrue(isinstance(log, AdminLogFactory._meta.model))
        self.assertEqual(log.admin_user, self.admin_user)
        
    def test_admin_log_string_representation(self):
        """Test AdminLog string representation."""
        log = AdminLogFactory.create(
            admin_user=self.admin_user,
            action="User Created"
        )
        expected = f"{self.admin_user} - User Created"
        self.assertEqual(str(log), expected)
        
    def test_admin_log_action_validation(self):
        """Test action field validation."""
        log = AdminLogFactory.build(admin_user=self.admin_user)
        
        # Test empty action
        log.action = ""
        with self.assertRaises(ValidationError):
            log.full_clean()
            
    def test_admin_log_ip_address_validation(self):
        """Test ip_address field validation."""
        log = AdminLogFactory.build(admin_user=self.admin_user)
        
        # Test invalid IP address
        log.ip_address = "invalid-ip"
        with self.assertRaises(ValidationError):
            log.full_clean()
            
    def test_admin_log_user_agent_validation(self):
        """Test user_agent field validation."""
        log = AdminLogFactory.build(admin_user=self.admin_user)
        
        # Test too long user agent
        log.user_agent = "x" * 501  # Assuming max_length is 500
        with self.assertRaises(ValidationError):
            log.full_clean()
            
    def test_admin_log_admin_user_relationship(self):
        """Test AdminLog-AdminUser relationship."""
        log = AdminLogFactory.create(admin_user=self.admin_user)
        
        # Test reverse relationship
        self.assertIn(log, self.admin_user.logs.all())


class AdminReportModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for AdminReport model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        self.admin_user = AdminUserFactory.create(user=self.user)
        
    def test_admin_report_creation(self):
        """Test AdminReport model creation."""
        report = AdminReportFactory.create(admin_user=self.admin_user)
        self.assertTrue(isinstance(report, AdminReportFactory._meta.model))
        self.assertEqual(report.admin_user, self.admin_user)
        
    def test_admin_report_string_representation(self):
        """Test AdminReport string representation."""
        report = AdminReportFactory.create(
            admin_user=self.admin_user,
            name="Monthly User Report"
        )
        expected = f"Monthly User Report"
        self.assertEqual(str(report), expected)
        
    def test_admin_report_name_validation(self):
        """Test name field validation."""
        report = AdminReportFactory.build(admin_user=self.admin_user)
        
        # Test empty name
        report.name = ""
        with self.assertRaises(ValidationError):
            report.full_clean()
            
    def test_admin_report_type_choices(self):
        """Test report_type field choices."""
        report = AdminReportFactory.build(admin_user=self.admin_user)
        
        valid_types = ['USER', 'TRANSACTION', 'SYSTEM', 'SECURITY']
        for report_type in valid_types:
            report.report_type = report_type
            report.full_clean()  # Should not raise
            
        # Test invalid type
        report.report_type = 'INVALID'
        with self.assertRaises(ValidationError):
            report.full_clean()
            
    def test_admin_report_status_choices(self):
        """Test status field choices."""
        report = AdminReportFactory.build(admin_user=self.admin_user)
        
        valid_statuses = ['PENDING', 'GENERATING', 'COMPLETED', 'FAILED']
        for status in valid_statuses:
            report.status = status
            report.full_clean()  # Should not raise
            
        # Test invalid status
        report.status = 'INVALID'
        with self.assertRaises(ValidationError):
            report.full_clean()
            
    def test_admin_report_format_choices(self):
        """Test format field choices."""
        report = AdminReportFactory.build(admin_user=self.admin_user)
        
        valid_formats = ['PDF', 'CSV', 'EXCEL', 'JSON']
        for format_type in valid_formats:
            report.format = format_type
            report.full_clean()  # Should not raise
            
        # Test invalid format
        report.format = 'INVALID'
        with self.assertRaises(ValidationError):
            report.full_clean()
            
    def test_admin_report_admin_user_relationship(self):
        """Test AdminReport-AdminUser relationship."""
        report = AdminReportFactory.create(admin_user=self.admin_user)
        
        # Test reverse relationship
        self.assertIn(report, self.admin_user.reports.all())


class AdminSettingModelTest(TestCase, TestMixin, DateTimeTestMixin):
    """Test cases for AdminSetting model."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        self.admin_user = AdminUserFactory.create(user=self.user)
        
    def test_admin_setting_creation(self):
        """Test AdminSetting model creation."""
        setting = AdminSettingFactory.create(admin_user=self.admin_user)
        self.assertTrue(isinstance(setting, AdminSettingFactory._meta.model))
        self.assertEqual(setting.admin_user, self.admin_user)
        
    def test_admin_setting_string_representation(self):
        """Test AdminSetting string representation."""
        setting = AdminSettingFactory.create(
            admin_user=self.admin_user,
            key="notification_email"
        )
        expected = f"notification_email"
        self.assertEqual(str(setting), expected)
        
    def test_admin_setting_key_validation(self):
        """Test key field validation."""
        setting = AdminSettingFactory.build(admin_user=self.admin_user)
        
        # Test empty key
        setting.key = ""
        with self.assertRaises(ValidationError):
            setting.full_clean()
            
    def test_admin_setting_value_validation(self):
        """Test value field validation."""
        setting = AdminSettingFactory.build(admin_user=self.admin_user)
        
        # Test too long value
        setting.value = "x" * 1001  # Assuming max_length is 1000
        with self.assertRaises(ValidationError):
            setting.full_clean()
            
    def test_admin_setting_admin_user_relationship(self):
        """Test AdminSetting-AdminUser relationship."""
        setting = AdminSettingFactory.create(admin_user=self.admin_user)
        
        # Test reverse relationship
        self.assertIn(setting, self.admin_user.settings.all())


class AdminUserQuerySetTest(TestCase, TestMixin):
    """Test cases for AdminUser model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_active_queryset(self):
        """Test active queryset method."""
        # Create admin users with different active status
        active = AdminUserFactory.create(is_active=True)
        inactive = AdminUserFactory.create(is_active=False)
        
        active_admins = AdminUser.objects.active()
        self.assertEqual(active_admins.count(), 1)
        self.assertIn(active, active_admins)
        self.assertNotIn(inactive, active_admins)
        
    def test_by_role_queryset(self):
        """Test by_role queryset method."""
        # Create admin users with different roles
        role1 = AdminRoleFactory.create(name="Role 1")
        role2 = AdminRoleFactory.create(name="Role 2")
        
        admin1 = AdminUserFactory.create(role=role1)
        admin2 = AdminUserFactory.create(role=role2)
        
        # Test filtering by role1
        role1_admins = AdminUser.objects.by_role(role1.id)
        self.assertEqual(role1_admins.count(), 1)
        self.assertIn(admin1, role1_admins)
        self.assertNotIn(admin2, role1_admins)
        
    def test_with_permission_queryset(self):
        """Test with_permission queryset method."""
        # Create admin users with different permissions
        permission = AdminPermissionFactory.create(code="test_permission")
        
        admin_with_permission = AdminUserFactory.create()
        admin_with_permission.permissions.add(permission)
        
        admin_without_permission = AdminUserFactory.create()
        
        # Test filtering by permission
        admins_with_permission = AdminUser.objects.with_permission("test_permission")
        self.assertEqual(admins_with_permission.count(), 1)
        self.assertIn(admin_with_permission, admins_with_permission)
        self.assertNotIn(admin_without_permission, admins_with_permission)


class AdminRoleQuerySetTest(TestCase, TestMixin):
    """Test cases for AdminRole model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_active_queryset(self):
        """Test active queryset method."""
        # Create roles with different active status
        active = AdminRoleFactory.create(is_active=True)
        inactive = AdminRoleFactory.create(is_active=False)
        
        active_roles = AdminRole.objects.active()
        self.assertEqual(active_roles.count(), 1)
        self.assertIn(active, active_roles)
        self.assertNotIn(inactive, active_roles)


class AdminPermissionQuerySetTest(TestCase, TestMixin):
    """Test cases for AdminPermission model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        
    def test_active_queryset(self):
        """Test active queryset method."""
        # Create permissions with different active status
        active = AdminPermissionFactory.create(is_active=True)
        inactive = AdminPermissionFactory.create(is_active=False)
        
        active_permissions = AdminPermission.objects.active()
        self.assertEqual(active_permissions.count(), 1)
        self.assertIn(active, active_permissions)
        self.assertNotIn(inactive, active_permissions)
        
    def test_by_code_queryset(self):
        """Test by_code queryset method."""
        # Create permissions with different codes
        permission1 = AdminPermissionFactory.create(code="user_management")
        permission2 = AdminPermissionFactory.create(code="payment_management")
        
        # Test filtering by code
        filtered_permissions = AdminPermission.objects.by_code("user_management")
        self.assertEqual(filtered_permissions.count(), 1)
        self.assertIn(permission1, filtered_permissions)
        self.assertNotIn(permission2, filtered_permissions)


class AdminLogQuerySetTest(TestCase, TestMixin):
    """Test cases for AdminLog model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        self.admin_user = AdminUserFactory.create(user=self.user)
        
    def test_by_admin_queryset(self):
        """Test by_admin queryset method."""
        # Create logs for different admin users
        user2 = UserFactory.create()
        admin_user2 = AdminUserFactory.create(user=user2)
        
        log1 = AdminLogFactory.create(admin_user=self.admin_user)
        log2 = AdminLogFactory.create(admin_user=admin_user2)
        
        # Test filtering by admin user
        admin_logs = AdminLog.objects.by_admin(self.admin_user.id)
        self.assertEqual(admin_logs.count(), 1)
        self.assertIn(log1, admin_logs)
        self.assertNotIn(log2, admin_logs)
        
    def test_by_action_queryset(self):
        """Test by_action queryset method."""
        # Create logs with different actions
        log1 = AdminLogFactory.create(
            admin_user=self.admin_user,
            action="User Created"
        )
        log2 = AdminLogFactory.create(
            admin_user=self.admin_user,
            action="User Updated"
        )
        
        # Test filtering by action
        action_logs = AdminLog.objects.by_action("User Created")
        self.assertEqual(action_logs.count(), 1)
        self.assertIn(log1, action_logs)
        self.assertNotIn(log2, action_logs)
        
    def test_by_date_range_queryset(self):
        """Test by_date_range queryset method."""
        # Create logs with different dates
        old_log = AdminLogFactory.create(
            admin_user=self.admin_user,
            created_at=self.create_past_date(days=10)
        )
        recent_log = AdminLogFactory.create(
            admin_user=self.admin_user,
            created_at=self.create_past_date(days=2)
        )
        future_log = AdminLogFactory.create(
            admin_user=self.admin_user,
            created_at=self.create_future_date(days=5)
        )
        
        # Test date range (last 7 days)
        start_date = self.create_past_date(days=7)
        end_date = timezone.now()
        range_logs = AdminLog.objects.by_date_range(start_date, end_date)
        self.assertEqual(range_logs.count(), 2)
        self.assertIn(recent_log, range_logs)
        self.assertNotIn(old_log, range_logs)
        self.assertNotIn(future_log, range_logs)


class AdminReportQuerySetTest(TestCase, TestMixin):
    """Test cases for AdminReport model custom querysets."""
    
    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.user = UserFactory.create()
        self.admin_user = AdminUserFactory.create(user=self.user)
        
    def test_by_admin_queryset(self):
        """Test by_admin queryset method."""
        # Create reports for different admin users
        user2 = UserFactory.create()
        admin_user2 = AdminUserFactory.create(user=user2)
        
        report1 = AdminReportFactory.create(admin_user=self.admin_user)
        report2 = AdminReportFactory.create(admin_user=admin_user2)
        
        # Test filtering by admin user
        admin_reports = AdminReport.objects.by_admin(self.admin_user.id)
        self.assertEqual(admin_reports.count(), 1)
        self.assertIn(report1, admin_reports)
        self.assertNotIn(report2, admin_reports)
        
    def test_by_type_queryset(self):
        """Test by_type queryset method."""
        # Create reports with different types
        user_report = AdminReportFactory.create(
            admin_user=self.admin_user,
            report_type='USER'
        )
        transaction_report = AdminReportFactory.create(
            admin_user=self.admin_user,
            report_type='TRANSACTION'
        )
        
        # Test filtering by type
        user_reports = AdminReport.objects.by_type('USER')
        self.assertEqual(user_reports.count(), 1)
        self.assertIn(user_report, user_reports)
        self.assertNotIn(transaction_report, user_reports)
        
    def test_by_status_queryset(self):
        """Test by_status queryset method."""
        # Create reports with different statuses
        pending_report = AdminReportFactory.create(
            admin_user=self.admin_user,
            status='PENDING'
        )
        completed_report = AdminReportFactory.create(
            admin_user=self.admin_user,
            status='COMPLETED'
        )
        
        # Test filtering by status
        pending_reports = AdminReport.objects.by_status('PENDING')
        self.assertEqual(pending_reports.count(), 1)
        self.assertIn(pending_report, pending_reports)
        self.assertNotIn(completed_report, pending_reports)


class AdminPortalSignalTest(TestCase, TestMixin):
    """Test cases for admin portal signals."""
    
    def test_admin_user_created_signal(self):
        """Test AdminUser creation signal."""
        # This would test that AdminUser creation triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_admin_log_created_signal(self):
        """Test AdminLog creation signal."""
        # This would test that AdminLog creation triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic
        
    def test_admin_report_generated_signal(self):
        """Test AdminReport generation signal."""
        # This would test that AdminReport generation triggers
        # appropriate signals and side effects
        pass  # Implementation depends on actual signal logic