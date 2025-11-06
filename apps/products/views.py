from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from apps.common.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin
from apps.common.permissions import IsOwnerOrAdmin
from rest_framework.exceptions import PermissionDenied
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related('category','seller')
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category','price','university','faculty','status']
    search_fields = ['title','description']
    ordering_fields = ['price','created_at']

    def get_permissions(self):
        # Anyone can GET or POST (create)
        if self.action in ['list', 'retrieve', 'create']:
            return [permissions.AllowAny()]
        # For update, partial_update, destroy → only owner/admin
        return [IsOwnerOrAdmin()]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_staff:  # Regular users
            user_products_count = Product.objects.filter(seller=user).count()
            if user_products_count >= 2:
                raise PermissionDenied("Regular users can only add up to 2 products.")
        serializer.save(seller=user)