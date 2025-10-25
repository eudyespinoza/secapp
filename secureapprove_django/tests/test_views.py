# ==================================================
# SecureApprove Django - Test Views
# ==================================================

import pytest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from decimal import Decimal

from apps.authentication.models import Tenant
from apps.requests.models import ApprovalRequest

User = get_user_model()


class AuthenticationViewsTest(TestCase):
    """Test authentication views"""
    
    def setUp(self):
        self.client = Client()
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
    
    def test_login_view_get(self):
        """Test login view GET request"""
        response = self.client.get(reverse('authentication:login'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In')
        self.assertContains(response, 'Email Address')
    
    def test_login_valid_credentials(self):
        """Test login with valid credentials"""
        response = self.client.post(reverse('authentication:login'), {
            'username': 'test@example.com',
            'password': 'testpass123'
        })
        
        self.assertRedirects(response, reverse('dashboard:index'))
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = self.client.post(reverse('authentication:login'), {
            'username': 'test@example.com',
            'password': 'wrongpassword'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct')
    
    def test_register_view_get(self):
        """Test register view GET request"""
        response = self.client.get(reverse('authentication:register'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')
        self.assertContains(response, 'Email')
    
    def test_register_valid_data(self):
        """Test registration with valid data"""
        response = self.client.post(reverse('authentication:register'), {
            'email': 'newuser@example.com',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123',
            'terms_accepted': True
        })
        
        self.assertRedirects(response, reverse('authentication:login'))
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())
    
    def test_profile_view_authenticated(self):
        """Test profile view for authenticated user"""
        self.client.login(username='test@example.com', password='testpass123')
        response = self.client.get(reverse('authentication:profile'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Profile')
        self.assertContains(response, self.user.first_name)
    
    def test_profile_view_anonymous(self):
        """Test profile view redirects for anonymous user"""
        response = self.client.get(reverse('authentication:profile'))
        
        self.assertRedirects(response, f"/auth/login/?next={reverse('authentication:profile')}")


class RequestViewsTest(TestCase):
    """Test request management views"""
    
    def setUp(self):
        self.client = Client()
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
        
        self.request = ApprovalRequest.objects.create(
            title="Test Request",
            description="Test description",
            category="expense",
            priority="medium",
            amount=Decimal("100.00"),
            created_by=self.user,
            tenant=self.tenant
        )
    
    def test_dashboard_view_authenticated(self):
        """Test dashboard view for authenticated user"""
        self.client.login(username='test@example.com', password='testpass123')
        response = self.client.get(reverse('dashboard:index'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
        self.assertContains(response, 'Total Requests')
    
    def test_request_list_view(self):
        """Test request list view"""
        self.client.login(username='test@example.com', password='testpass123')
        response = self.client.get(reverse('requests:list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All Requests')
        self.assertContains(response, self.request.title)
    
    def test_request_detail_view(self):
        """Test request detail view"""
        self.client.login(username='test@example.com', password='testpass123')
        response = self.client.get(reverse('requests:detail', kwargs={'pk': self.request.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.request.title)
        self.assertContains(response, self.request.description)
    
    def test_request_create_view_get(self):
        """Test request create view GET"""
        self.client.login(username='test@example.com', password='testpass123')
        response = self.client.get(reverse('requests:create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'New Request')
        self.assertContains(response, 'Category')
    
    def test_request_create_view_post(self):
        """Test request create view POST"""
        self.client.login(username='test@example.com', password='testpass123')
        response = self.client.post(reverse('requests:create'), {
            'title': 'New Test Request',
            'description': 'New test description',
            'category': 'purchase',
            'priority': 'high',
            'amount': '250.00'
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after successful creation
        self.assertTrue(ApprovalRequest.objects.filter(title='New Test Request').exists())
    
    def test_request_approve_view(self):
        """Test request approval"""
        self.client.login(username='approver@example.com', password='testpass123')
        response = self.client.post(reverse('requests:approve', kwargs={'pk': self.request.pk}), {
            'approval_notes': 'Approved for testing'
        })
        
        self.assertRedirects(response, reverse('requests:detail', kwargs={'pk': self.request.pk}))
        
        # Refresh from database
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, 'approved')
    
    def test_request_reject_view(self):
        """Test request rejection"""
        self.client.login(username='approver@example.com', password='testpass123')
        response = self.client.post(reverse('requests:reject', kwargs={'pk': self.request.pk}), {
            'rejection_reason': 'Not within budget'
        })
        
        self.assertRedirects(response, reverse('requests:detail', kwargs={'pk': self.request.pk}))
        
        # Refresh from database
        self.request.refresh_from_db()
        self.assertEqual(self.request.status, 'rejected')
    
    def test_anonymous_redirects(self):
        """Test that anonymous users are redirected to login"""
        views_to_test = [
            'dashboard:index',
            'requests:list',
            'requests:create',
            ('requests:detail', {'pk': self.request.pk}),
        ]
        
        for view in views_to_test:
            if isinstance(view, tuple):
                url = reverse(view[0], kwargs=view[1])
            else:
                url = reverse(view)
            
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.url.startswith('/auth/login/'))


class APIViewsTest(TestCase):
    """Test API endpoints"""
    
    def setUp(self):
        self.client = Client()
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
        
        self.request = ApprovalRequest.objects.create(
            title="Test Request",
            description="Test description",
            category="expense",
            created_by=self.user,
            tenant=self.tenant
        )
    
    def test_api_requests_list_authenticated(self):
        """Test API requests list with authentication"""
        self.client.login(username='test@example.com', password='testpass123')
        response = self.client.get('/api/requests/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_api_requests_list_anonymous(self):
        """Test API requests list without authentication"""
        response = self.client.get('/api/requests/')
        
        self.assertEqual(response.status_code, 401)  # Unauthorized
    
    def test_api_dashboard_stats(self):
        """Test API dashboard stats"""
        self.client.login(username='test@example.com', password='testpass123')
        response = self.client.get('/api/dashboard/stats/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('total_requests', data)
        self.assertIn('pending_requests', data)
    
    def test_api_swagger_docs(self):
        """Test API documentation is accessible"""
        response = self.client.get('/api/docs/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SecureApprove API')