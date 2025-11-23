
import os
import sys
import django
import inspect

sys.path.append(os.path.join(os.getcwd(), 'secureapprove_django'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import webpush.models
import inspect
print(inspect.getsource(webpush.models.SubscriptionInfo))
