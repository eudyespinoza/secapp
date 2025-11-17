# ==================================================
# SecureApprove Django - Request Views
# ==================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.translation import gettext as _, gettext_lazy
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import ApprovalRequest
from .forms import DynamicRequestForm
from .serializers import ApprovalRequestSerializer

# ==================================================
# Web Views (Django Templates)
# ==================================================

@login_required
def request_list(request):
    """List all requests for the current user"""
    
    # Get user's requests
    requests_qs = ApprovalRequest.objects.filter(
        tenant=request.user.tenant
    ).select_related('requester', 'approver').order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    search_query = request.GET.get('q')
    
    if status_filter and status_filter != 'all':
        requests_qs = requests_qs.filter(status=status_filter)
    
    if category_filter and category_filter != 'all':
        requests_qs = requests_qs.filter(category=category_filter)
    
    if search_query:
        requests_qs = requests_qs.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(requests_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'search_query': search_query,
        'categories': ApprovalRequest.CATEGORY_CHOICES,
        'statuses': ApprovalRequest.STATUS_CHOICES,
    }
    
    return render(request, 'requests/list.html', context)

@login_required
def create_request(request):
    """Create a new approval request"""
    
    if request.method == 'POST':
        form = DynamicRequestForm(request.POST, user=request.user)
        if form.is_valid():
            approval_request = form.save()
            messages.success(
                request, 
                _('Your request "{}" has been submitted successfully.').format(approval_request.title)
            )
            return redirect('requests:detail', pk=approval_request.pk)
    else:
        form = DynamicRequestForm(user=request.user)
    
    context = {
        'form': form,
        'page_title': _('New Request'),
    }
    
    return render(request, 'requests/create.html', context)

@login_required
def request_detail(request, pk):
    """View request details"""
    
    approval_request = get_object_or_404(
        ApprovalRequest, 
        pk=pk, 
        tenant=request.user.tenant
    )
    
    # Check if user can approve this request
    can_approve = (
        request.user.role in ['admin', 'approver'] and 
        approval_request.status == 'pending' and
        approval_request.requester != request.user
    )
    
    context = {
        'request_obj': approval_request,
        'can_approve': can_approve,
    }
    
    return render(request, 'requests/detail.html', context)

@login_required
@require_http_methods(["POST"])
def approve_request(request, pk):
    """Approve a request"""
    
    approval_request = get_object_or_404(
        ApprovalRequest, 
        pk=pk, 
        tenant=request.user.tenant
    )
    
    # Check permissions
    if request.user.role not in ['admin', 'approver']:
        messages.error(request, _('You do not have permission to approve requests.'))
        return redirect('requests:detail', pk=pk)
    
    if approval_request.status != 'pending':
        messages.error(request, _('This request has already been processed.'))
        return redirect('requests:detail', pk=pk)
    
    if approval_request.requester == request.user:
        messages.error(request, _('You cannot approve your own request.'))
        return redirect('requests:detail', pk=pk)

    # Require recent WebAuthn verification on this device
    from django.utils import timezone
    last_webauthn_at = request.session.get('last_webauthn_at')
    is_recent = False
    if last_webauthn_at:
        try:
            last_dt = timezone.datetime.fromisoformat(last_webauthn_at)
            if timezone.is_naive(last_dt):
                last_dt = timezone.make_aware(last_dt, timezone.utc)
            # Consider valid if within last 2 minutes
            is_recent = (timezone.now() - last_dt).total_seconds() <= 120
        except Exception:
            is_recent = False
    if not is_recent:
        messages.error(
            request,
            _('For security reasons, you must confirm with your biometric on this device before approving. Please try again.'),
        )
        return redirect('requests:detail', pk=pk)
    
    # Approve the request
    approval_request.approve(request.user)
    
    messages.success(
        request, 
        _('Request "{}" has been approved.').format(approval_request.title)
    )
    
    return redirect('requests:detail', pk=pk)

@login_required
@require_http_methods(["POST"])
def reject_request(request, pk):
    """Reject a request"""
    
    approval_request = get_object_or_404(
        ApprovalRequest, 
        pk=pk, 
        tenant=request.user.tenant
    )
    
    # Check permissions
    if request.user.role not in ['admin', 'approver']:
        messages.error(request, _('You do not have permission to reject requests.'))
        return redirect('requests:detail', pk=pk)
    
    if approval_request.status != 'pending':
        messages.error(request, _('This request has already been processed.'))
        return redirect('requests:detail', pk=pk)
    
    if approval_request.requester == request.user:
        messages.error(request, _('You cannot reject your own request.'))
        return redirect('requests:detail', pk=pk)

    # Require recent WebAuthn verification on this device
    from django.utils import timezone
    last_webauthn_at = request.session.get('last_webauthn_at')
    is_recent = False
    if last_webauthn_at:
        try:
            last_dt = timezone.datetime.fromisoformat(last_webauthn_at)
            if timezone.is_naive(last_dt):
                last_dt = timezone.make_aware(last_dt, timezone.utc)
            is_recent = (timezone.now() - last_dt).total_seconds() <= 120
        except Exception:
            is_recent = False
    if not is_recent:
        messages.error(
            request,
            _('For security reasons, you must confirm with your biometric on this device before rejecting. Please try again.'),
        )
        return redirect('requests:detail', pk=pk)
    
    # Get rejection reason
    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, _('Please provide a reason for rejection.'))
        return redirect('requests:detail', pk=pk)
    
    # Reject the request
    approval_request.reject(request.user, reason)
    
    messages.success(
        request, 
        _('Request "{}" has been rejected.').format(approval_request.title)
    )
    
    return redirect('requests:detail', pk=pk)

@login_required
def get_category_fields(request):
    """AJAX endpoint to get dynamic fields for a category"""
    
    category = request.GET.get('category')
    if not category:
        return JsonResponse({'error': 'Category required'}, status=400)
    
    # Create a temporary form to get field configuration
    form = DynamicRequestForm(user=request.user)
    config = form._get_category_config(category)
    
    return JsonResponse({
        'show_amount': config['show_amount'],
        'required_fields': config['required_fields'],
        'extra_fields': config.get('extra_fields', [])
    })

# ==================================================
# API Views (Django REST Framework)
# ==================================================

class ApprovalRequestViewSet(viewsets.ModelViewSet):
    """API ViewSet for ApprovalRequest"""
    
    serializer_class = ApprovalRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter requests by user's tenant"""
        return ApprovalRequest.objects.filter(
            tenant=self.request.user.tenant
        ).select_related('requester', 'approver')
    
    def perform_create(self, serializer):
        """Set requester and tenant when creating"""
        serializer.save(
            requester=self.request.user,
            tenant=self.request.user.tenant
        )
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a request via API"""
        
        approval_request = self.get_object()
        
        # Check permissions
        if request.user.role not in ['admin', 'approver']:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if approval_request.status != 'pending':
            return Response(
                {'error': 'Request already processed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if approval_request.requester == request.user:
            return Response(
                {'error': 'Cannot approve own request'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Approve the request
        approval_request.approve(request.user)
        
        serializer = self.get_serializer(approval_request)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a request via API"""
        
        approval_request = self.get_object()
        
        # Check permissions
        if request.user.role not in ['admin', 'approver']:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if approval_request.status != 'pending':
            return Response(
                {'error': 'Request already processed'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if approval_request.requester == request.user:
            return Response(
                {'error': 'Cannot reject own request'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get rejection reason
        reason = request.data.get('reason', '').strip()
        if not reason:
            return Response(
                {'error': 'Rejection reason required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reject the request
        approval_request.reject(request.user, reason)
        
        serializer = self.get_serializer(approval_request)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics"""
        
        qs = self.get_queryset()
        
        stats = {
            'total': qs.count(),
            'pending': qs.filter(status='pending').count(),
            'approved': qs.filter(status='approved').count(),
            'rejected': qs.filter(status='rejected').count(),
            'my_requests': qs.filter(requester=request.user).count(),
        }
        
        # Add category breakdown
        category_stats = {}
        for category_code, category_name in ApprovalRequest.CATEGORY_CHOICES:
            category_stats[category_code] = qs.filter(category=category_code).count()
        
        stats['by_category'] = category_stats
        
        return Response(stats)
