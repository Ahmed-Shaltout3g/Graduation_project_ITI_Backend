from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatViewSet, MessageViewSet

router = DefaultRouter()
router.register('chats', ChatViewSet)
router.register('messages', MessageViewSet)

urlpatterns = [path('', include(router.urls))]
