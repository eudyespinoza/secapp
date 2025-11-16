from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.requests.models import ApprovalRequest
from .models import TenantUserInvite
from .utils import ensure_user_tenant

User = get_user_model()


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
            },
        )

    def post(self, request):
        tenant = self.get_tenant(request)
        if not tenant or not request.user.can_admin_tenant():
            return redirect("landing:index")

        action = request.POST.get("action")
        if action == "update_user":
            user_id = request.POST.get("user_id")
            role = request.POST.get("role")
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
