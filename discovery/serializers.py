from django.contrib.auth.models import User
from rest_framework import serializers

from discovery.models import Product, ProductMetadata


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            # use the email so that we can log in with the email address without any changes
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            is_active=False,
        )
        return user


class LoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")


class ProductMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductMetadata
        exclude = ["product"]


class ProductSerializer(serializers.ModelSerializer):
    metadata = ProductMetadataSerializer()

    class Meta:
        model = Product
        fields = "__all__"
