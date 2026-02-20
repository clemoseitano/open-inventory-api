import json
from django.contrib.auth.models import User
from rest_framework import serializers
from discovery.models import Product, ProductMetadata, SyncJournal, Tenant


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "first_name", "last_name", "email", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(
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


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class SyncActionSerializer(serializers.Serializer):
    id = serializers.CharField()
    actionType = serializers.CharField()
    payload = serializers.JSONField()
    createdAt = serializers.CharField(required=False)


class SyncJournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyncJournal
        fields = ("action_id", "action_type", "payload", "created_at")

    def to_representation(self, instance):
        payload = instance.payload
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except:
                pass
        return {
            "id": instance.action_id,
            "actionType": instance.action_type,
            "payload": payload,
            "createdAt": instance.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
