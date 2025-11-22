# ==================================================
# SecureApprove Django - Main URLs
# ==================================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
print(f"DEBUG: urls.py loaded. LANGUAGES={settings.LANGUAGES}")
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.i18n import set_language
from django.utils.translation import activate
from django.urls import translate_url
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

from django.views.generic import TemplateView
import os

# Custom view for Service Worker to avoid TemplateView issues
def service_worker(request):
    path = os.path.join(settings.BASE_DIR, 'templates', 'service_worker.js')
    try:
        with open(path, 'r') as f:
            content = f.read()
        return HttpResponse(content, content_type='application/javascript')
    except FileNotFoundError:
        return HttpResponse("/* Service Worker Not Found */", content_type='application/javascript', status=404)

# Health check endpoint
def health_check(request):
    return JsonResponse({"status": "healthy", "service": "secureapprove-django"})


# Custom language switcher with URL translation (works with i18n_patterns)
def custom_set_language(request):
    """
    Custom language switcher that properly handles i18n_patterns URL translation.
    It mirrors Django's set_language but also rewrites the URL prefix.
    """
    if request.method == "POST":
        lang_code = request.POST.get("language")
        next_url = request.POST.get("next", request.META.get("HTTP_REFERER", "/"))

        if lang_code and lang_code in dict(settings.LANGUAGES):
            # Translate the current URL to the new language prefix
            # We must do this BEFORE activating the new language, because resolve()
            # depends on the current language matching the URL prefix.
            try:
                next_translated = translate_url(next_url, lang_code)
            except Exception:
                next_translated = next_url

            # Activate language in this request
            activate(lang_code)

            # Build redirect response
            response = HttpResponseRedirect(next_translated)

            # Set language cookie
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                lang_code,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )

            # Store in session as well
            if hasattr(request, "session"):
                request.session[settings.LANGUAGE_COOKIE_NAME] = lang_code

            return response

    # Fallback
    return HttpResponseRedirect("/")

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
    path('api/requests/', include(('apps.requests.urls', 'requests'), namespace='api-requests')),
    path('api/chat/', include(('apps.chat.urls', 'chat'), namespace='api-chat')),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]

# Main URL patterns with i18n
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Health check (no i18n)
    path('health/', health_check, name='health'),
    
    # Service Worker
    path('service-worker.js', service_worker, name='service-worker'),
    path('webpush/', include('webpush.urls')),

    # i18n URLs (custom set_language with URL translation, CSRF-exempt for proxy issues)
    path('i18n/setlang/', csrf_exempt(custom_set_language), name='set_language'),
    path('i18n/', include('django.conf.urls.i18n')),
    
    # API routes (no translation)
    *api_urlpatterns,
]

# Internationalized URLs
i18n_urls = i18n_patterns(
    # Landing page as main page
    path('', include('apps.landing.urls')),
    
    # Dashboard for authenticated users
    path('dashboard/', include(('apps.requests.urls', 'requests'), namespace='dashboard-requests')),
    
    # Web interface routes
    path('auth/', include('apps.authentication.urls')),
    path('billing/', include('apps.billing.urls')),
    path('settings/tenant/', include(('apps.tenants.urls', 'tenants'), namespace='tenants')),
    
    # Django allauth
    path('accounts/', include('allauth.urls')),
    
    prefix_default_language=True,
)

print(f"DEBUG: i18n_patterns result: {i18n_urls}")

urlpatterns += i18n_urls

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
