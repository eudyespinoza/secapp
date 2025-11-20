# ==================================================
# SecureApprove Django - Test Configuration
# ==================================================

import os
import sys
from pathlib import Path

import django
from django.conf import settings

def pytest_configure():
    """Configure Django settings for pytest"""
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
        django.setup()
