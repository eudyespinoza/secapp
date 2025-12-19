# ==================================================
# SecureApprove Django - WebAuthn Step-Up for Approvals
# ==================================================

import json
import logging
import secrets
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.utils import timezone
from django.core.cache import cache

from .models import ApprovalRequest
from apps.authentication.models import ApprovalAudit
from apps.authentication.webauthn_service import webauthn_service

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
@require_http_methods(["POST"])
def approval_webauthn_options(request, approval_id):
    """
    Generate WebAuthn challenge for step-up authentication on approval.
    
    This endpoint is called when a user clicks "Approve" or "Reject" on an approval request.
    It generates a fresh WebAuthn challenge specifically for this approval action.
    """
    try:
        # Get approval request
        approval_request = get_object_or_404(
            ApprovalRequest,
            pk=approval_id,
            tenant=request.user.tenant
        )
        
        # Validate user can approve
        if not request.user.can_approve_requests():
            return JsonResponse({
                'error': _('You do not have permission to approve requests')
            }, status=403)
        
        if approval_request.status != 'pending':
            return JsonResponse({
                'error': _('This request has already been processed')
            }, status=400)
        
        if approval_request.requester == request.user:
            return JsonResponse({
                'error': _('You cannot approve your own request')
            }, status=400)
        
        # Check if user has WebAuthn credentials
        if not request.user.has_webauthn_credentials:
            return JsonResponse({
                'error': _('No WebAuthn credentials registered. Please register a device first.')
            }, status=400)
        
        # Parse action from request body
        data = json.loads(request.body)
        action = data.get('action', 'approve')  # 'approve' or 'reject'
        
        if action not in ['approve', 'reject']:
            return JsonResponse({
                'error': _('Invalid action. Must be "approve" or "reject".')
            }, status=400)
        
        # Prepare context data for cryptographic binding (optional)
        context_data = {
            'approval_id': str(approval_request.pk),
            'action': action,
            'title': approval_request.title,
            'category': approval_request.category,
            'amount': str(approval_request.amount) if approval_request.amount else None,
            'requester_id': str(approval_request.requester.id),
        }
        
        # Generate WebAuthn challenge for this specific approval
        options = webauthn_service.generate_approval_challenge(
            user=request.user,
            approval_id=str(approval_request.pk),
            context_data=context_data
        )
        
        logger.info(
            f"Generated WebAuthn approval challenge for user {request.user.email}, "
            f"approval {approval_request.pk}, action {action}"
        )
        
        return JsonResponse({
            'options': options,
            'approvalId': str(approval_request.pk),
            'action': action,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON data')}, status=400)
    except Exception as e:
        logger.error(f"Error generating approval WebAuthn options: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def approval_webauthn_verify(request, approval_id):
    """
    Verify WebAuthn response and execute the approval/rejection action.
    
    This endpoint verifies the WebAuthn signature and, if valid, performs the approval/rejection.
    It also creates an audit log entry.
    """
    try:
        data = json.loads(request.body)
        
        # Get approval request
        approval_request = get_object_or_404(
            ApprovalRequest,
            pk=approval_id,
            tenant=request.user.tenant
        )
        
        # Validate user can approve
        if not request.user.can_approve_requests():
            return JsonResponse({
                'error': _('You do not have permission to approve requests')
            }, status=403)
        
        if approval_request.status != 'pending':
            return JsonResponse({
                'error': _('This request has already been processed')
            }, status=400)
        
        if approval_request.requester == request.user:
            return JsonResponse({
                'error': _('You cannot approve your own request')
            }, status=400)
        
        # Extract data from request
        action = data.get('action', 'approve')
        credential_data = data.get('response')
        comment = data.get('comment', '')
        reason = data.get('reason', '')  # For rejections
        
        if not credential_data:
            return JsonResponse({
                'error': _('WebAuthn response is required')
            }, status=400)
        
        if action not in ['approve', 'reject']:
            return JsonResponse({
                'error': _('Invalid action')
            }, status=400)
        
        if action == 'reject' and not reason:
            return JsonResponse({
                'error': _('Rejection reason is required')
            }, status=400)
        
        # Prepare context data (must match what was sent in options)
        context_data = {
            'approval_id': str(approval_request.pk),
            'action': action,
            'title': approval_request.title,
            'category': approval_request.category,
            'amount': str(approval_request.amount) if approval_request.amount else None,
            'requester_id': str(approval_request.requester.id),
        }
        
        # Verify WebAuthn response
        try:
            verification_result = webauthn_service.verify_approval_response(
                user=request.user,
                approval_id=str(approval_request.pk),
                credential_data=credential_data,
                context_data=context_data
            )
        except ValueError as e:
            # Create failed audit log
            ApprovalAudit.objects.create(
                approval_request=approval_request,
                user=request.user,
                credential_id='unknown',
                challenge_id='unknown',
                action=action,
                status='failed',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                context_data=context_data,
                error_message=str(e)
            )
            
            logger.warning(
                f"Failed WebAuthn verification for approval {approval_request.pk}: {str(e)}"
            )
            
            return JsonResponse({
                'error': _('Authentication verification failed: {}').format(str(e))
            }, status=400)
        
        if not verification_result.get('verified'):
            # Create failed audit log
            ApprovalAudit.objects.create(
                approval_request=approval_request,
                user=request.user,
                credential_id=verification_result.get('credential_id', 'unknown'),
                challenge_id=verification_result.get('challenge_id', 'unknown'),
                action=action,
                status='failed',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                context_data=context_data,
                error_message='Verification returned false'
            )
            
            return JsonResponse({
                'error': _('Authentication verification failed')
            }, status=400)
        
        # WebAuthn verified successfully - perform the action
        try:
            if action == 'approve':
                approval_request.approve(request.user, comment)
                message = _('Request approved successfully')
            else:  # reject
                approval_request.reject(request.user, reason)
                message = _('Request rejected successfully')
            
            # Update session flag
            request.session['last_webauthn_at'] = timezone.now().isoformat()
            
            # Create success audit log
            audit = ApprovalAudit.objects.create(
                approval_request=approval_request,
                user=request.user,
                credential_id=verification_result['credential_id'],
                challenge_id=verification_result['challenge_id'],
                action=action,
                status='success',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                context_data=context_data
            )
            
            logger.info(
                f"User {request.user.email} {action}ed approval {approval_request.pk} "
                f"with WebAuthn credential {verification_result['credential_id'][:16]}..."
            )
            
            return JsonResponse({
                'success': True,
                'message': message,
                'approval': {
                    'id': str(approval_request.pk),
                    'status': approval_request.status,
                    'action': action,
                },
                'audit_id': str(audit.id),
            })
            
        except Exception as e:
            # Create failed audit log
            ApprovalAudit.objects.create(
                approval_request=approval_request,
                user=request.user,
                credential_id=verification_result['credential_id'],
                challenge_id=verification_result['challenge_id'],
                action=action,
                status='failed',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                context_data=context_data,
                error_message=str(e)
            )
            
            logger.error(f"Error performing approval action: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON data')}, status=400)
    except Exception as e:
        logger.error(f"Error verifying approval WebAuthn: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


# ==================================================
# WebAuthn Step-Up for Request Creation
# ==================================================

@login_required
@require_http_methods(["POST"])
def create_request_webauthn_options(request):
    """
    Generate WebAuthn challenge for step-up authentication before creating a request.
    
    This endpoint is called when a user submits the request creation form.
    It generates a fresh WebAuthn challenge specifically for this creation action.
    """
    try:
        # Check if user has WebAuthn credentials
        if not request.user.has_webauthn_credentials:
            return JsonResponse({
                'error': _('No WebAuthn credentials registered. Please register a device first.'),
                'noCredentials': True
            }, status=400)
        
        # Parse request data to include in context
        data = json.loads(request.body)
        
        # Generate a unique creation token
        creation_token = secrets.token_urlsafe(32)
        
        # Prepare context data for cryptographic binding
        context_data = {
            'action': 'create_request',
            'creation_token': creation_token,
            'title': data.get('title', ''),
            'category': data.get('category', ''),
            'amount': data.get('amount', ''),
            'user_id': str(request.user.id),
        }
        
        # Generate WebAuthn challenge for this creation
        options = webauthn_service.generate_approval_challenge(
            user=request.user,
            approval_id=f"create_{creation_token}",  # Using token as pseudo-approval ID
            context_data=context_data
        )
        
        # Store the creation token in cache for verification
        cache_key = f"webauthn_create_request_{request.user.id}_{creation_token}"
        cache.set(cache_key, {
            'token': creation_token,
            'context': context_data,
            'created_at': timezone.now().isoformat(),
        }, timeout=300)  # 5 minutes timeout
        
        logger.info(
            f"Generated WebAuthn creation challenge for user {request.user.email}, "
            f"token {creation_token[:16]}..."
        )
        
        return JsonResponse({
            'options': options,
            'creationToken': creation_token,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON data')}, status=400)
    except Exception as e:
        logger.error(f"Error generating creation WebAuthn options: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def create_request_webauthn_verify(request):
    """
    Verify WebAuthn response for request creation.
    
    This endpoint verifies the WebAuthn signature and returns a verification token
    that can be used to submit the request creation form.
    """
    try:
        data = json.loads(request.body)
        
        # Extract data from request
        creation_token = data.get('creationToken')
        credential_data = data.get('response')
        
        if not creation_token:
            return JsonResponse({
                'error': _('Creation token is required')
            }, status=400)
        
        if not credential_data:
            return JsonResponse({
                'error': _('WebAuthn response is required')
            }, status=400)
        
        # Verify the creation token exists in cache
        cache_key = f"webauthn_create_request_{request.user.id}_{creation_token}"
        cached_data = cache.get(cache_key)
        
        if not cached_data:
            return JsonResponse({
                'error': _('Creation token expired or invalid. Please try again.')
            }, status=400)
        
        context_data = cached_data.get('context', {})
        
        # Verify WebAuthn response
        try:
            verification_result = webauthn_service.verify_approval_response(
                user=request.user,
                approval_id=f"create_{creation_token}",
                credential_data=credential_data,
                context_data=context_data
            )
        except ValueError as e:
            logger.warning(
                f"Failed WebAuthn verification for creation by {request.user.email}: {str(e)}"
            )
            return JsonResponse({
                'error': _('Authentication verification failed: {}').format(str(e))
            }, status=400)
        
        if not verification_result.get('verified'):
            return JsonResponse({
                'error': _('Authentication verification failed')
            }, status=400)
        
        # Generate a verified token that the form can use
        verified_token = secrets.token_urlsafe(32)
        
        # Store the verified token for the actual form submission
        verified_cache_key = f"webauthn_create_verified_{request.user.id}_{verified_token}"
        cache.set(verified_cache_key, {
            'token': verified_token,
            'creation_token': creation_token,
            'verified_at': timezone.now().isoformat(),
            'credential_id': verification_result.get('credential_id'),
        }, timeout=300)  # 5 minutes to submit the form
        
        # Clean up the creation token
        cache.delete(cache_key)
        
        # Update session flag
        request.session['last_webauthn_at'] = timezone.now().isoformat()
        
        logger.info(
            f"User {request.user.email} verified WebAuthn for request creation, "
            f"credential {verification_result.get('credential_id', 'unknown')[:16]}..."
        )
        
        return JsonResponse({
            'success': True,
            'verifiedToken': verified_token,
            'message': _('Authentication successful. You can now submit your request.')
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': _('Invalid JSON data')}, status=400)
    except Exception as e:
        logger.error(f"Error verifying creation WebAuthn: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
