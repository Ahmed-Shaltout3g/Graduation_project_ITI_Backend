from rest_framework import viewsets, permissions
from django.contrib.auth import get_user_model
from .serializers import UserSerializer
from apps.common.permissions import IsOwnerOrAdmin

# SimpleJWT imports for custom token behavior
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claim for role: normalize to only 'admin' or 'user'
        role = 'admin' if (user.is_superuser or user.is_staff) else 'user'
        token['role'] = role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Include role in the response payload for convenience (admin/user)
        data['role'] = 'admin' if (self.user.is_superuser or self.user.is_staff) else 'user'
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return User.objects.all()
        return User.objects.filter(id=user.id)

    def perform_update(self, serializer):
        serializer.save()

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        elif self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]
        return [permissions.IsAuthenticated()]
