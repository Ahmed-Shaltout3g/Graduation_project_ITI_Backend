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
        fields = ['id', 'title', 'description', 'price', 'condition', 'image', 'images', 'category', 'seller', 'university', 'faculty', 'is_featured', 'status', 'created_at', 'updated_at', 'category_name']
        read_only_fields = ('seller','created_at','updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and not request.user.is_staff:
            # For non-staff users, status is set automatically, so remove it from input fields
            self.fields.pop('status', None)

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
        if value:  # Only validate if value is provided
            allowed = [c[0] for c in Product.STATUS_CHOICES]
            if value not in allowed:
                raise serializers.ValidationError(f"status must be one of {allowed}")
        return value

    def validate(self, data):
        # For non-staff users, status field should not be required during validation
        request = self.context.get('request')
        if request and request.user and not request.user.is_staff:
            # Remove status from validation if it's empty for non-staff
            if 'status' in data and not data['status']:
                data.pop('status', None)
        return data
from django.contrib.auth import get_user_model

User = get_user_model()

class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email")
