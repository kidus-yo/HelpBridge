from rest_framework import serializers
from common.languages import LANGUAGE_CHOICES
from .models import AccessibilityPreference

class AccessibilityPreferenceSerializer(serializers.ModelSerializer):
    language = serializers.CharField(source='preferred_language', read_only=True)
    voice_enabled = serializers.SerializerMethodField()
    right_to_left = serializers.SerializerMethodField()

    class Meta:
        model = AccessibilityPreference
        fields = [
            'id', 'session', 'preferred_language', 'language',
            'simple_mode', 'text_size', 'voice_enabled',
            'voice_input_enabled', 'voice_output_enabled',
            'text_direction', 'right_to_left', 'high_contrast',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'session', 'created_at', 'updated_at']

    def get_voice_enabled(self, obj):
        return obj.voice_input_enabled or obj.voice_output_enabled

    def get_right_to_left(self, obj):
        return obj.text_direction == 'rtl'

class UpdateAccessibilityPreferenceSerializer(serializers.ModelSerializer):
    language = serializers.ChoiceField(choices=LANGUAGE_CHOICES, required=False, write_only=True)
    voice_enabled = serializers.BooleanField(required=False, write_only=True)
    right_to_left = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = AccessibilityPreference
        fields = [
            'preferred_language', 'language', 'simple_mode', 'text_size',
            'voice_enabled', 'voice_input_enabled', 'voice_output_enabled',
            'text_direction', 'right_to_left', 'high_contrast'
        ]

    def validate(self, attrs):
        # Support user's "language" alias
        if 'language' in attrs:
            attrs['preferred_language'] = attrs.pop('language')

        # Support user's "voice_enabled" alias
        if 'voice_enabled' in attrs:
            ve = attrs.pop('voice_enabled')
            attrs['voice_input_enabled'] = ve
            attrs['voice_output_enabled'] = ve

        # Support user's "right_to_left" alias
        if 'right_to_left' in attrs:
            rtl = attrs.pop('right_to_left')
            attrs['text_direction'] = 'rtl' if rtl else 'ltr'

        return attrs
