from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ChatConversationViewSet, download_attachment


router = DefaultRouter()
router.register(r'conversations', ChatConversationViewSet, basename='chat-conversation')

app_name = 'chat'

urlpatterns = [
    path('', include(router.urls)),
    path('attachments/<uuid:attachment_id>/download/', download_attachment, name='download-attachment'),
]

