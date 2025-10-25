# ==================================================
# SecureApprove Django - Billing Apps Config
# ==================================================

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.billing'
    verbose_name = _('Billing')
    
    def ready(self):
        import apps.billing.signals