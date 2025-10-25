"""
Custom middleware for SecureApprove
"""
from django.utils.translation import get_language
from django.urls import translate_url
from django.http import HttpResponseRedirect


class LanguageURLMiddleware:
    """
    Middleware to handle URL translation when language changes with i18n_patterns.
    
    This ensures that when a user changes language, the URL prefix changes accordingly:
    /es/billing/plans/ -> /en/billing/plans/
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Store the current language before processing
        old_lang = get_language()
        
        # Process the request
        response = self.get_response(request)
        
        # Check if this is a redirect response from set_language view
        if (isinstance(response, HttpResponseRedirect) and 
            hasattr(request, 'session') and 
            'django_language' in request.session):
            
            new_lang = request.session['django_language']
            
            # If language changed, translate the redirect URL
            if new_lang != old_lang and response.url:
                translated_url = translate_url(response.url, new_lang)
                response['Location'] = translated_url
        
        return response
