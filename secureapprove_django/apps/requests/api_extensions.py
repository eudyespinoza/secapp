# ==================================================
# SecureApprove Django - Enhanced API Documentation
# ==================================================

from django.urls import path
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import ApprovalRequest
from .serializers import ApprovalRequestSerializer, ApprovalRequestCreateSerializer

# API Documentation Schemas
dashboard_stats_response = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'basic_stats': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                'pending': openapi.Schema(type=openapi.TYPE_INTEGER),
                'approved': openapi.Schema(type=openapi.TYPE_INTEGER),
                'rejected': openapi.Schema(type=openapi.TYPE_INTEGER),
                'my_requests': openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        ),
        'category_breakdown': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            additional_properties=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'label': openapi.Schema(type=openapi.TYPE_STRING),
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        ),
        'priority_breakdown': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            additional_properties=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'label': openapi.Schema(type=openapi.TYPE_STRING),
                    'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        ),
        'recent_activity': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                    'day_name': openapi.Schema(type=openapi.TYPE_STRING),
                    'total': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'pending': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'approved': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'rejected': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        ),
        'approval_metrics': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'pending_for_me': openapi.Schema(type=openapi.TYPE_INTEGER),
                'approved_by_me': openapi.Schema(type=openapi.TYPE_INTEGER),
                'rejected_by_me': openapi.Schema(type=openapi.TYPE_INTEGER),
                'total_decisions': openapi.Schema(type=openapi.TYPE_INTEGER),
            }
        ),
        'amount_metrics': openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'total_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                'approved_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                'pending_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
            }
        ),
        'user_role': openapi.Schema(type=openapi.TYPE_STRING),
        'tenant_name': openapi.Schema(type=openapi.TYPE_STRING),
    }
)

bulk_action_request = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        'request_ids': openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(type=openapi.TYPE_INTEGER),
            description='List of request IDs to perform action on'
        ),
        'action': openapi.Schema(
            type=openapi.TYPE_STRING,
            enum=['approve', 'reject'],
            description='Action to perform on selected requests'
        ),
        'reason': openapi.Schema(
            type=openapi.TYPE_STRING,
            description='Reason for rejection (required if action is reject)'
        ),
    },
    required=['request_ids', 'action']
)

class BulkActionSerializer(serializers.Serializer):
    """Serializer for bulk actions"""
    request_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=50,
        help_text="List of request IDs (max 50)"
    )
    action = serializers.ChoiceField(
        choices=['approve', 'reject'],
        help_text="Action to perform"
    )
    reason = serializers.CharField(
        required=False,
        max_length=500,
        help_text="Reason for rejection (required if action is 'reject')"
    )
    
    def validate(self, data):
        if data['action'] == 'reject' and not data.get('reason'):
            raise serializers.ValidationError({
                'reason': 'Reason is required when rejecting requests.'
            })
        return data

@swagger_auto_schema(
    method='post',
    request_body=BulkActionSerializer,
    responses={
        200: openapi.Response(
            description='Bulk action completed successfully',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'processed': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'failed': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'results': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'error': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    )
                }
            )
        ),
        400: 'Bad Request',
        403: 'Permission Denied'
    },
    operation_description='Perform bulk approve/reject on multiple requests',
    tags=['Requests']
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_action_requests(request):
    """Bulk approve or reject multiple requests"""
    
    # Check permissions
    if request.user.role not in ['admin', 'approver']:
        return Response({
            'error': 'Permission denied',
            'message': 'Only admins and approvers can perform bulk actions'
        }, status=status.HTTP_403_FORBIDDEN)
    
    serializer = BulkActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'error': 'Invalid data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    data = serializer.validated_data
    request_ids = data['request_ids']
    action = data['action']
    reason = data.get('reason')
    
    # Get requests to process
    requests_qs = ApprovalRequest.objects.filter(
        id__in=request_ids,
        tenant=request.user.tenant,
        status='pending'
    ).exclude(requester=request.user)
    
    # Process each request
    results = []
    processed = 0
    failed = 0
    
    for approval_request in requests_qs:
        try:
            if action == 'approve':
                approval_request.approve(request.user)
                results.append({
                    'id': approval_request.id,
                    'success': True,
                    'message': 'Approved successfully'
                })
            elif action == 'reject':
                approval_request.reject(request.user, reason)
                results.append({
                    'id': approval_request.id,
                    'success': True,
                    'message': 'Rejected successfully'
                })
            processed += 1
        except Exception as e:
            results.append({
                'id': approval_request.id,
                'success': False,
                'error': str(e)
            })
            failed += 1
    
    return Response({
        'success': True,
        'action': action,
        'processed': processed,
        'failed': failed,
        'total_requested': len(request_ids),
        'results': results
    })

@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            description='Export data',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'filename': openapi.Schema(type=openapi.TYPE_STRING),
                    'format': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'total_records': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        )
    },
    manual_parameters=[
        openapi.Parameter(
            'format',
            openapi.IN_QUERY,
            description="Export format",
            type=openapi.TYPE_STRING,
            enum=['json', 'csv'],
            default='json'
        ),
        openapi.Parameter(
            'status',
            openapi.IN_QUERY,
            description="Filter by status",
            type=openapi.TYPE_STRING,
            enum=['pending', 'approved', 'rejected']
        ),
        openapi.Parameter(
            'category',
            openapi.IN_QUERY,
            description="Filter by category",
            type=openapi.TYPE_STRING,
            enum=['expense', 'purchase', 'travel', 'contract', 'document', 'other']
        ),
        openapi.Parameter(
            'date_from',
            openapi.IN_QUERY,
            description="Filter from date (YYYY-MM-DD)",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_DATE
        ),
        openapi.Parameter(
            'date_to',
            openapi.IN_QUERY,
            description="Filter to date (YYYY-MM-DD)",
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_DATE
        ),
    ],
    operation_description='Export requests data in JSON or CSV format',
    tags=['Requests']
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_requests(request):
    """Export requests data"""
    
    # Get query parameters
    export_format = request.GET.get('format', 'json')
    status_filter = request.GET.get('status')
    category_filter = request.GET.get('category')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Build queryset
    requests_qs = ApprovalRequest.objects.filter(
        tenant=request.user.tenant
    ).select_related('requester', 'approver')
    
    # Filter by role: only admins and approvers can see all requests
    if request.user.role not in ['admin', 'approver']:
        requests_qs = requests_qs.filter(requester=request.user)
    
    # Apply filters
    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)
    
    if category_filter:
        requests_qs = requests_qs.filter(category=category_filter)
    
    if date_from:
        from datetime import datetime
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
        requests_qs = requests_qs.filter(created_at__date__gte=date_from_obj)
    
    if date_to:
        from datetime import datetime
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
        requests_qs = requests_qs.filter(created_at__date__lte=date_to_obj)
    
    # Serialize data
    serializer = ApprovalRequestSerializer(requests_qs, many=True)
    
    # Generate filename
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'requests_export_{timestamp}.{export_format}'
    
    if export_format == 'csv':
        # Convert to CSV format
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        headers = [
            'ID', 'Title', 'Description', 'Category', 'Priority', 'Amount',
            'Status', 'Requester', 'Approved By', 'Created At', 'Approved At'
        ]
        writer.writerow(headers)
        
        # Write data
        for item in serializer.data:
            writer.writerow([
                item['id'],
                item['title'],
                item['description'],
                item['category_display'],
                item['priority_display'],
                item['amount'] or '',
                item['status_display'],
                item['requester_name'],
                item['approved_by_name'] or '',
                item['created_at_formatted'],
                item['approved_at_formatted'] or '',
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        return Response({
            'filename': filename,
            'format': 'csv',
            'content': csv_content,
            'total_records': len(serializer.data)
        })
    
    else:  # JSON format
        return Response({
            'filename': filename,
            'format': 'json',
            'data': serializer.data,
            'total_records': len(serializer.data)
        })

# Add these to the URLs
additional_api_urls = [
    path('bulk-action/', bulk_action_requests, name='bulk-action'),
    path('export/', export_requests, name='export'),
]