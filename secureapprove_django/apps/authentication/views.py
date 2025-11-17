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
from django.conf import settings
from secrets import token_urlsafe
import json
import logging

from .models import User, DevicePairingSession
from apps.tenants.models import Tenant, TenantUserInvite
from apps.tenants.utils import assign_tenant_from_reservation
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
    """
    DEPRECATED: Registration is now only available through subscription flow.
    This view redirects to the subscription plans page.
    """
    def get(self, request):
        messages.info(request, _('Please select a subscription plan to get started.'))
        return redirect('billing:select_plan')


class RedirectToSubscriptionView(View):
    """Redirect any registration attempts to subscription plans"""
    def get(self, request):
        messages.info(request, _('Please select a subscription plan to get started.'))
        return redirect('billing:select_plan')
    
    def post(self, request):
        return redirect('billing:select_plan')


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(BaseLogoutView):
    """Custom logout view (CSRF-exempt for proxy compatibility)"""
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
    """
    Create or reuse a user for WebAuthn registration (step 1).

    Business rules:
      - If the email already exists and has NO WebAuthn credentials -> allow registration.
      - If the email already exists and HAS WebAuthn credentials -> reject (409).
      - If the email does not exist:
          * Allow creation ONLY if:
              - There is a pending TenantUserInvite (reserved email), OR
              - It is the primary admin email (handled specially).
          * Otherwise, reject with 403 so the user must subscribe first.
    """
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
        
        # At this point, no user exists with this email.
        # Only allow creation if the email is RESERVED for a tenant,
        # or it is the primary admin email.
        is_reserved = TenantUserInvite.objects.filter(
            email=email,
            status='pending',
        ).exists()

        primary_admin_email = 'eudyespinoza@gmail.com'

        if not is_reserved and email != primary_admin_email:
            # This email is not allowed to self-register via WebAuthn.
            # The user must go through the subscription flow instead.
            return JsonResponse(
                {
                    'error': _(
                        'No account found for this email. Please subscribe to a plan or ask your administrator to add you.'
                    ),
                    'code': 'registration_not_allowed',
                },
                status=403,
            )

        # Create new user WITHOUT tenant; tenant assignment is handled after
        # successful WebAuthn registration via assign_tenant_from_reservation,
        # except for the primary admin which is ensured at startup.
        user_defaults = {
            'username': email,
            'email': email,
            'name': name,
            'role': 'requester',
            'is_active': True,
        }

        # Primary admin hardening: ensure correct flags and tenant if needed.
        if email == primary_admin_email:
            user_defaults.update(
                {
                    'role': 'admin',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )

        user = User.objects.create(**user_defaults)

        # For safety, ensure the primary admin is attached to the "secureapprove" tenant
        # even if entrypoint did not run in this environment.
        if email == primary_admin_email and not getattr(user, 'tenant_id', None):
            try:
                tenant, created_tenant = Tenant.objects.get_or_create(
                    key='secureapprove',
                    defaults={
                        'name': 'SecureApprove',
                        'plan_id': 'scale',
                        'seats': 10,
                        'approver_limit': 999,
                        'status': 'active',
                        'is_active': True,
                        'billing': {
                            'provider': 'internal',
                            'provisioned_via': 'webauthn_register_fallback',
                        },
                    },
                )
                user.tenant = tenant
                user.save(update_fields=['tenant', 'role', 'is_staff', 'is_superuser', 'is_active'])
            except Exception as e:
                logger.error(f"Error ensuring tenant for primary admin in webauthn_register_user: {e}")

        logger.info(f"Created new user for WebAuthn registration: {user.email}")
        
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


@login_required
@require_http_methods(["POST"])
def webauthn_register_begin(request):
    """
    Begin WebAuthn registration for an additional device for the logged-in user.

    Used from the profile page "Add Biometric Device" flow.
    """
    user = request.user
    try:
        options = webauthn_service.generate_registration_options(user)
        return JsonResponse(
            {
                "success": True,
                "publicKey": {
                    "challenge": options["challenge"],
                    "rp": options["rp"],
                    "user": options["user"],
                    "pubKeyCredParams": options["pubKeyCredParams"],
                    "timeout": options["timeout"],
                    "excludeCredentials": options["excludeCredentials"],
                    "authenticatorSelection": options["authenticatorSelection"],
                    "attestation": options["attestation"],
                },
            }
        )
    except Exception as e:
        logger.error(f"Error generating WebAuthn options for extra device: {e}")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=400,
        )


@login_required
@require_http_methods(["POST"])
def webauthn_register_complete(request):
    """
    Complete WebAuthn registration for an additional device for the logged-in user.

    Expects a `credential` object in the body with id/rawId/response/type as sent
    from the profile page JavaScript.
    """
    try:
        data = json.loads(request.body)
        credential = data.get("credential")
        if not credential:
            return JsonResponse(
                {"success": False, "error": _("Credential data is required")},
                status=400,
            )

        result = webauthn_service.verify_registration_response(request.user, credential)

        return JsonResponse(
            {
                "success": True,
                "credentialId": result.get("credential_id"),
            }
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": _("Invalid JSON data")},
            status=400,
        )
    except Exception as e:
        logger.error(f"Error completing WebAuthn registration for extra device: {e}")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=400,
        )


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

            # Associate user with a reserved tenant, if any
            assign_tenant_from_reservation(user)
            
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

            # Associate user with a reserved tenant on first login, if any
            assign_tenant_from_reservation(user)

            # Update last login timestamp
            now = timezone.now()
            user.last_login_at = now
            user.save(update_fields=['last_login_at'])

            # Mark in session the time of last WebAuthn verification
            request.session['last_webauthn_at'] = now.isoformat()
            
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
def profile_view(request):
    """User profile view"""
    # Get user's WebAuthn credentials from JSONField
    webauthn_credentials = []
    raw_creds = getattr(request.user, "webauthn_credentials", None)

    if raw_creds:
        # JSONField normally returns a Python list, pero contemplamos
        # también el caso legacy en el que haya quedado una cadena JSON.
        if isinstance(raw_creds, list):
            webauthn_credentials = raw_creds
        else:
            try:
                import json
                parsed = json.loads(raw_creds)
                if isinstance(parsed, list):
                    webauthn_credentials = parsed
            except Exception:
                webauthn_credentials = []

    return render(request, 'authentication/profile.html', {
        'user': request.user,
        'webauthn_credentials': webauthn_credentials,
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
            'userId': str(user.id),
            'reserved': False,
        })
    except User.DoesNotExist:
        reserved = TenantUserInvite.objects.filter(
            email=email,
            status='pending',
        ).exists()
        return JsonResponse({
            'exists': False,
            'hasCredentials': False,
            'userId': None,
            'reserved': reserved,
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
        
        # Get current credentials from JSONField (list or JSON string)
        webauthn_credentials = []
        raw_creds = getattr(user, "webauthn_credentials", None)
        if raw_creds:
            if isinstance(raw_creds, list):
                webauthn_credentials = raw_creds
            else:
                try:
                    parsed = json.loads(raw_creds)
                    if isinstance(parsed, list):
                        webauthn_credentials = parsed
                except Exception:
                    webauthn_credentials = []
        
        # Filter out the credential to delete
        updated_credentials = [
            cred for cred in webauthn_credentials 
            if str(cred.get('credential_id', '')) != str(credential_id)
        ]
        
        # Update user's credentials (JSONField, almacenamos como lista)
        user.webauthn_credentials = updated_credentials
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
            'public_key': None,
            'sign_count': 0,
            'created_at': timezone.now().isoformat(),
            'name': 'Auto-generated Key',
            'type': 'fallback',
            'authenticator_type': 'software',
        }
        
        # Store the credential in JSONField
        webauthn_credentials = []
        raw_creds = getattr(user, "webauthn_credentials", None)
        if raw_creds:
            if isinstance(raw_creds, list):
                webauthn_credentials = raw_creds
            else:
                try:
                    parsed = json.loads(raw_creds)
                    if isinstance(parsed, list):
                        webauthn_credentials = parsed
                except Exception:
                    webauthn_credentials = []
        
        webauthn_credentials.append(fallback_credential)
        user.webauthn_credentials = webauthn_credentials
        user.save()
        
        # Log the user in after creating fallback credential
        login(request, user)
        # Associate with reserved tenant if applicable
        assign_tenant_from_reservation(user)
        
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


# ================================================
# Device Pairing Flow (pair new device via link/QR)
# ================================================

@login_required
@require_http_methods(["POST"])
def device_pairing_create(request):
    """
    Create a new pairing session for the current user.
    Returns a URL (with language prefix) that can be opened on another device.
    """
    ttl_minutes = 10
    expires_at = timezone.now() + timezone.timedelta(minutes=ttl_minutes)

    # Generate secure random token
    token = token_urlsafe(32)

    session = DevicePairingSession.objects.create(
        user=request.user,
        token=token,
        status='pending',
        expires_at=expires_at,
    )

    # Build absolute URL with current language prefix
    from django.utils.translation import get_language
    lang = get_language() or settings.LANGUAGE_CODE
    pairing_path = f"/{lang}/auth/device-pairing/{session.token}/"
    pairing_url = request.build_absolute_uri(pairing_path)

    return JsonResponse(
        {
            "success": True,
            "pairingUrl": pairing_url,
            "expiresInSeconds": ttl_minutes * 60,
        }
    )


def _get_valid_pairing_session(token: str):
    try:
        session = DevicePairingSession.objects.select_related("user").get(token=token)
    except DevicePairingSession.DoesNotExist:
        return None

    if session.status != "pending":
        return None
    if session.is_expired:
        session.status = "expired"
        session.save(update_fields=["status"])
        return None
    return session


class DevicePairingLandingView(View):
    """
    Public landing page when opening a pairing link on a new device.
    """

    template_name = "authentication/device_pairing_landing.html"

    def get(self, request, token):
        session = _get_valid_pairing_session(token)
        if not session:
            return render(
                request,
                self.template_name,
                {"invalid": True},
            )

        return render(
            request,
            self.template_name,
            {
                "invalid": False,
                "pairing_token": token,
                "user_email": session.user.email,
                "expires_at": session.expires_at,
            },
        )


@csrf_exempt
@require_http_methods(["POST"])
def device_pairing_begin(request, token):
    """
    Begin WebAuthn registration on the pairing device.
    The user is identified via the pairing token.
    """
    session = _get_valid_pairing_session(token)
    if not session:
        return JsonResponse(
            {"success": False, "error": _("Pairing session not found or expired.")},
            status=400,
        )

    try:
        options = webauthn_service.generate_registration_options(session.user)
        return JsonResponse(
            {
                "success": True,
                "publicKey": {
                    "challenge": options["challenge"],
                    "rp": options["rp"],
                    "user": options["user"],
                    "pubKeyCredParams": options["pubKeyCredParams"],
                    "timeout": options["timeout"],
                    "excludeCredentials": options["excludeCredentials"],
                    "authenticatorSelection": options["authenticatorSelection"],
                    "attestation": options["attestation"],
                },
            }
        )
    except Exception as e:
        logger.error(f"Error generating WebAuthn options for device pairing: {e}")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=400,
        )


@csrf_exempt
@require_http_methods(["POST"])
def device_pairing_complete(request, token):
    """
    Complete WebAuthn registration on the pairing device.
    """
    session = _get_valid_pairing_session(token)
    if not session:
        return JsonResponse(
            {"success": False, "error": _("Pairing session not found or expired.")},
            status=400,
        )

    try:
        data = json.loads(request.body)
        credential = data.get("credential")
        if not credential:
            return JsonResponse(
                {"success": False, "error": _("Credential data is required")},
                status=400,
            )

        result = webauthn_service.verify_registration_response(session.user, credential)

        # Mark session as completed
        session.status = "completed"
        session.paired_at = timezone.now()
        session.paired_user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
        session.paired_platform = data.get("platform", "")[:255]
        session.save(
            update_fields=["status", "paired_at", "paired_user_agent", "paired_platform"]
        )

        return JsonResponse(
            {
                "success": True,
                "credentialId": result.get("credential_id"),
            }
        )
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": _("Invalid JSON data")},
            status=400,
        )
    except Exception as e:
        logger.error(f"Error completing device pairing: {e}")
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=400,
        )


@login_required
@require_http_methods(["GET"])
def device_pairing_status(request, token):
    """
    Check the status of a pairing session for the current user.
    """
    try:
        session = DevicePairingSession.objects.get(token=token, user=request.user)
    except DevicePairingSession.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": _("Pairing session not found.")},
            status=404,
        )

    status = session.status
    if session.is_expired and status == "pending":
        status = "expired"

    return JsonResponse(
        {
            "success": True,
            "status": status,
        }
    )


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
