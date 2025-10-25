# ==================================================
# SecureApprove Django - Authentication Views
# ==================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView as BaseLogoutView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
import json
import logging

from .models import User
from .webauthn_service import webauthn_service

logger = logging.getLogger(__name__)


# ================================================
# WebAuthn Passwordless Authentication Views
# ================================================

class WebAuthnLoginView(View):
    """WebAuthn passwordless login view"""
    template_name = 'authentication/webauthn_login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('landing:index')
        return render(request, self.template_name)
    
    def post(self, request):
        # Handle traditional form fallback if needed
        return render(request, self.template_name)


class WebAuthnRegisterView(View):
    """WebAuthn passwordless registration view"""
    template_name = 'authentication/webauthn_register.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('landing:index')
        return render(request, self.template_name)


class LogoutView(BaseLogoutView):
    """Custom logout view"""
    next_page = 'authentication:webauthn_login'
    
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, _('You have been successfully logged out.'))
        return super().dispatch(request, *args, **kwargs)


# ================================================
# WebAuthn API Endpoints (Passwordless Authentication)
# ================================================

@csrf_exempt
@require_http_methods(["POST"])
def webauthn_register_user(request):
    """Create new user for WebAuthn registration (step 1) - NO TENANT CREATED"""
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        
        if not name or not email:
            return JsonResponse({'error': _('Name and email are required')}, status=400)
        
        # Check if user exists
        existing_user = User.objects.filter(email=email).first()
        if existing_user:
            # If user exists but has no credentials, allow to continue registration
            if not existing_user.webauthn_credentials:
                return JsonResponse({
                    'id': str(existing_user.id),
                    'name': existing_user.name,
                    'email': existing_user.email,
                    'role': existing_user.role,
                    'hasTenant': existing_user.tenant_id is not None,
                    'message': _('User exists but needs to complete WebAuthn registration')
                })
            else:
                return JsonResponse({'error': _('Email already registered with WebAuthn credentials')}, status=409)
        
        # Create new user WITHOUT tenant (tenant is created after payment)
        user = User.objects.create(
            username=email,  # Use email as username
            email=email,
            name=name,
            role='requester',  # Default role for new users
            is_active=True,
            tenant=None  # NO TENANT - will be created after subscription payment
        )
        
        logger.info(f"Created new user for WebAuthn registration: {user.email} (NO TENANT)")
        
        return JsonResponse({
            'id': str(user.id),
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'hasTenant': False,
            'message': _('User created successfully. Now register WebAuthn credential.')
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON data')}, status=400)
    except Exception as e:
        logger.error(f"Error creating user for WebAuthn: {str(e)}")
        return JsonResponse({'error': _('Registration failed')}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def webauthn_register_options(request):
    """Get WebAuthn registration options (step 2)"""
    try:
        data = json.loads(request.body)
        user_id = data.get('userId')
        
        if not user_id:
            return JsonResponse({'error': _('User ID is required')}, status=400)
        
        user = get_object_or_404(User, id=user_id)
        
        # Generate registration options
        try:
            print(f"DEBUG: About to call webauthn_service.generate_registration_options for user {user.id}")
            options = webauthn_service.generate_registration_options(user)
            print(f"DEBUG: Successfully generated options: {type(options)}")
        except Exception as e:
            print(f"DEBUG: Exception in generate_registration_options: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            raise
        
        logger.info(f"Generated WebAuthn registration options for user: {user.email}")
        
        return JsonResponse(options)
        
    except User.DoesNotExist:
        return JsonResponse({'error': _('User not found')}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON data')}, status=400)
    except Exception as e:
        logger.error(f"Error generating WebAuthn registration options: {str(e)}")
        return JsonResponse({'error': _('Failed to generate registration options')}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def webauthn_register_verify(request):
    """Verify WebAuthn registration (step 3)"""
    try:
        data = json.loads(request.body)
        user_id = data.get('userId')
        response_data = data.get('response')
        
        if not user_id or not response_data:
            return JsonResponse({'error': _('User ID and response are required')}, status=400)
        
        user = get_object_or_404(User, id=user_id)
        
        # Verify registration
        result = webauthn_service.verify_registration_response(user, response_data)
        
        if result['verified']:
            logger.info(f"WebAuthn registration successful for user: {user.email}")
            
            # Log the user in after successful registration
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            
            return JsonResponse({
                'verified': True,
                'user': {
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email,
                    'role': user.role,
                    'hasTenant': hasattr(user, 'tenant') and user.tenant is not None
                },
                'redirect_url': '/dashboard/' if hasattr(user, 'tenant') and user.tenant else '/billing/',
                'message': _('Registration successful! Redirecting...')
            })
        else:
            return JsonResponse({'error': _('Registration verification failed')}, status=400)
        
    except User.DoesNotExist:
        return JsonResponse({'error': _('User not found')}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON data')}, status=400)
    except Exception as e:
        logger.error(f"Error verifying WebAuthn registration: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def webauthn_login_options(request):
    """Get WebAuthn authentication options for login"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        
        if not email:
            return JsonResponse({'error': _('Email is required')}, status=400)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({'error': _('User not found')}, status=404)
        
        if not user.has_webauthn_credentials:
            return JsonResponse({'error': _('No WebAuthn credentials registered for this user')}, status=400)
        
        # Generate authentication options
        options = webauthn_service.generate_authentication_options(user)
        
        logger.info(f"Generated WebAuthn login options for user: {email}")
        
        return JsonResponse({
            'options': options,
            'userId': str(user.id)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON data')}, status=400)
    except Exception as e:
        logger.error(f"Error generating WebAuthn login options: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def webauthn_login_verify(request):
    """Verify WebAuthn authentication for login"""
    try:
        data = json.loads(request.body)
        user_id = data.get('userId')
        response_data = data.get('response')
        
        if not user_id or not response_data:
            return JsonResponse({'error': _('User ID and response are required')}, status=400)
        
        user = get_object_or_404(User, id=user_id)
        
        # Verify authentication
        result = webauthn_service.verify_authentication_response(user, response_data)
        
        if result['verified']:
            logger.info(f"WebAuthn login successful for user: {user.email}")
            
            # Log the user in
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            
            # Update last login
            user.last_login_at = timezone.now()
            user.save(update_fields=['last_login_at'])
            
            return JsonResponse({
                'verified': True,
                'user': {
                    'id': str(user.id),
                    'name': user.name,
                    'email': user.email,
                    'role': user.role,
                }
            })
        else:
            return JsonResponse({'error': _('Authentication verification failed')}, status=400)
        
    except User.DoesNotExist:
        return JsonResponse({'error': _('User not found')}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON data')}, status=400)
    except Exception as e:
        logger.error(f"Error verifying WebAuthn login: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ================================================
# Profile Management
# ================================================

@login_required
@login_required
def profile_view(request):
    """User profile view"""
    # Get user's WebAuthn credentials
    webauthn_credentials = []
    if hasattr(request.user, 'webauthn_credentials') and request.user.webauthn_credentials:
        try:
            import json
            credentials_data = json.loads(request.user.webauthn_credentials)
            if isinstance(credentials_data, list):
                webauthn_credentials = credentials_data
        except (json.JSONDecodeError, AttributeError):
            webauthn_credentials = []
    
    return render(request, 'authentication/profile.html', {
        'user': request.user,
        'webauthn_credentials': webauthn_credentials
    })


@login_required
def profile_edit(request):
    """Edit user profile"""
    if request.method == 'POST':
        user = request.user
        user.name = request.POST.get('name', user.name)
        user.save()
        messages.success(request, _('Profile updated successfully.'))
        return redirect('authentication:profile')
    
    return render(request, 'authentication/profile_edit.html', {
        'user': request.user
    })


# ================================================
# Utility Views
# ================================================

@csrf_exempt
@require_http_methods(["GET"])
def webauthn_user_check(request):
    """Check if user exists and has WebAuthn credentials"""
    email = request.GET.get('email', '').strip().lower()
    
    if not email:
        return JsonResponse({'error': _('Email is required')}, status=400)
    
    try:
        user = User.objects.get(email=email)
        return JsonResponse({
            'exists': True,
            'hasCredentials': user.has_webauthn_credentials,
            'userId': str(user.id)
        })
    except User.DoesNotExist:
        return JsonResponse({
            'exists': False,
            'hasCredentials': False,
            'userId': None
        })


@login_required
@require_http_methods(["POST"])
def webauthn_delete_credential(request):
    """Delete a WebAuthn credential"""
    try:
        data = json.loads(request.body)
        credential_id = data.get('credential_id')
        
        if not credential_id:
            return JsonResponse({'error': _('Credential ID is required')}, status=400)
        
        user = request.user
        
        # Get current credentials
        webauthn_credentials = []
        if hasattr(user, 'webauthn_credentials') and user.webauthn_credentials:
            try:
                credentials_data = json.loads(user.webauthn_credentials)
                if isinstance(credentials_data, list):
                    webauthn_credentials = credentials_data
            except (json.JSONDecodeError, AttributeError):
                webauthn_credentials = []
        
        # Filter out the credential to delete
        updated_credentials = [
            cred for cred in webauthn_credentials 
            if str(cred.get('credential_id', '')) != str(credential_id)
        ]
        
        # Update user's credentials
        user.webauthn_credentials = json.dumps(updated_credentials) if updated_credentials else None
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': _('Device removed successfully'),
            'remaining_credentials': len(updated_credentials)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON data')}, status=400)
    except Exception as e:
        logger.error(f"Error deleting WebAuthn credential: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def webauthn_create_fallback_credential(request):
    """Create a fallback credential for devices without WebAuthn support"""
    try:
        data = json.loads(request.body)
        user_id = data.get('userId')
        
        if not user_id:
            return JsonResponse({'error': _('User ID is required')}, status=400)
        
        user = get_object_or_404(User, id=user_id)
        
        # Generate a unique credential ID for this user
        import secrets
        import base64
        
        credential_id = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        
        # Create a fallback credential
        fallback_credential = {
            'credential_id': credential_id,
            'public_key': None,  # No actual public key for fallback
            'sign_count': 0,
            'created_at': timezone.now().isoformat(),
            'name': f'Auto-generated Key',
            'type': 'fallback',
            'authenticator_type': 'software'
        }
        
        # Store the credential
        webauthn_credentials = []
        if hasattr(user, 'webauthn_credentials') and user.webauthn_credentials:
            try:
                credentials_data = json.loads(user.webauthn_credentials)
                if isinstance(credentials_data, list):
                    webauthn_credentials = credentials_data
            except (json.JSONDecodeError, AttributeError):
                webauthn_credentials = []
        
        webauthn_credentials.append(fallback_credential)
        user.webauthn_credentials = json.dumps(webauthn_credentials)
        user.save()
        
        # Log the user in after creating fallback credential
        login(request, user)
        
        return JsonResponse({
            'success': True,
            'message': _('Fallback credential created successfully'),
            'credential_id': credential_id,
            'user': {
                'id': str(user.id),
                'name': user.name,
                'email': user.email,
                'role': user.role,
                'hasTenant': hasattr(user, 'owned_tenant') and user.owned_tenant is not None
            },
            'redirect_url': '/dashboard/' if hasattr(user, 'owned_tenant') and user.owned_tenant else '/billing/',
            'authenticated': True
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON data')}, status=400)
    except Exception as e:
        logger.error(f"Error creating fallback credential: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def check_auth_status(request):
    """Check if user is authenticated and return user info"""
    if request.user.is_authenticated:
        # Check if user has tenant
        has_tenant = hasattr(request.user, 'tenant') and request.user.tenant is not None
        
        return JsonResponse({
            'authenticated': True,
            'user': {
                'id': str(request.user.id),
                'name': request.user.name if hasattr(request.user, 'name') else request.user.get_full_name(),
                'email': request.user.email,
                'role': request.user.role if hasattr(request.user, 'role') else 'user',
                'hasTenant': has_tenant,
                'tenantId': str(request.user.tenant.id) if has_tenant else None,
            },
            'next_url': '/dashboard/' if has_tenant else '/billing/'
        })
    else:
        return JsonResponse({
            'authenticated': False,
            'next_url': '/auth/login/'
        })


# Import timezone for last_login_at
from django.utils import timezone