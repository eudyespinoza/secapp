# ==================================================
# SecureApprove Django - WebAuthn Step-Up for Approvals
# ==================================================

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.utils import timezone

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
