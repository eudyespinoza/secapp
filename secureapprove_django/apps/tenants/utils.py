from django.utils import timezone

from .models import Tenant, TenantUserInvite


def ensure_user_tenant(user):
    """
    Ensure the given user has an associated tenant.

    - If already has tenant, returns it.
    - If no tenant and user is staff/superuser OR has an administrative
      tenant role, creates or reuses a default tenant named "SecureApprove"
      and assigns the user as tenant_admin when needed.
    """
    if getattr(user, "tenant_id", None):
        return user.tenant

    # Allow automatic tenant creation for:
    #   - staff / superuser (Django flags)
    #   - users with tenant_admin / superadmin role
    role = getattr(user, "role", None)
    is_admin_role = role in ("tenant_admin", "superadmin")
    if not (user.is_staff or user.is_superuser or is_admin_role):
        return None

    key = "secureapprove"
    tenant, _ = Tenant.objects.get_or_create(
        key=key,
        defaults={
            "name": "SecureApprove",
            "plan_id": "scale",
            "seats": 10,
            "approver_limit": 999,
            "status": "active",
            "is_active": True,
            "billing": {
                "provisioned_at": timezone.now().isoformat(),
                "provider": "internal",
            },
        },
    )

    user.tenant = tenant
    # Asegurar rol administrativo mínimo
    if getattr(user, "role", None) not in ("tenant_admin", "superadmin"):
        user.role = "tenant_admin"
    user.save(update_fields=["tenant", "role"])
    return tenant


def assign_tenant_from_reservation(user):
    """
    If there is a pending TenantUserInvite for this user's email,
    and the user has no tenant yet, associate the user with that
    tenant (respecting seat limits) and mark the reservation as
    accepted.
    """
    email = (getattr(user, "email", "") or "").lower()
    if not email:
        return

    # Do not override existing tenant assignments
    if getattr(user, "tenant_id", None):
        return

    invite = (
        TenantUserInvite.objects.filter(
            email=email,
            status="pending",
            tenant__is_active=True,
        )
        .order_by("-created_at")
        .first()
    )
    if not invite or invite.is_expired:
        return

    tenant = invite.tenant

    seats = tenant.seats or 0
    used_seats = tenant.used_seats
    has_subscription = hasattr(tenant, "subscription")
    can_by_subscription = (
        tenant.subscription.can_create_user() if has_subscription else True
    )

    if seats and used_seats >= seats:
        return

    if not can_by_subscription:
        return

    user.tenant = tenant
    # Do not downgrade superadmin; otherwise honour reserved role
    if getattr(user, "role", None) not in ("superadmin",) and invite.role:
        user.role = invite.role
    user.is_active = True
    user.save(update_fields=["tenant", "role", "is_active"])

    invite.status = "accepted"
    invite.accepted_at = timezone.now()
    invite.save(update_fields=["status", "accepted_at"])


def generate_unique_slug(name):
    """Generate a unique tenant key slug from a name"""
    from django.utils.text import slugify
    import random
    import string

    base_slug = slugify(name)
    if not base_slug:
        base_slug = "tenant"

    slug = base_slug
    counter = 1

    while Tenant.objects.filter(key=slug).exists():
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        slug = f"{base_slug}-{suffix}"
        counter += 1

    return slug
