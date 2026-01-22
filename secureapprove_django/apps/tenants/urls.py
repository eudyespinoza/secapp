from django.urls import path

from .views import TenantSettingsView, TenantAuditView, TenantInviteAcceptView, SuperAdminTenantView

app_name = "tenants"

urlpatterns = [
    # Mounted at /<lang>/settings/tenant/ in config.urls
    path("", TenantSettingsView.as_view(), name="settings"),
    path("audit/", TenantAuditView.as_view(), name="audit"),
    path("superadmin/", SuperAdminTenantView.as_view(), name="superadmin"),
    path("invite/<str:token>/", TenantInviteAcceptView.as_view(), name="invite_accept"),
]
