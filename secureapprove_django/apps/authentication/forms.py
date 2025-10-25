# ==================================================
# SecureApprove Django - Authentication Forms
# ==================================================

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Field, HTML, Div
from crispy_forms.bootstrap import FormActions

from .models import User


# ================================================
# User Registration Form
# ================================================

class CustomUserCreationForm(UserCreationForm):
    """Enhanced user creation form with Bootstrap styling"""
    
    email = forms.EmailField(
        required=True,
        help_text=_('Required. Enter a valid email address.')
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        help_text=_('Required.')
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        help_text=_('Required.')
    )
    terms_accepted = forms.BooleanField(
        required=True,
        label=_('I accept the Terms of Service and Privacy Policy')
    )
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Update field attributes
        self.fields['email'].widget.attrs.update({
            'placeholder': _('Enter your email address'),
            'autocomplete': 'email'
        })
        self.fields['first_name'].widget.attrs.update({
            'placeholder': _('Enter your first name'),
            'autocomplete': 'given-name'
        })
        self.fields['last_name'].widget.attrs.update({
            'placeholder': _('Enter your last name'),
            'autocomplete': 'family-name'
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': _('Create a strong password'),
            'autocomplete': 'new-password'
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': _('Confirm your password'),
            'autocomplete': 'new-password'
        })
        
        # Crispy Forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Field('first_name', css_class='form-control-lg'),
                Field('last_name', css_class='form-control-lg'),
                css_class='row'
            ),
            Field('email', css_class='form-control-lg'),
            Field('password1', css_class='form-control-lg'),
            Field('password2', css_class='form-control-lg'),
            Field('terms_accepted'),
            FormActions(
                Submit('submit', _('Create Account'), css_class='btn-primary btn-lg w-100')
            )
        )
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


# ================================================
# User Login Form
# ================================================

class CustomAuthenticationForm(AuthenticationForm):
    """Enhanced authentication form with Bootstrap styling and WebAuthn support"""
    
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        label=_('Remember me for 30 days')
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Update field attributes
        self.fields['username'].widget.attrs.update({
            'placeholder': _('Enter your email address'),
            'autocomplete': 'email',
            'autofocus': True
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': _('Enter your password'),
            'autocomplete': 'current-password'
        })
        
        # Update labels
        self.fields['username'].label = _('Email Address')
        self.fields['password'].label = _('Password')
        
        # Crispy Forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('username', css_class='form-control-lg'),
            Field('password', css_class='form-control-lg'),
            Field('remember_me'),
            HTML('''
                <div class="d-grid gap-2 mb-3">
                    <button type="submit" class="btn btn-primary btn-lg">
                        <i class="bi bi-box-arrow-in-right me-2"></i>
                        {% trans "Sign In" %}
                    </button>
                </div>
                <div class="text-center mb-3">
                    <div class="text-muted">{% trans "or" %}</div>
                </div>
                <div class="d-grid gap-2 mb-3">
                    <button type="button" id="webauthn-login" class="btn btn-outline-primary btn-lg">
                        <i class="bi bi-fingerprint me-2"></i>
                        {% trans "Sign in with WebAuthn" %}
                    </button>
                </div>
            '''),
        )


# ================================================
# Profile Update Form
# ================================================

class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile information"""
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'name')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'placeholder': _('Enter your first name'),
                'class': 'form-control'
            }),
            'last_name': forms.TextInput(attrs={
                'placeholder': _('Enter your last name'),
                'class': 'form-control'
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': _('Enter your phone number'),
                'class': 'form-control'
            }),
            'company': forms.TextInput(attrs={
                'placeholder': _('Enter your company name'),
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Crispy Forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Field('first_name'),
                Field('last_name'),
                css_class='row'
            ),
            Field('phone'),
            Field('company'),
            FormActions(
                Submit('submit', _('Update Profile'), css_class='btn-primary')
            )
        )


# ================================================
# Password Change Form
# ================================================

class CustomPasswordChangeForm(forms.Form):
    """Custom password change form"""
    
    current_password = forms.CharField(
        label=_('Current Password'),
        widget=forms.PasswordInput(attrs={
            'placeholder': _('Enter your current password'),
            'class': 'form-control'
        })
    )
    new_password1 = forms.CharField(
        label=_('New Password'),
        widget=forms.PasswordInput(attrs={
            'placeholder': _('Enter your new password'),
            'class': 'form-control'
        })
    )
    new_password2 = forms.CharField(
        label=_('Confirm New Password'),
        widget=forms.PasswordInput(attrs={
            'placeholder': _('Confirm your new password'),
            'class': 'form-control'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        
        # Crispy Forms helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Field('current_password'),
            Field('new_password1'),
            Field('new_password2'),
            FormActions(
                Submit('submit', _('Change Password'), css_class='btn-primary')
            )
        )
    
    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise forms.ValidationError(_('Current password is incorrect.'))
        return current_password
    
    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError(_('The two password fields must match.'))
        
        return cleaned_data
    
    def save(self):
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        self.user.save()
        return self.user