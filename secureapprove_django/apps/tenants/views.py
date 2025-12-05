from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.requests.models import ApprovalRequest
from .models import Tenant, TenantUserInvite, ApprovalTypeConfig
from .utils import ensure_user_tenant

User = get_user_model()


@method_decorator(csrf_exempt, name="dispatch")
class TenantSettingsView(LoginRequiredMixin, View):
    """
    Basic tenant settings page for tenant admins:
      - View tenant info (plan, seats, status)
      - View and adjust users (role, active)
      - View available request categories
    """

    template_name = "tenants/settings.html"

    def get_tenant(self, request):
        tenant = ensure_user_tenant(request.user)
        return tenant

    def get(self, request):
        tenant = self.get_tenant(request)
        if not tenant:
            return redirect("landing:index")

        if not request.user.can_admin_tenant():
            return redirect("landing:index")

        users = tenant.users.all().order_by("-is_active", "email")
        categories = ApprovalRequest.CATEGORY_CHOICES
        invites = TenantUserInvite.objects.filter(tenant=tenant).order_by("-created_at")
        
        # Get or initialize approval type configurations
        approval_configs = ApprovalTypeConfig.objects.filter(tenant=tenant).order_by('sort_order', 'name')
        if not approval_configs.exists():
            ApprovalTypeConfig.initialize_for_tenant(tenant)
            approval_configs = ApprovalTypeConfig.objects.filter(tenant=tenant).order_by('sort_order', 'name')
        
        # Get approvers for assignment
        approvers = tenant.users.filter(
            is_active=True,
            role__in=['approver', 'tenant_admin', 'superadmin']
        ).order_by('email')

        return render(
            request,
            self.template_name,
            {
                "tenant": tenant,
                "users": users,
                "invites": invites,
                "categories": categories,
                "roles": User.ROLE_CHOICES,
                "used_seats": tenant.used_seats,
                "available_seats": tenant.available_seats,
                "approval_configs": approval_configs,
                "approvers": approvers,
            },
        )

    def post(self, request):
        tenant = self.get_tenant(request)
        if not tenant or not request.user.can_admin_tenant():
            return redirect("landing:index")

        action = request.POST.get("action")
        if action == "update_user":
            user_id = request.POST.get("user_id")
            role = (request.POST.get("role") or "").strip()
            is_active = request.POST.get("is_active") == "on"

            try:
                user = tenant.users.get(id=user_id)
            except User.DoesNotExist:
                return redirect("tenants:settings")

            valid_roles = {code for code, _ in User.ROLE_CHOICES}
            if role in valid_roles:
                user.role = role
                user.is_active = is_active
                user.save(update_fields=["role", "is_active"])
                messages.success(request, _("User updated successfully."))
            else:
                messages.error(request, _("Invalid role selected."))

        elif action == "create_invite":
            email = (request.POST.get("email") or "").strip().lower()
            role = request.POST.get("role") or "requester"

            if not email:
                messages.error(request, _("Email is required to invite a user."))
                return redirect("tenants:settings")

            valid_roles = {code for code, _ in User.ROLE_CHOICES}
            if role not in valid_roles:
                role = "requester"

            seats = tenant.seats or 0
            used_seats = tenant.used_seats
            has_subscription = hasattr(tenant, "subscription")
            can_by_subscription = (
                tenant.subscription.can_create_user() if has_subscription else True
            )

            if seats and used_seats >= seats:
                messages.error(
                    request,
                    _(
                        "You have reached the maximum number of users for your current seats. Please upgrade your subscription to add more users."
                    ),
                )
                return redirect("tenants:settings")

            if not can_by_subscription:
                messages.error(
                    request,
                    _(
                        "Your current subscription does not allow adding more users this month."
                    ),
                )
                return redirect("tenants:settings")

            from secrets import token_urlsafe

            invite, created = TenantUserInvite.objects.update_or_create(
                tenant=tenant,
                email=email,
                status="pending",
                defaults={
                    "role": role,
                    "token": token_urlsafe(32),
                    "expires_at": timezone.now() + timezone.timedelta(days=7),
                    "created_by": request.user,
                },
            )

            invite_url = None
            try:
                invite_url = request.build_absolute_uri(
                    reverse("tenants:invite_accept", args=[invite.token])
                )
            except Exception:
                invite_url = None

            if invite_url and getattr(settings, "EMAIL_HOST", None):
                from django.core.mail import send_mail

                subject = _("You have been invited to SecureApprove")
                message = _(
                    "You have been invited to join the tenant '%(tenant)s' on SecureApprove.\n\n"
                    "To accept the invitation and access the platform, please click the following link:\n\n"
                    "%(url)s\n\n"
                    "If you did not expect this invitation, you can ignore this email."
                ) % {"tenant": tenant.name, "url": invite_url}
                try:
                    send_mail(
                        subject,
                        message,
                        getattr(
                            settings,
                            "DEFAULT_FROM_EMAIL",
                            "noreply@secureapprove.com",
                        ),
                        [email],
                        fail_silently=True,
                    )
                except Exception:
                    pass

            if created:
                messages.success(
                    request,
                    _("Invitation created successfully for %(email)s.")
                    % {"email": email},
                )
            else:
                messages.success(
                    request,
                    _("Invitation updated for %(email)s.") % {"email": email},
                )

        elif action == "cancel_invite":
            invite_id = request.POST.get("invite_id")
            if invite_id:
                try:
                    invite = TenantUserInvite.objects.get(id=invite_id, tenant=tenant)
                    invite.status = "cancelled"
                    invite.save(update_fields=["status"])
                    messages.success(
                        request,
                        _("Invitation for %(email)s has been cancelled.")
                        % {"email": invite.email},
                    )
                except TenantUserInvite.DoesNotExist:
                    pass

        # ========================================
        # Approval Type Configuration Actions
        # ========================================
        elif action == "toggle_approval_type":
            config_id = request.POST.get("config_id")
            if config_id:
                try:
                    config = ApprovalTypeConfig.objects.get(id=config_id, tenant=tenant)
                    config.is_enabled = not config.is_enabled
                    config.save(update_fields=["is_enabled"])
                    status = _("enabled") if config.is_enabled else _("disabled")
                    messages.success(
                        request,
                        _("Approval type '%(name)s' has been %(status)s.")
                        % {"name": config.name, "status": status},
                    )
                except ApprovalTypeConfig.DoesNotExist:
                    messages.error(request, _("Approval type not found."))

        elif action == "update_approval_type":
            config_id = request.POST.get("config_id")
            if config_id:
                try:
                    config = ApprovalTypeConfig.objects.get(id=config_id, tenant=tenant)
                    
                    # Update basic fields
                    name = request.POST.get("name", "").strip()
                    if name:
                        config.name = name
                    
                    description = request.POST.get("description", "").strip()
                    config.description = description
                    
                    icon = request.POST.get("icon", "").strip()
                    if icon:
                        config.icon = icon
                    
                    color = request.POST.get("color", "").strip()
                    if color in ['primary', 'success', 'warning', 'danger', 'info', 'secondary', 'dark']:
                        config.color = color
                    
                    # Update approval requirements
                    required_approvers = request.POST.get("required_approvers")
                    if required_approvers:
                        try:
                            config.required_approvers = max(1, int(required_approvers))
                        except ValueError:
                            pass
                    
                    show_amount = request.POST.get("show_amount") == "on"
                    config.show_amount = show_amount
                    
                    config.save()
                    
                    # Update designated approvers
                    approver_ids = request.POST.getlist("designated_approvers")
                    if approver_ids:
                        approvers = tenant.users.filter(
                            id__in=approver_ids,
                            is_active=True,
                            role__in=['approver', 'tenant_admin', 'superadmin']
                        )
                        config.designated_approvers.set(approvers)
                    else:
                        config.designated_approvers.clear()
                    
                    messages.success(
                        request,
                        _("Approval type '%(name)s' has been updated.")
                        % {"name": config.name},
                    )
                except ApprovalTypeConfig.DoesNotExist:
                    messages.error(request, _("Approval type not found."))

        elif action == "create_approval_type":
            name = request.POST.get("name", "").strip()
            category_key = request.POST.get("category_key", "").strip().lower()
            
            if not name or not category_key:
                messages.error(request, _("Name and key are required."))
                return redirect("tenants:settings")
            
            # Sanitize category key
            import re
            category_key = re.sub(r'[^a-z0-9_]', '_', category_key)
            
            # Check if key already exists
            if ApprovalTypeConfig.objects.filter(tenant=tenant, category_key=category_key).exists():
                messages.error(request, _("An approval type with this key already exists."))
                return redirect("tenants:settings")
            
            # Get max sort order
            max_order = ApprovalTypeConfig.objects.filter(tenant=tenant).aggregate(
                max_order=models.Max('sort_order')
            )['max_order'] or 0
            
            # Create new config
            config = ApprovalTypeConfig.objects.create(
                tenant=tenant,
                category_key=category_key,
                name=name,
                description=request.POST.get("description", "").strip(),
                icon=request.POST.get("icon", "bi-file-earmark-check").strip(),
                color=request.POST.get("color", "primary").strip(),
                is_enabled=True,
                is_custom=True,
                required_approvers=max(1, int(request.POST.get("required_approvers", 1))),
                show_amount=request.POST.get("show_amount") == "on",
                sort_order=max_order + 10,
            )
            
            # Set designated approvers if provided
            approver_ids = request.POST.getlist("designated_approvers")
            if approver_ids:
                approvers = tenant.users.filter(
                    id__in=approver_ids,
                    is_active=True,
                    role__in=['approver', 'tenant_admin', 'superadmin']
                )
                config.designated_approvers.set(approvers)
            
            messages.success(
                request,
                _("Approval type '%(name)s' has been created.")
                % {"name": config.name},
            )

        elif action == "delete_approval_type":
            config_id = request.POST.get("config_id")
            if config_id:
                try:
                    config = ApprovalTypeConfig.objects.get(id=config_id, tenant=tenant)
                    if not config.is_custom:
                        messages.error(request, _("Cannot delete default approval types. You can disable them instead."))
                    else:
                        name = config.name
                        config.delete()
                        messages.success(
                            request,
                            _("Approval type '%(name)s' has been deleted.")
                            % {"name": name},
                        )
                except ApprovalTypeConfig.DoesNotExist:
                    messages.error(request, _("Approval type not found."))

        return redirect("tenants:settings")


class TenantInviteAcceptView(View):
    """
    Public invitation acceptance view.

    - Validates invitation token and tenant seats.
    - Creates or updates the associated user.
    - Logs the user in and redirects to dashboard.
    """

    template_name = "tenants/invite_accept.html"

    def _get_valid_invite(self, token):
        invite = get_object_or_404(TenantUserInvite, token=token)
        if invite.status != "pending":
            return None
        if invite.is_expired:
            invite.status = "expired"
            invite.save(update_fields=["status"])
            return None
        return invite

    def get(self, request, token):
        invite = self._get_valid_invite(token)
        if not invite:
            return render(
                request,
                self.template_name,
                {"invalid": True},
            )

        tenant = invite.tenant
        used_seats = tenant.used_seats
        available_seats = tenant.available_seats

        no_seats = available_seats is not None and available_seats <= 0

        return render(
            request,
            self.template_name,
            {
                "invite": invite,
                "tenant": tenant,
                "no_seats": no_seats,
                "used_seats": used_seats,
                "available_seats": available_seats,
            },
        )

    def post(self, request, token):
        invite = self._get_valid_invite(token)
        if not invite:
            messages.error(request, _("This invitation is no longer valid."))
            return redirect("landing:index")

        tenant = invite.tenant

        used_seats = tenant.used_seats
        available_seats = tenant.available_seats
        if available_seats is not None and available_seats <= 0:
            messages.error(
                request,
                _(
                    "This tenant has no available seats. Please contact the administrator."
                ),
            )
            return redirect("landing:index")

        email = invite.email.lower()

        # Create or update user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": email,
                "name": email.split("@")[0],
                "role": invite.role or "requester",
                "tenant": tenant,
                "is_active": True,
            },
        )

        if not created:
            # User exists, validate tenant association
            if user.tenant and user.tenant != tenant:
                messages.error(
                    request,
                    _(
                        "This email is already associated with a different tenant. Please contact support."
                    ),
                )
                return redirect("landing:index")

            # Attach to tenant if not already
            if not user.tenant:
                user.tenant = tenant
            # Update role (do not downgrade superadmin)
            if user.role not in ("superadmin",) and invite.role:
                user.role = invite.role
            user.is_active = True
            user.save(update_fields=["tenant", "role", "is_active"])

        # Mark invite as accepted
        invite.status = "accepted"
        invite.accepted_at = timezone.now()
        invite.save(update_fields=["status", "accepted_at"])

        # Log the user in
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)

        messages.success(
            request,
            _("Welcome! Your invitation has been accepted and your account is ready."),
        )
        return redirect("requests:dashboard")


class SuperAdminTenantView(LoginRequiredMixin, View):
    """
    Super Admin view to manage tenants and invite primary users.
    Restricted to specific superadmin email.
    """
    template_name = "tenants/superadmin.html"

    def dispatch(self, request, *args, **kwargs):
        # Hardcoded security check as requested
        if request.user.email != "eudyespinoza@gmail.com":
             return redirect("landing:index")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        tenants = Tenant.objects.all().order_by("-created_at")
        return render(request, self.template_name, {
            "tenants": tenants,
            "plans": Tenant.PLAN_CHOICES,
            "statuses": Tenant.STATUS_CHOICES,
        })

    def post(self, request):
        action = request.POST.get("action")
        
        if action == "create_tenant":
            name = request.POST.get("name")
            key = request.POST.get("key")
            plan_id = request.POST.get("plan_id")
            status = request.POST.get("status")
            seats = request.POST.get("seats")
            
            if not all([name, key, plan_id, status, seats]):
                messages.error(request, _("All fields are required."))
                return redirect("tenants:superadmin")
                
            if Tenant.objects.filter(key=key).exists():
                messages.error(request, _("Tenant key already exists."))
                return redirect("tenants:superadmin")
                
            # Set limits based on plan
            approver_limit = 2
            if plan_id == 'growth':
                approver_limit = 6
            elif plan_id == 'scale':
                approver_limit = 999
                
            Tenant.objects.create(
                name=name,
                key=key,
                plan_id=plan_id,
                status=status,
                seats=int(seats),
                approver_limit=approver_limit,
                is_active=(status == 'active')
            )
            messages.success(request, _("Tenant created successfully."))

        elif action == "edit_tenant":
            tenant_id = request.POST.get("tenant_id")
            name = request.POST.get("name")
            plan_id = request.POST.get("plan_id")
            status = request.POST.get("status")
            seats = request.POST.get("seats")
            
            tenant = get_object_or_404(Tenant, id=tenant_id)
            tenant.name = name
            tenant.plan_id = plan_id
            tenant.status = status
            if seats:
                tenant.seats = int(seats)
            tenant.is_active = (status == 'active')
            
            # Update approver limit based on plan
            if plan_id == 'starter':
                tenant.approver_limit = 2
            elif plan_id == 'growth':
                tenant.approver_limit = 6
            elif plan_id == 'scale':
                tenant.approver_limit = 999
                
            tenant.save()
            messages.success(request, _("Tenant updated successfully."))
            
        elif action == "invite_primary":
            tenant_id = request.POST.get("tenant_id")
            email = request.POST.get("email")
            
            if not all([tenant_id, email]):
                messages.error(request, _("Tenant and Email are required."))
                return redirect("tenants:superadmin")
                
            tenant = get_object_or_404(Tenant, id=tenant_id)
            
            from secrets import token_urlsafe
            
            invite, created = TenantUserInvite.objects.update_or_create(
                tenant=tenant,
                email=email,
                status="pending",
                defaults={
                    "role": "tenant_admin", # Primary user is admin
                    "token": token_urlsafe(32),
                    "expires_at": timezone.now() + timezone.timedelta(days=7),
                    "created_by": request.user,
                },
            )
            
            # Send email
            invite_url = request.build_absolute_uri(
                reverse("tenants:invite_accept", args=[invite.token])
            )
            
            if getattr(settings, "EMAIL_HOST", None):
                from django.core.mail import send_mail
                subject = _("You have been invited to manage '%(tenant)s'") % {"tenant": tenant.name}
                message = _(
                    "You have been invited to be the administrator for tenant '%(tenant)s' on SecureApprove.\n\n"
                    "To accept the invitation and set up your account, please click the following link:\n\n"
                    "%(url)s\n\n"
                ) % {"tenant": tenant.name, "url": invite_url}
                
                try:
                    send_mail(
                        subject,
                        message,
                        getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@secureapprove.com"),
                        [email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
            
            messages.success(request, _("Invitation sent to %(email)s") % {"email": email})

        return redirect("tenants:superadmin")
