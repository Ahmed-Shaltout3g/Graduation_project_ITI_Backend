from rest_framework import serializers
from .models import Category, Product

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    seller = serializers.ReadOnlyField(source='sellxer.id')
    class Meta:
        model = Product
        fields = '__all__'
        read_only_fields = ('seller','created_at','updated_at')
