# ==================================================
# SecureApprove Django - Test Forms
# ==================================================

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.authentication.forms import (
    CustomUserCreationForm, 
    CustomAuthenticationForm,
    ProfileUpdateForm
)
from apps.requests.forms import (
    ExpenseRequestForm,
    PurchaseRequestForm,
    TravelRequestForm
)
from apps.authentication.models import Tenant

User = get_user_model()


class AuthenticationFormsTest(TestCase):
    """Test authentication forms"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Company",
            domain="testcompany.com"
        )
    
    def test_user_creation_form_valid(self):
        """Test user creation form with valid data"""
        form_data = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123',
            'terms_accepted': True
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_user_creation_form_password_mismatch(self):
        """Test user creation form with password mismatch"""
        form_data = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password1': 'complexpassword123',
            'password2': 'differentpassword',
            'terms_accepted': True
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_user_creation_form_no_terms(self):
        """Test user creation form without accepting terms"""
        form_data = {
            'email': 'test@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123',
            'terms_accepted': False
        }
        
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('terms_accepted', form.errors)
    
    def test_authentication_form_valid(self):
        """Test authentication form with valid credentials"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=self.tenant
        )
        
        form_data = {
            'username': 'test@example.com',
            'password': 'testpass123'
        }
        
        form = CustomAuthenticationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_profile_update_form_valid(self):
        """Test profile update form with valid data"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=self.tenant
        )
        
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '+1234567890',
            'company': 'Test Company'
        }
        
        form = ProfileUpdateForm(data=form_data, instance=user)
        self.assertTrue(form.is_valid())


class RequestFormsTest(TestCase):
    """Test request forms"""
    
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Test Company",
            domain="testcompany.com"
        )
        
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=self.tenant
        )
    
    def test_expense_form_valid(self):
        """Test expense request form with valid data"""
        form_data = {
            'title': 'Office Supplies',
            'description': 'Need new office supplies',
            'priority': 'medium',
            'amount': '150.00',
            'expense_category': 'office_supplies',
            'cost_center': 'IT Department',
            'receipt_reference': 'REC-001'
        }
        
        form = ExpenseRequestForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_expense_form_invalid_amount(self):
        """Test expense form with invalid amount"""
        form_data = {
            'title': 'Office Supplies',
            'description': 'Need new office supplies',
            'priority': 'medium',
            'amount': '-50.00',  # Negative amount
            'expense_category': 'office_supplies'
        }
        
        form = ExpenseRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('amount', form.errors)
    
    def test_purchase_form_valid(self):
        """Test purchase request form with valid data"""
        form_data = {
            'title': 'New Laptops',
            'description': 'Need new laptops for team',
            'priority': 'high',
            'amount': '2500.00',
            'vendor': 'Tech Supplier Inc',
            'cost_center': 'IT Department'
        }
        
        form = PurchaseRequestForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_travel_form_valid(self):
        """Test travel request form with valid data"""
        form_data = {
            'title': 'Conference Travel',
            'description': 'Travel to annual conference',
            'priority': 'medium',
            'amount': '1200.00',
            'destination': 'New York, NY',
            'start_date': '2024-03-15',
            'end_date': '2024-03-17'
        }
        
        form = TravelRequestForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_travel_form_invalid_dates(self):
        """Test travel form with invalid date range"""
        form_data = {
            'title': 'Conference Travel',
            'description': 'Travel to annual conference',
            'priority': 'medium',
            'amount': '1200.00',
            'destination': 'New York, NY',
            'start_date': '2024-03-17',  # End date before start date
            'end_date': '2024-03-15'
        }
        
        form = TravelRequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)