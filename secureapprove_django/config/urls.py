# ==================================================
# SecureApprove Django - Main URLs
# ==================================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.i18n import set_language
from django.utils.translation import activate
from django.urls import translate_url
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

# Health check endpoint
def health_check(request):
    return JsonResponse({"status": "healthy", "service": "secureapprove-django"})

# Custom language switcher with URL translation
def custom_set_language(request):
    """
    Custom language switcher that properly handles i18n_patterns URL translation.
    This extends Django's built-in set_language view with translate_url support.
    """
    if request.method == 'POST':
        lang_code = request.POST.get('language')
        next_url = request.POST.get('next', request.META.get('HTTP_REFERER', '/'))
        
        if lang_code and lang_code in dict(settings.LANGUAGES):
            # Activate the language
            activate(lang_code)
            
            # Translate the current URL to use the new language prefix
            next_trans = translate_url(next_url, lang_code)
            
            # Create response with redirect
            response = HttpResponseRedirect(next_trans)
            
            # Set language in cookie
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
            
            # Also store in session
            if hasattr(request, 'session'):
                request.session[settings.LANGUAGE_COOKIE_NAME] = lang_code
            
            return response
    
    # Fallback to root
    return HttpResponseRedirect('/')



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
    
    # Django's built-in i18n URLs (includes set_language with CSRF support)
    path('i18n/', include('django.conf.urls.i18n')),
    
    # API routes (no translation)
    *api_urlpatterns,
]

# Internationalized URLs
urlpatterns += i18n_patterns(
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
