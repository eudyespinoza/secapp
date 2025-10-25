# ==================================================
# SecureApprove Django - Test Models
# ==================================================

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal

from apps.authentication.models import User, Tenant
from apps.requests.models import ApprovalRequest
from apps.billing.models import Plan, Subscription, Invoice

User = get_user_model()


class TenantModelTest(TestCase):
    """Test Tenant model functionality"""
    
    def test_create_tenant(self):
        """Test basic tenant creation"""
        tenant = Tenant.objects.create(
            name="Test Company",
            domain="testcompany.com"
        )
        self.assertEqual(tenant.name, "Test Company")
        self.assertEqual(tenant.domain, "testcompany.com")
        self.assertTrue(tenant.is_active)
    
    def test_tenant_str_representation(self):
        """Test tenant string representation"""
        tenant = Tenant.objects.create(name="Test Company")
        self.assertEqual(str(tenant), "Test Company")


class UserModelTest(TestCase):
    """Test User model functionality"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Company",
            domain="testcompany.com"
        )
    
    def test_create_user(self):
        """Test basic user creation"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
            tenant=self.tenant
        )
        
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertEqual(user.tenant, self.tenant)
        self.assertTrue(user.check_password("testpass123"))
    
    def test_create_superuser(self):
        """Test superuser creation"""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123"
        )
        
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
    
    def test_user_full_name(self):
        """Test user full name method"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe"
        )
        
        self.assertEqual(user.get_full_name(), "John Doe")
    
    def test_user_short_name(self):
        """Test user short name method"""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe"
        )
        
        self.assertEqual(user.get_short_name(), "John")
    
    def test_email_required(self):
        """Test that email is required"""
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="testpass123")


class ApprovalRequestModelTest(TestCase):
    """Test ApprovalRequest model functionality"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Company",
            domain="testcompany.com"
        )
        
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
            tenant=self.tenant
        )
        
        self.approver = User.objects.create_user(
            email="approver@example.com",
            password="testpass123",
            first_name="Jane",
            last_name="Smith",
            tenant=self.tenant
        )
    
    def test_create_expense_request(self):
        """Test creating an expense request"""
        request = ApprovalRequest.objects.create(
            title="Office Supplies",
            description="Need new office supplies for the team",
            category="expense",
            priority="medium",
            amount=Decimal("150.00"),
            created_by=self.user,
            tenant=self.tenant,
            expense_category="office_supplies",
            cost_center="IT Department"
        )
        
        self.assertEqual(request.title, "Office Supplies")
        self.assertEqual(request.category, "expense")
        self.assertEqual(request.status, "pending")
        self.assertEqual(request.amount, Decimal("150.00"))
        self.assertEqual(request.created_by, self.user)
    
    def test_approve_request(self):
        """Test approving a request"""
        request = ApprovalRequest.objects.create(
            title="Test Request",
            description="Test description",
            category="expense",
            created_by=self.user,
            tenant=self.tenant
        )
        
        success = request.approve(self.approver, "Approved for testing")
        
        self.assertTrue(success)
        self.assertEqual(request.status, "approved")
        self.assertEqual(request.approved_by, self.approver)
        self.assertIsNotNone(request.approved_at)
    
    def test_reject_request(self):
        """Test rejecting a request"""
        request = ApprovalRequest.objects.create(
            title="Test Request",
            description="Test description",
            category="expense",
            created_by=self.user,
            tenant=self.tenant
        )
        
        success = request.reject(self.approver, "Not within budget")
        
        self.assertTrue(success)
        self.assertEqual(request.status, "rejected")
        self.assertEqual(request.rejection_reason, "Not within budget")
        self.assertIsNotNone(request.rejected_at)
    
    def test_cannot_self_approve(self):
        """Test that users cannot approve their own requests"""
        request = ApprovalRequest.objects.create(
            title="Test Request",
            description="Test description",
            category="expense",
            created_by=self.user,
            tenant=self.tenant
        )
        
        success = request.approve(self.user, "Self approval")
        
        self.assertFalse(success)
        self.assertEqual(request.status, "pending")
    
    def test_request_str_representation(self):
        """Test request string representation"""
        request = ApprovalRequest.objects.create(
            title="Test Request",
            description="Test description",
            category="expense",
            created_by=self.user,
            tenant=self.tenant
        )
        
        expected = f"Test Request - {self.user.get_full_name()}"
        self.assertEqual(str(request), expected)


class BillingModelTest(TestCase):
    """Test Billing models functionality"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Company",
            domain="testcompany.com"
        )
        
        self.plan = Plan.objects.create(
            name="Starter",
            slug="starter",
            price=Decimal("29.99"),
            billing_cycle="monthly",
            max_users=5,
            max_requests_per_month=100
        )
    
    def test_create_plan(self):
        """Test plan creation"""
        self.assertEqual(self.plan.name, "Starter")
        self.assertEqual(self.plan.price, Decimal("29.99"))
        self.assertEqual(self.plan.max_users, 5)
        self.assertTrue(self.plan.is_active)
    
    def test_create_subscription(self):
        """Test subscription creation"""
        subscription = Subscription.objects.create(
            tenant=self.tenant,
            plan=self.plan,
            status="active"
        )
        
        self.assertEqual(subscription.tenant, self.tenant)
        self.assertEqual(subscription.plan, self.plan)
        self.assertEqual(subscription.status, "active")
    
    def test_create_invoice(self):
        """Test invoice creation"""
        subscription = Subscription.objects.create(
            tenant=self.tenant,
            plan=self.plan,
            status="active"
        )
        
        invoice = Invoice.objects.create(
            subscription=subscription,
            amount=self.plan.price,
            status="pending"
        )
        
        self.assertEqual(invoice.subscription, subscription)
        self.assertEqual(invoice.amount, self.plan.price)
        self.assertEqual(invoice.status, "pending")
        self.assertIsNotNone(invoice.invoice_number)