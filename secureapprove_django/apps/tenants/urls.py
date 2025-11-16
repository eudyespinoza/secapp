from django.urls import path

from .views import TenantSettingsView, TenantInviteAcceptView

app_name = "tenants"

urlpatterns = [
    # Mounted at /<lang>/settings/tenant/ in config.urls
    path("", TenantSettingsView.as_view(), name="settings"),
    path("invite/<str:token>/", TenantInviteAcceptView.as_view(), name="invite_accept"),
]
