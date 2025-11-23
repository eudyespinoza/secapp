
import os
import sys
import django
from django.urls import get_resolver

# Setup Django environment
sys.path.append(os.path.join(os.getcwd(), 'secureapprove_django'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

def print_urls(urlpatterns, prefix=''):
    for entry in urlpatterns:
        if hasattr(entry, 'url_patterns'):
            # It's an include
            new_prefix = prefix + str(entry.pattern)
            print_urls(entry.url_patterns, new_prefix)
        else:
            print(f"{prefix}{entry.pattern} -> {entry.name}")

resolver = get_resolver()
# Filter for webpush
print("Searching for webpush URLs...")
for pattern in resolver.url_patterns:
    if str(pattern.pattern) == 'webpush/':
        print_urls(pattern.url_patterns, 'webpush/')
