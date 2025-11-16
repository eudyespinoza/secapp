from django.shortcuts import render
from django.views.decorators.cache import never_cache

@never_cache
def test_i18n_view(request):
    return render(request, 'test_i18n.html')
