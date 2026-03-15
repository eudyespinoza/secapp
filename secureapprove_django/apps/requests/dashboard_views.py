# ==================================================
# SecureApprove Django - Dashboard Views
# ==================================================

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils.translation import gettext as _
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import hashlib
import secrets
import uuid
from datetime import timedelta
from .models import ApprovalRequest
from apps.authentication.models import User, TermsApprovalSession
from apps.authentication.webauthn_service import webauthn_service
from apps.authentication.approvals_api_serializers import TermsTokenRequestSerializer


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

@login_required
def dashboard(request):
    """Main dashboard view"""
    
    # Check if user has a tenant
    if not hasattr(request.user, 'tenant') or request.user.tenant is None:
        # User doesn't have a tenant yet, redirect to billing
        from django.shortcuts import redirect
        return redirect('/billing/')
    
    # Get user's tenant requests
    requests_qs = ApprovalRequest.objects.filter(tenant=request.user.tenant)
    
    # Filter by role: only admins and approvers can see all requests
    if request.user.role not in ['admin', 'approver']:
        requests_qs = requests_qs.filter(requester=request.user)
    
    # Basic stats
    stats = {
        'total_requests': requests_qs.count(),
        'pending_requests': requests_qs.filter(status='pending').count(),
        'approved_requests': requests_qs.filter(status='approved').count(),
        'rejected_requests': requests_qs.filter(status='rejected').count(),
        'cancelled_requests': requests_qs.filter(status='cancelled').count(),
        'my_requests': requests_qs.filter(requester=request.user).count(),
    }
    
    # Recent requests (last 10)
    recent_requests = requests_qs.select_related(
        'requester', 'approver'
    ).order_by('-created_at')[:10]
    
    # Category breakdown with translated labels
    category_counts = requests_qs.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Map category codes to translated display names
    category_display_map = dict(ApprovalRequest.CATEGORY_CHOICES)
    category_stats = [
        {
            'category': str(category_display_map.get(item['category'], item['category'])),
            'count': item['count']
        }
        for item in category_counts
    ]
    
    # Priority breakdown with translated labels
    priority_counts = requests_qs.values('priority').annotate(
        count=Count('id')
    ).order_by('-count')
    
    priority_display_map = dict(ApprovalRequest.PRIORITY_CHOICES)
    priority_stats = [
        {
            'priority': str(priority_display_map.get(item['priority'], item['priority'])),
            'count': item['count']
        }
        for item in priority_counts
    ]
    
    # Requests by status over time (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_stats = []
    
    for i in range(30):
        date = thirty_days_ago + timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        day_requests = requests_qs.filter(
            created_at__gte=date_start,
            created_at__lt=date_end
        )
        
        daily_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'total': day_requests.count(),
            'pending': day_requests.filter(status='pending').count(),
            'approved': day_requests.filter(status='approved').count(),
            'rejected': day_requests.filter(status='rejected').count(),
            'cancelled': day_requests.filter(status='cancelled').count(),
        })
    
    # Pending requests requiring user's attention (if approver)
    pending_for_approval = []
    if request.user.role in ['admin', 'approver']:
        pending_for_approval = requests_qs.filter(
            status='pending'
        ).exclude(
            requester=request.user
        ).select_related('requester').order_by('-created_at')[:50]
    
    context = {
        'stats': stats,
        'recent_requests': recent_requests,
        'category_stats': category_stats,
        'priority_stats': priority_stats,
        'daily_stats': daily_stats,
        'pending_for_approval': pending_for_approval,
        'user_can_approve': request.user.role in ['admin', 'approver'],
    }
    
    return render(request, 'dashboard/index.html', context)


@login_required
def iframe_integration_guide(request):
    """Professional integration guide for SecureApprove iframe embed."""

    if not hasattr(request.user, 'tenant') or request.user.tenant is None:
        from django.shortcuts import redirect
        return redirect('/billing/')

    # Integration setup must be managed by tenant admins/super admins.
    if not request.user.can_admin_tenant():
        from django.shortcuts import redirect
        return redirect('requests:dashboard')

    app_origin = f"{request.scheme}://{request.get_host()}"
    embed_url = f"{app_origin}/{request.LANGUAGE_CODE}/embed/secureapprove/"
    token_endpoint = f"{app_origin}/api/approvals/terms/token/"
    loader_url = f"{app_origin}/static/js/secureapprove-embed-loader.js"
    backend_session_endpoint = f"/{request.LANGUAGE_CODE}/dashboard/api/integrations/iframe/session/"

    context = {
        'app_origin': app_origin,
        'embed_url': embed_url,
        'loader_url': loader_url,
        'token_endpoint': token_endpoint,
        'backend_session_endpoint': backend_session_endpoint,
        'tenant_key': getattr(request.user.tenant, 'key', ''),
        'tenant_name': getattr(request.user.tenant, 'name', ''),
        'actor_email': request.user.email,
    }
    return render(request, 'integrations/iframe_setup.html', context)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def iframe_integration_session_api(request):
    """Internal bootstrap endpoint to issue ephemeral iframe session data for integrations."""

    if not getattr(request.user, 'tenant_id', None):
        return Response({'detail': 'Authenticated user has no tenant.'}, status=400)

    if not request.user.can_admin_tenant():
        return Response({'detail': 'Insufficient permissions.'}, status=403)

    subject_user_id = request.data.get('subjectUserId')
    if not subject_user_id:
        return Response({'detail': 'subjectUserId is required.'}, status=400)

    decision = request.data.get('decision', 'approve')
    decision = 'reject' if decision == 'reject' else 'approve'
    approved = decision == 'approve'

    approval_type = request.data.get('approvalType', 'document')
    document_version = request.data.get('documentVersion', '')
    document_hash = request.data.get('documentHash', '')

    subject_user = get_object_or_404(User, pk=subject_user_id)

    if subject_user.tenant_id != request.user.tenant_id:
        return Response({'detail': 'User does not belong to your tenant.'}, status=403)

    if not subject_user.has_webauthn_credentials:
        return Response({'detail': 'User has no WebAuthn credentials.'}, status=400)

    payload = {
        'user_id': int(subject_user_id),
        'purpose': f'external_{approval_type}_{decision}',
        'document_type': approval_type,
        'document_version': document_version,
        'document_hash': document_hash,
        'context': {
            'tenant': {
                'key': getattr(request.user.tenant, 'key', ''),
                'name': getattr(request.user.tenant, 'name', ''),
                'external_id': request.data.get('tenantExternalId', ''),
            },
            'actor_user': {
                'id': str(request.user.id),
                'email': request.user.email,
                'name': request.user.get_full_name(),
            },
            'subject_user': {
                'id': str(subject_user.id),
                'email': subject_user.email,
                'name': subject_user.get_full_name(),
            },
            'approval': {
                'type': approval_type,
                'decision': decision,
                'approved': approved,
                'reference_id': request.data.get('referenceId', ''),
                'amount': request.data.get('amount'),
                'currency': request.data.get('currency', ''),
                'notes': request.data.get('notes', ''),
                'source': 'dashboard_iframe_integration_module',
                'requested_at': timezone.now().isoformat(),
            },
        },
    }

    serializer = TermsTokenRequestSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    raw_token = secrets.token_urlsafe(48)
    token_hash = _sha256_hex(raw_token)
    expires_at = timezone.now() + timedelta(seconds=120)
    session_id = uuid.uuid4()

    session = TermsApprovalSession(
        id=session_id,
        tenant=request.user.tenant,
        subject_user=subject_user,
        created_by=request.user,
        purpose=data['purpose'],
        document_type=data['document_type'],
        document_version=data['document_version'],
        document_hash=data['document_hash'],
        context_data=data.get('context', {}) or {},
        approval_id=f"terms_{session_id}",
        token_hash=token_hash,
        expires_at=expires_at,
    )

    context_data = {
        'purpose': data['purpose'],
        'document_type': data['document_type'],
        'document_version': data['document_version'],
        'document_hash': data['document_hash'],
        'subject_user_id': str(subject_user.id),
        'tenant_id': str(request.user.tenant_id),
    }
    extra = session.context_data or {}
    if isinstance(extra, dict) and extra:
        context_data['extra'] = extra

    session.save()

    options = webauthn_service.generate_approval_challenge(
        user=subject_user,
        approval_id=session.approval_id,
        context_data=context_data,
    )

    session.challenge_id = options.get('challengeId', '')
    session.save(update_fields=['challenge_id'])

    return Response(
        {
            'approvalToken': raw_token,
            'webauthnOptions': options,
            'approved': approved,
            'context': payload['context'],
            'expiresAt': session.expires_at.isoformat(),
        },
        status=201,
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_api_stats(request):
    """API endpoint for dashboard statistics"""
    
    requests_qs = ApprovalRequest.objects.filter(tenant=request.user.tenant)
    
    # Filter by role: only admins and approvers can see all requests
    if request.user.role not in ['admin', 'approver']:
        requests_qs = requests_qs.filter(requester=request.user)
    
    # Basic stats
    stats = {
        'total': requests_qs.count(),
        'pending': requests_qs.filter(status='pending').count(),
        'approved': requests_qs.filter(status='approved').count(),
        'rejected': requests_qs.filter(status='rejected').count(),
        'cancelled': requests_qs.filter(status='cancelled').count(),
        'my_requests': requests_qs.filter(requester=request.user).count(),
    }
    
    # Category breakdown
    category_stats = {}
    for category_code, category_name in ApprovalRequest.CATEGORY_CHOICES:
        category_stats[category_code] = {
            'label': str(category_name),
            'count': requests_qs.filter(category=category_code).count()
        }
    
    # Priority breakdown
    priority_stats = {}
    for priority_code, priority_name in ApprovalRequest.PRIORITY_CHOICES:
        priority_stats[priority_code] = {
            'label': str(priority_name),
            'count': requests_qs.filter(priority=priority_code).count()
        }
    
    # Recent activity (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    recent_activity = []
    
    for i in range(7):
        date = seven_days_ago + timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)
        
        day_requests = requests_qs.filter(
            created_at__gte=date_start,
            created_at__lt=date_end
        )
        
        recent_activity.append({
            'date': date.strftime('%Y-%m-%d'),
            'day_name': date.strftime('%A'),
            'total': day_requests.count(),
            'pending': day_requests.filter(status='pending').count(),
            'approved': day_requests.filter(status='approved').count(),
            'rejected': day_requests.filter(status='rejected').count(),
            'cancelled': day_requests.filter(status='cancelled').count(),
        })
    
    # Approval metrics (if user is approver)
    approval_metrics = {}
    if request.user.role in ['admin', 'approver']:
        pending_count = requests_qs.filter(
            status='pending'
        ).exclude(requester=request.user).count()
        
        approved_by_user = requests_qs.filter(
            approver=request.user,
            status='approved'
        ).count()
        
        rejected_by_user = requests_qs.filter(
            approver=request.user,
            status='rejected'
        ).count()
        
        approval_metrics = {
            'pending_for_me': pending_count,
            'approved_by_me': approved_by_user,
            'rejected_by_me': rejected_by_user,
            'total_decisions': approved_by_user + rejected_by_user,
        }
    
    # Amount metrics
    amount_metrics = {
        'total_amount': float(requests_qs.filter(
            amount__isnull=False
        ).aggregate(
            total=Count('amount')
        )['total'] or 0),
        'approved_amount': float(requests_qs.filter(
            status='approved',
            amount__isnull=False
        ).aggregate(
            total=Count('amount')
        )['total'] or 0),
        'pending_amount': float(requests_qs.filter(
            status='pending',
            amount__isnull=False
        ).aggregate(
            total=Count('amount')
        )['total'] or 0),
    }
    
    return Response({
        'basic_stats': stats,
        'category_breakdown': category_stats,
        'priority_breakdown': priority_stats,
        'recent_activity': recent_activity,
        'approval_metrics': approval_metrics,
        'amount_metrics': amount_metrics,
        'user_role': request.user.role,
        'tenant_name': request.user.tenant.name if request.user.tenant else None,
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pending_approvals_api(request):
    """API endpoint for pending approvals for current user"""
    
    if request.user.role not in ['admin', 'approver']:
        return Response({
            'error': 'Permission denied',
            'message': 'Only admins and approvers can view pending approvals'
        }, status=403)
    
    pending_requests = ApprovalRequest.objects.filter(
        tenant=request.user.tenant,
        status='pending'
    ).exclude(
        requester=request.user
    ).select_related('requester').order_by('-created_at')
    
    # Serialize the data
    pending_data = []
    for req in pending_requests:
        pending_data.append({
            'id': req.id,
            'title': req.title,
            'description': req.description[:100] + '...' if len(req.description) > 100 else req.description,
            'category': req.category,
            'category_display': req.get_category_display(),
            'priority': req.priority,
            'priority_display': req.get_priority_display(),
            'amount': float(req.amount) if req.amount else None,
            'requester': {
                'id': req.requester.id,
                'name': f"{req.requester.first_name} {req.requester.last_name}",
                'email': req.requester.email,
            },
            'created_at': req.created_at.isoformat(),
            'metadata': req.metadata,
        })
    
    return Response({
        'pending_requests': pending_data,
        'total_count': len(pending_data),
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_requests_summary_api(request):
    """API endpoint for current user's requests summary"""
    
    my_requests = ApprovalRequest.objects.filter(
        requester=request.user,
        tenant=request.user.tenant
    )
    
    summary = {
        'total': my_requests.count(),
        'pending': my_requests.filter(status='pending').count(),
        'approved': my_requests.filter(status='approved').count(),
        'rejected': my_requests.filter(status='rejected').count(),
    }
    
    # Recent requests
    recent = my_requests.select_related('approver').order_by('-created_at')[:5]
    recent_data = []
    
    for req in recent:
        recent_data.append({
            'id': req.id,
            'title': req.title,
            'category': req.category,
            'category_display': req.get_category_display(),
            'status': req.status,
            'status_display': req.get_status_display(),
            'amount': float(req.amount) if req.amount else None,
            'created_at': req.created_at.isoformat(),
            'approved_at': req.approved_at.isoformat() if req.approved_at else None,
            'approved_by': f"{req.approver.first_name} {req.approver.last_name}" if req.approver else None,
        })
    
    return Response({
        'summary': summary,
        'recent_requests': recent_data,
    })
