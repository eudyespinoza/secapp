# ==================================================
# SecureApprove Django - User Model
# ==================================================

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

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
    webauthn_credentials = models.JSONField(
        _('WebAuthn Credentials'),
        default=list,
        blank=True,
        help_text=_('Stored WebAuthn credentials for biometric authentication')
    )
    
    # Additional fields
    is_active = models.BooleanField(_('Active'), default=True)
    last_login_at = models.DateTimeField(_('Last Login'), null=True, blank=True)
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
        return len(self.webauthn_credentials) > 0
    
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
        self.webauthn_credentials.append(credential_data)
        self.save(update_fields=['webauthn_credentials'])
    
    def get_webauthn_credential(self, credential_id):
        """Get a specific WebAuthn credential by ID"""
        for cred in self.webauthn_credentials:
            if cred.get('credential_id') == credential_id:
                return cred
        return None
    
    def remove_webauthn_credential(self, credential_id):
        """Remove a WebAuthn credential"""
        self.webauthn_credentials = [
            cred for cred in self.webauthn_credentials 
            if cred.get('credential_id') != credential_id
        ]
        self.save(update_fields=['webauthn_credentials'])
    
    def is_passwordless_only(self):
        """Check if user only uses passwordless authentication"""
        # User is passwordless-only if they have WebAuthn credentials
        # and no usable password set
        return self.has_webauthn_credentials and not self.has_usable_password()
