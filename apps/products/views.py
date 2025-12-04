from rest_framework import viewsets, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import PermissionDenied

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from apps.common.permissions import IsAdminOrReadOnly, IsOwnerOrAdmin

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related('category', 'seller')
    serializer_class = ProductSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'category': ['exact'],
        'price': ['exact', 'lt', 'gt'],
        'university': ['exact'],
        'faculty': ['exact'],
        'status': ['exact'],
        'seller__id': ['exact'],  # دعم فلترة البائع
    }
    search_fields = ['title', 'description']
    ordering_fields = ['price', 'created_at']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_staff:
            count = Product.objects.filter(seller=user).count()
            if count >= 2:
                raise PermissionDenied("Regular users can only add up to 2 products.")
        # Enforce default status for regular users: newly created products by non-staff
        # must be inactive. Staff users may set status when creating.
        if not user.is_staff:
            # newly created products by non-staff go to 'pending' for admin approval
            serializer.save(seller=user, status='pending')
        else:
            serializer.save(seller=user)

    def perform_update(self, serializer):
        # Prevent non-staff users from changing status to 'active'. Admin/staff can.
        requested_status = None
        try:
            requested_status = self.request.data.get('status')
        except Exception:
            requested_status = None

        if requested_status == 'active' and not self.request.user.is_staff:
            raise PermissionDenied('Only admin/staff can set product status to active.')

        serializer.save()
