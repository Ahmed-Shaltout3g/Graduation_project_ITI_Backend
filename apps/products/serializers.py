from rest_framework import serializers
from .models import Category, Product

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    seller = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ('seller','created_at','updated_at')

    def get_seller(self, obj):
        if obj.seller:
            return {
                "id": obj.seller.id,
                "email": obj.seller.email,
                "first_name": obj.seller.first_name,
                "phone": getattr(obj.seller, "phone", None)
            }
        return None

    def validate_status(self, value):
        """Ensure status is one of the allowed STATUS_CHOICES on Product."""
        allowed = [c[0] for c in Product.STATUS_CHOICES]
        if value not in allowed:
            raise serializers.ValidationError(f"status must be one of {allowed}")
        return value
