# ==================================================
# SecureApprove Django - Main URLs
# ==================================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

# Swagger/API Documentation
schema_view = get_schema_view(
    openapi.Info(
        title="SecureApprove API",
        default_version='v1',
        description="API for SecureApprove - Approval Workflow System",
        contact=openapi.Contact(email="contact@secureapprove.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# API URLs (no i18n prefix)
api_urlpatterns = [
    path('api/auth/', include('apps.authentication.api_urls')),
    path('api/requests/', include('apps.requests.urls')),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]

# Main URL patterns with i18n
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Language switching
    path('i18n/', include('django.conf.urls.i18n')),
    
    # API routes (no translation)
    *api_urlpatterns,
]

# Internationalized URLs
urlpatterns += i18n_patterns(
    # Landing page as main page
    path('', include('apps.landing.urls')),
    
    # Dashboard for authenticated users
    path('dashboard/', include('apps.requests.urls')),
    
    # Web interface routes
    path('auth/', include('apps.authentication.urls')),
    path('billing/', include('apps.billing.urls')),
    
    # Django allauth
    path('accounts/', include('allauth.urls')),
    
    prefix_default_language=False,
)

# Static and media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns

# Custom error handlers
# handler404 = 'apps.core.views.handler404'
# handler500 = 'apps.core.views.handler500'