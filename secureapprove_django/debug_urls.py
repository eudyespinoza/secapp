import os
import django
from django.urls import get_resolver

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

resolver = get_resolver()
url_patterns = resolver.url_patterns

def print_urls(patterns, prefix=''):
    for pattern in patterns:
        if hasattr(pattern, 'url_patterns'):
            print_urls(pattern.url_patterns, prefix + pattern.pattern.regex.pattern)
        else:
            print(prefix + pattern.pattern.regex.pattern)

print("Printing all URLs:")
# This is a simplified printer, might not handle all regex perfectly but good enough to see if presence is there
from django_extensions.management.commands.show_urls import Command
c = Command()
c.handle(no_color=True, format='table', urlconf='config.urls', order='url', language=None, decorator=None, app=None)
