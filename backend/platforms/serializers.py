from rest_framework import serializers

from platforms.models import Institution, Platform, PlatformIntegration
from platforms.services.credentials import generate_api_key, hash_api_key, key_prefix
from platforms.services.context import CONTEXT_TYPES, DEFAULT_SCOPES


class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = [
            "id",
            "name",
            "slug",
            "platform_type",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "slug",
            "institution_type",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PlatformIntegrationSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(read_only=True)

    class Meta:
        model = PlatformIntegration
        fields = [
            "id",
            "platform",
            "institution",
            "name",
            "status",
            "permitted_scopes",
            "api_key_prefix",
            "api_key",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "api_key_prefix", "api_key", "created_at", "updated_at"]

    def create(self, validated_data):
        raw_key = generate_api_key()
        validated_data["api_key_hash"] = hash_api_key(raw_key)
        validated_data["api_key_prefix"] = key_prefix(raw_key)
        if not validated_data.get("permitted_scopes"):
            validated_data["permitted_scopes"] = list(DEFAULT_SCOPES) + [
                "courses:write",
                "knowledge:write",
            ]
        integration = super().create(validated_data)
        integration.api_key = raw_key
        return integration


class IssueContextTokenSerializer(serializers.Serializer):
    user_ref = serializers.CharField(max_length=128)
    context_type = serializers.ChoiceField(choices=[(c, c) for c in CONTEXT_TYPES], default="general")
    context_id = serializers.CharField(max_length=64, required=False, allow_blank=True, allow_null=True)
    preferred_language = serializers.CharField(max_length=8, default="en")
    scopes = serializers.ListField(child=serializers.CharField(max_length=64), required=False)
