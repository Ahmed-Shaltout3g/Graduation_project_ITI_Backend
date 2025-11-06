from rest_framework import serializers
from .models import Chat, Message

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.ReadOnlyField(source='sender.id')
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ('timestamp','sender')

class ChatSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    class Meta:
        model = Chat
        fields = '__all__'
        read_only_fields = ('created_at',)
