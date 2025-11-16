from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ChatConversationViewSet


router = DefaultRouter()
router.register(r'conversations', ChatConversationViewSet, basename='chat-conversation')

app_name = 'chat'

urlpatterns = [
    path('', include(router.urls)),
]

