# ==================================================
# SecureApprove Django - Authentication URLs
# ==================================================

from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # ================================================
    # WebAuthn Passwordless Authentication (Primary)
    # ================================================
    
    # Main WebAuthn login page
    path('login/', views.WebAuthnLoginView.as_view(), name='webauthn_login'),
    # Register redirects to subscription plans
    path('register/', views.RedirectToSubscriptionView.as_view(), name='webauthn_register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # ================================================
    # WebAuthn API Endpoints
    # ================================================
    
    # Registration flow (3 steps)
    path('webauthn/register/', 
         views.webauthn_register_user, 
         name='webauthn_register_user'),
    path('webauthn/register/options/', 
         views.webauthn_register_options, 
         name='webauthn_register_options'),
    path('webauthn/register/verify/', 
         views.webauthn_register_verify, 
         name='webauthn_register_verify'),
    
    # Login flow (2 steps)
    path('webauthn/login/options/', 
         views.webauthn_login_options, 
         name='webauthn_login_options'),
    path('webauthn/login/verify/', 
         views.webauthn_login_verify, 
         name='webauthn_login_verify'),
    
    # Utility endpoints
    path('webauthn/user-check/', 
         views.webauthn_user_check, 
         name='webauthn_user_check'),
    path('webauthn/delete/', 
         views.webauthn_delete_credential, 
         name='webauthn_delete_credential'),
    path('webauthn/fallback/', 
         views.webauthn_create_fallback_credential, 
         name='webauthn_create_fallback_credential'),
    
    # Status endpoint
    path('status/', 
         views.check_auth_status, 
         name='check_auth_status'),
    
    # ================================================
    # Profile Management
    # ================================================
    
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
]