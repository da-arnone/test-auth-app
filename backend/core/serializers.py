from rest_framework import serializers

from .models import AppUser, UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    appScope = serializers.CharField(source="app_scope")

    class Meta:
        model = UserProfile
        fields = ["appScope", "role", "context"]


class UserSerializer(serializers.ModelSerializer):
    profiles = UserProfileSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = AppUser
        fields = ["id", "username", "suspended", "createdAt", "updatedAt", "profiles"]

