# ==================================================
# SecureApprove Django - Dashboard Views
# ==================================================

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Q
from django.utils.translation import gettext as _
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import timedelta
from .models import ApprovalRequest

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
