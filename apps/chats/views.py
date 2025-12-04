from rest_framework import viewsets, permissions
from .models import Chat, Message
from .serializers import ChatSerializer, MessageSerializer
from apps.common.permissions import IsOwnerOrAdmin

class ChatViewSet(viewsets.ModelViewSet):
    queryset = Chat.objects.all().select_related('product','buyer','seller')
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all().select_related('chat','sender')
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)
