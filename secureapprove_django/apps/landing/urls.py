from django.urls import path
from .views import LandingPageView, DemoPageView, TermsView
from .test_i18n_view import test_i18n_view

app_name = 'landing'

urlpatterns = [
    path('', LandingPageView.as_view(), name='index'),
    path('terms/', TermsView.as_view(), name='terms'),
    path('demo/', DemoPageView.as_view(), name='demo'),
    path('test-i18n/', test_i18n_view, name='test_i18n'),
]