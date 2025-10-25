from django.urls import path
from .views import LandingPageView, DemoPageView

app_name = 'landing'

urlpatterns = [
    path('', LandingPageView.as_view(), name='index'),
    path('demo/', DemoPageView.as_view(), name='demo'),
]