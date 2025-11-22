# ==================================================
# SecureApprove Django - Request Serializers
# ==================================================

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import ApprovalRequest

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Minimal user serializer for embedding"""
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'full_name']

class ApprovalRequestSerializer(serializers.ModelSerializer):
    """Serializer for ApprovalRequest model"""
    
    requester = UserSerializer(read_only=True)
    approver = UserSerializer(read_only=True)
    requester_name = serializers.CharField(source='requester.full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approver.full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    created_at_formatted = serializers.SerializerMethodField()
    approved_at_formatted = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    
    class Meta:
        model = ApprovalRequest
        fields = [
            'id', 'title', 'description', 'category', 'category_display',
            'priority', 'priority_display', 'amount', 'status', 'status_display',
            'requester', 'requester_name', 'approver', 'approved_by_name',
            'metadata', 'rejection_reason', 'created_at', 'created_at_formatted',
            'approved_at', 'approved_at_formatted', 'tenant', 'can_approve'
        ]
        read_only_fields = [
            'id', 'requester', 'approver', 'status', 'approved_at', 
            'rejection_reason', 'created_at', 'tenant', 'can_approve'
        ]
    
    def get_can_approve(self, obj):
        """Check if current user can approve this request"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
            
        return (
            request.user.role in ['admin', 'approver'] and 
            obj.status == 'pending' and
            obj.requester != request.user
        )

    def get_created_at_formatted(self, obj):
        """Format created_at for display"""
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    
    def get_approved_at_formatted(self, obj):
        """Format approved_at for display"""
        if obj.approved_at:
            return obj.approved_at.strftime('%Y-%m-%d %H:%M')
        return None
    
    def validate_amount(self, value):
        """Validate amount based on category"""
        category = self.initial_data.get('category')
        
        # Categories that require amount
        amount_required_categories = ['expense', 'purchase', 'travel']
        
        if category in amount_required_categories:
            if not value or value <= 0:
                raise serializers.ValidationError(
                    _('Amount is required and must be greater than 0 for this category.')
                )
        
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        category = data.get('category')
        metadata = data.get('metadata', {})
        
        # Validate required metadata fields based on category
        required_metadata = self._get_required_metadata(category)
        
        for field in required_metadata:
            if field not in metadata or not metadata[field]:
                raise serializers.ValidationError({
                    'metadata': _(f'{field} is required for {category} requests.')
                })
        
        return data
    
    def _get_required_metadata(self, category):
        """Get required metadata fields for each category"""
        requirements = {
            'expense': ['expense_category', 'receipt_ref'],
            'purchase': ['vendor', 'cost_center'],
            'travel': ['destination', 'start_date', 'end_date'],
            'contract': ['vendor', 'reason'],
            'document': ['document_id', 'reason'],
            'other': []
        }
        return requirements.get(category, [])

class ApprovalRequestCreateSerializer(serializers.ModelSerializer):
    """Specialized serializer for creating requests with dynamic validation"""
    
    # Extra fields for dynamic categories
    vendor = serializers.CharField(required=False, allow_blank=True)
    cost_center = serializers.CharField(required=False, allow_blank=True)
    expense_category = serializers.CharField(required=False, allow_blank=True)
    receipt_ref = serializers.CharField(required=False, allow_blank=True)
    destination = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    document_id = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = ApprovalRequest
        fields = [
            'title', 'description', 'category', 'priority', 'amount',
            'vendor', 'cost_center', 'expense_category', 'receipt_ref',
            'destination', 'start_date', 'end_date', 'document_id', 'reason'
        ]
    
    def validate(self, data):
        """Dynamic validation based on category"""
        category = data.get('category')
        
        if not category:
            raise serializers.ValidationError({
                'category': _('This field is required.')
            })
        
        # Get category configuration
        config = self._get_category_config(category)
        
        # Validate amount field
        if config['show_amount']:
            amount = data.get('amount')
            if not amount or amount <= 0:
                raise serializers.ValidationError({
                    'amount': _('Amount is required and must be greater than 0 for this category.')
                })
        
        # Validate required extra fields
        errors = {}
        for field_name in config.get('extra_fields', []):
            if field_name in config['required_fields']:
                value = data.get(field_name)
                if not value:
                    errors[field_name] = _('This field is required for this category.')
        
        if errors:
            raise serializers.ValidationError(errors)
        
        # Validate date fields for travel
        if category == 'travel':
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            if start_date and end_date and start_date > end_date:
                raise serializers.ValidationError({
                    'end_date': _('End date must be after start date.')
                })
        
        return data
    
    def _get_category_config(self, category):
        """Get configuration for a specific category"""
        configs = {
            'expense': {
                'show_amount': True,
                'required_fields': ['title', 'description', 'amount', 'priority', 'expense_category', 'receipt_ref'],
                'extra_fields': ['expense_category', 'receipt_ref']
            },
            'purchase': {
                'show_amount': True,
                'required_fields': ['title', 'description', 'amount', 'priority', 'vendor', 'cost_center'],
                'extra_fields': ['vendor', 'cost_center']
            },
            'travel': {
                'show_amount': True,
                'required_fields': ['title', 'description', 'amount', 'priority', 'destination', 'start_date', 'end_date'],
                'extra_fields': ['destination', 'start_date', 'end_date']
            },
            'contract': {
                'show_amount': False,
                'required_fields': ['title', 'description', 'priority', 'vendor', 'reason'],
                'extra_fields': ['vendor', 'reason']
            },
            'document': {
                'show_amount': False,
                'required_fields': ['title', 'description', 'priority', 'document_id', 'reason'],
                'extra_fields': ['document_id', 'reason']
            },
            'other': {
                'show_amount': False,
                'required_fields': ['title', 'description', 'priority'],
                'extra_fields': []
            }
        }
        return configs.get(category, configs['other'])
    
    def create(self, validated_data):
        """Create request with metadata from extra fields"""
        
        # Extract extra fields
        extra_fields = [
            'vendor', 'cost_center', 'expense_category', 'receipt_ref',
            'destination', 'start_date', 'end_date', 'document_id', 'reason'
        ]
        
        metadata = {}
        for field in extra_fields:
            if field in validated_data:
                value = validated_data.pop(field)
                if value:
                    # Convert dates to strings for JSON storage
                    if hasattr(value, 'isoformat'):
                        value = value.isoformat()
                    metadata[field] = str(value)
        
        # Create the request
        validated_data['metadata'] = metadata
        return super().create(validated_data)