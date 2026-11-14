from rest_framework import serializers
from .models import AccessibilityPreference

class AccessibilityPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessibilityPreference
        fields = [
            'id', 'session', 'preferred_language', 'simple_mode',
            'text_size', 'voice_input_enabled', 'voice_output_enabled',
            'text_direction', 'high_contrast', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'session', 'created_at', 'updated_at']

class UpdateAccessibilityPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessibilityPreference
        fields = [
            'preferred_language', 'simple_mode', 'text_size',
            'voice_input_enabled', 'voice_output_enabled',
            'text_direction', 'high_contrast'
        ]

