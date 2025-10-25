# ==================================================
# SecureApprove Django - Simplified URLs for Demo
# ==================================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

# Main URL patterns
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Language switching
    path('i18n/', include('django.conf.urls.i18n')),
]

# Internationalized URLs
urlpatterns += i18n_patterns(
    # Landing page as main page
    path('', include('apps.landing.urls')),
    
    prefix_default_language=False,
)

# Static and media files
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)