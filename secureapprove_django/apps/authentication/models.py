# ==================================================
# SecureApprove Django - User Model
# ==================================================

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
import json

class User(AbstractUser):
    """
    Custom User model compatible with existing SecureApprove data
    """
    
    ROLE_CHOICES = [
        ('requester', _('Requester')),
        ('approver', _('Approver')),
        ('tenant_admin', _('Tenant Admin')),
        ('superadmin', _('Super Admin')),
    ]
    
    # Basic fields (email already in AbstractUser)
    name = models.CharField(_('Full Name'), max_length=255, blank=True)
    role = models.CharField(_('Role'), max_length=20, choices=ROLE_CHOICES, default='requester')
    
    # Tenant relationship
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    
    # WebAuthn credentials (JSON field to store credentials array)
    # Each credential now has: credential_id, public_key, sign_count, transports,
    # display_name, is_active, created_at, last_used_at
    webauthn_credentials = models.JSONField(
        _('WebAuthn Credentials'),
        default=list,
        blank=True,
        help_text=_('Stored WebAuthn credentials for biometric authentication')
    )
    
    # Additional fields
    is_active = models.BooleanField(_('Active'), default=True)
    last_login_at = models.DateTimeField(_('Last Login'), null=True, blank=True)
    webauthn_last_login_at = models.DateTimeField(_('Last WebAuthn Login'), null=True, blank=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    # Override email to be required and unique
    email = models.EmailField(_('Email Address'), unique=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'name']
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name or self.email} ({self.get_role_display()})"
    
    def get_full_name(self):
        return self.name or self.email
    
    def get_short_name(self):
        return self.name.split(' ')[0] if self.name else self.email.split('@')[0]
    
    @property
    def has_webauthn_credentials(self):
        """Check if user has registered WebAuthn credentials"""
        if not isinstance(self.webauthn_credentials, list):
            return False
        # Only count active credentials
        return any(cred.get('is_active', True) for cred in self.webauthn_credentials)
    
    def can_approve_requests(self):
        """Check if user can approve requests"""
        # Support legacy 'admin' role and Django staff/superuser flags
        return self.role in ['approver', 'tenant_admin', 'superadmin', 'admin'] or self.is_staff or self.is_superuser
    
    def can_admin_tenant(self):
        """Check if user can administrate tenant"""
        # Allow admin roles and Django staff/superusers
        return self.role in ['tenant_admin', 'superadmin', 'admin'] or self.is_staff or self.is_superuser
    
    def add_webauthn_credential(self, credential_data):
        """Add a WebAuthn credential to the user"""
        if not isinstance(self.webauthn_credentials, list):
            self.webauthn_credentials = []
        
        # Ensure credential has required fields
        now = timezone.now().isoformat()
        credential = {
            'credential_id': credential_data.get('credential_id'),
            'credential_public_key': credential_data.get('credential_public_key'),
            'sign_count': credential_data.get('sign_count', 0),
            'transports': credential_data.get('transports', []),
            'display_name': credential_data.get('display_name', f'Device {len(self.webauthn_credentials) + 1}'),
            'is_active': True,
            'created_at': credential_data.get('created_at', now),
            'last_used_at': None,
        }
        
        self.webauthn_credentials.append(credential)
        self.save(update_fields=['webauthn_credentials'])
    
    def get_webauthn_credential(self, credential_id):
        """Get a specific WebAuthn credential by ID"""
        for cred in self.webauthn_credentials:
            if cred.get('credential_id') == credential_id:
                return cred
        return None
    
    def update_credential_last_used(self, credential_id):
        """Update last_used_at timestamp for a credential"""
        for cred in self.webauthn_credentials:
            if cred.get('credential_id') == credential_id:
                cred['last_used_at'] = timezone.now().isoformat()
                self.save(update_fields=['webauthn_credentials'])
                break
    
    def rename_webauthn_credential(self, credential_id, new_name):
        """Rename a WebAuthn credential"""
        for cred in self.webauthn_credentials:
            if cred.get('credential_id') == credential_id:
                cred['display_name'] = new_name
                self.save(update_fields=['webauthn_credentials'])
                return True
        return False
    
    def deactivate_webauthn_credential(self, credential_id):
        """Deactivate (soft delete) a WebAuthn credential"""
        for cred in self.webauthn_credentials:
            if cred.get('credential_id') == credential_id:
                cred['is_active'] = False
                self.save(update_fields=['webauthn_credentials'])
                return True
        return False
    
    def remove_webauthn_credential(self, credential_id):
        """Remove (hard delete) a WebAuthn credential"""
        original_count = len(self.webauthn_credentials)
        self.webauthn_credentials = [
            cred for cred in self.webauthn_credentials 
            if cred.get('credential_id') != credential_id
        ]
        if len(self.webauthn_credentials) < original_count:
            self.save(update_fields=['webauthn_credentials'])
            return True
        return False
    
    def is_passwordless_only(self):
        """Check if user only uses passwordless authentication"""
        # User is passwordless-only if they have WebAuthn credentials
        # and no usable password set
        return self.has_webauthn_credentials and not self.has_usable_password()


class DevicePairingSession(models.Model):
    """
    Temporary pairing session used to link a new device
    (e.g., phone) with an existing user account for WebAuthn.
    """

    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('completed', _('Completed')),
        ('expired', _('Expired')),
        ('cancelled', _('Cancelled')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='device_pairing_sessions',
    )
    token = models.CharField(_('Pairing Token'), max_length=128, unique=True)
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    expires_at = models.DateTimeField(_('Expires At'))
    paired_at = models.DateTimeField(_('Paired At'), null=True, blank=True)
    paired_user_agent = models.TextField(_('Paired User Agent'), blank=True)
    paired_platform = models.CharField(_('Paired Platform'), max_length=255, blank=True)

    class Meta:
        verbose_name = _('Device Pairing Session')
        verbose_name_plural = _('Device Pairing Sessions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"Pairing session {self.id} for {self.user.email} ({self.status})"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class ApprovalAudit(models.Model):
    """
    Audit log for approval actions performed with WebAuthn step-up authentication.
    Records every WebAuthn challenge verification for approval operations.
    """
    
    STATUS_CHOICES = [
        ('success', _('Success')),
        ('failed', _('Failed')),
        ('expired', _('Expired')),
        ('cancelled', _('Cancelled')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Related approval request
    approval_request = models.ForeignKey(
        'requests.ApprovalRequest',
        on_delete=models.CASCADE,
        related_name='webauthn_audits',
        verbose_name=_('Approval Request')
    )
    
    # User who performed the action
    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='approval_audits',
        verbose_name=_('User')
    )
    
    # WebAuthn credential used
    credential_id = models.CharField(
        _('Credential ID'),
        max_length=512,
        help_text=_('Base64-encoded WebAuthn credential ID used for this approval')
    )
    
    # Challenge information
    challenge_id = models.CharField(
        _('Challenge ID'),
        max_length=128,
        help_text=_('Unique identifier for the challenge')
    )
    
    # Action details
    action = models.CharField(
        _('Action'),
        max_length=20,
        choices=[('approve', _('Approve')), ('reject', _('Reject'))],
        help_text=_('Type of approval action')
    )
    
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='success'
    )
    
    # Request metadata
    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)
    
    # Context data (optional, can include approval details hash for cryptographic binding)
    context_data = models.JSONField(
        _('Context Data'),
        default=dict,
        blank=True,
        help_text=_('Additional context: approval amount, type, etc.')
    )
    
    # Timestamps
    performed_at = models.DateTimeField(_('Performed At'), auto_now_add=True)
    
    # Error details (if failed)
    error_message = models.TextField(_('Error Message'), blank=True)
    
    class Meta:
        verbose_name = _('Approval Audit')
        verbose_name_plural = _('Approval Audits')
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['approval_request', 'performed_at']),
            models.Index(fields=['user', 'performed_at']),
            models.Index(fields=['status']),
            models.Index(fields=['credential_id']),
        ]
    
    def __str__(self):
        return f"Audit {self.id}: {self.user.email} - {self.action} - {self.status}"


class TermsApprovalSession(models.Model):
    """Short-lived, one-time token to bind a WebAuthn step-up to a legal acceptance event."""

    PURPOSE_CHOICES = [
        ('terms_acceptance', _('Terms Acceptance')),
        ('generic', _('Generic')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='terms_approval_sessions',
        verbose_name=_('Tenant'),
    )

    subject_user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='terms_approval_sessions',
        verbose_name=_('User'),
    )

    created_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_terms_approval_sessions',
        verbose_name=_('Created By'),
    )

    purpose = models.CharField(
        _('Purpose'),
        max_length=64,
        choices=PURPOSE_CHOICES,
        default='terms_acceptance',
    )

    document_type = models.CharField(_('Document Type'), max_length=32, default='terms')
    document_version = models.CharField(_('Document Version'), max_length=64, blank=True)
    document_hash = models.CharField(_('Document Hash'), max_length=128, blank=True)

    # Context bound to the WebAuthn challenge hash (see WebAuthnService.generate_approval_challenge)
    context_data = models.JSONField(_('Context Data'), default=dict, blank=True)

    # Identifiers used to locate the cached WebAuthn challenge
    approval_id = models.CharField(_('Approval ID'), max_length=128)
    challenge_id = models.CharField(_('Challenge ID'), max_length=128, blank=True)

    # Store only a hash of the token for maximum security
    token_hash = models.CharField(_('Token Hash'), max_length=64, unique=True)

    expires_at = models.DateTimeField(_('Expires At'))
    consumed_at = models.DateTimeField(_('Consumed At'), null=True, blank=True)

    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Terms Approval Session')
        verbose_name_plural = _('Terms Approval Sessions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'subject_user', 'created_at']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['consumed_at']),
        ]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_consumed(self):
        return self.consumed_at is not None


class TermsAcceptanceAudit(models.Model):
    """Audit log for Terms & Conditions acceptance/rejection via WebAuthn step-up."""

    STATUS_CHOICES = [
        ('success', _('Success')),
        ('failed', _('Failed')),
        ('expired', _('Expired')),
        ('cancelled', _('Cancelled')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='terms_acceptance_audits',
        verbose_name=_('Tenant'),
    )

    user = models.ForeignKey(
        'authentication.User',
        on_delete=models.CASCADE,
        related_name='terms_acceptance_audits',
        verbose_name=_('User'),
    )

    initiated_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_terms_acceptance_audits',
        verbose_name=_('Initiated By'),
    )

    session = models.ForeignKey(
        'authentication.TermsApprovalSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audits',
        verbose_name=_('Approval Session'),
    )

    purpose = models.CharField(_('Purpose'), max_length=64, default='terms_acceptance')
    document_type = models.CharField(_('Document Type'), max_length=32, default='terms')
    document_version = models.CharField(_('Document Version'), max_length=64, blank=True)
    document_hash = models.CharField(_('Document Hash'), max_length=128, blank=True)

    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='success')

    credential_id = models.CharField(_('Credential ID'), max_length=512, blank=True)
    challenge_id = models.CharField(_('Challenge ID'), max_length=128, blank=True)

    ip_address = models.GenericIPAddressField(_('IP Address'), null=True, blank=True)
    user_agent = models.TextField(_('User Agent'), blank=True)

    user_snapshot = models.JSONField(
        _('User Snapshot'),
        default=dict,
        blank=True,
        help_text=_('Snapshot of user fields at the time of acceptance'),
    )

    context_data = models.JSONField(_('Context Data'), default=dict, blank=True)
    error_message = models.TextField(_('Error Message'), blank=True)

    performed_at = models.DateTimeField(_('Performed At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Terms Acceptance Audit')
        verbose_name_plural = _('Terms Acceptance Audits')
        ordering = ['-performed_at']
        indexes = [
            models.Index(fields=['tenant', 'performed_at']),
            models.Index(fields=['user', 'performed_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Terms audit {self.id}: {self.user.email} - {self.status}"
