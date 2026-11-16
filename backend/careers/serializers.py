"""
Serializers for Careers, Accommodations, and Job Alert Subscriptions.
"""

from rest_framework import serializers
from careers.models import JobListing, AccommodationRequest, JobAlertSubscription


class JobListingSerializer(serializers.ModelSerializer):
    """
    Public representation of published job listings.
    """
    employment_type_display = serializers.CharField(source='get_employment_type_display', read_only=True)
    remote_policy_display = serializers.CharField(source='get_remote_policy_display', read_only=True)

    class Meta:
        model = JobListing
        fields = [
            'id',
            'title',
            'organization',
            'description',
            'location',
            'employment_type',
            'employment_type_display',
            'remote_policy',
            'remote_policy_display',
            'application_url',
            'contact_instructions',
            'required_skills',
            'salary_info',
            'deadline',
            'source_url',
            'is_demo',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class JobListingAdminSerializer(serializers.ModelSerializer):
    """
    Staff representation for managing and publishing job listings.
    """
    class Meta:
        model = JobListing
        fields = [
            'id',
            'title',
            'organization',
            'description',
            'location',
            'employment_type',
            'remote_policy',
            'application_url',
            'contact_instructions',
            'required_skills',
            'salary_info',
            'deadline',
            'source_url',
            'status',
            'is_demo',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class JobQuestionRequestSerializer(serializers.Serializer):
    job_id = serializers.UUIDField(required=True)
    question = serializers.CharField(required=True, max_length=500)
    language = serializers.CharField(required=False, default='en', max_length=10)


class JobQuestionResponseSerializer(serializers.Serializer):
    job_id = serializers.UUIDField()
    job_title = serializers.CharField()
    organization = serializers.CharField()
    question = serializers.CharField()
    answer = serializers.CharField()
    grounded = serializers.BooleanField()
    field_referenced = serializers.CharField(allow_null=True)
    language = serializers.CharField()
    source = serializers.CharField()


class AccommodationRequestSerializer(serializers.ModelSerializer):
    """
    Privacy-First accommodation request serializer.
    Focuses solely on functional adjustments without requesting medical diagnosis.
    """
    job_title = serializers.CharField(source='job_listing.title', read_only=True)
    guest_token = serializers.SerializerMethodField()

    class Meta:
        model = AccommodationRequest
        fields = [
            'id',
            'job_listing',
            'job_title',
            'functional_needs',
            'description',
            'preferred_contact_method',
            'contact_details',
            'status',
            'coordinator_response',
            'guest_token',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'status', 'coordinator_response', 'guest_token', 'created_at', 'updated_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated and request.user.is_staff:
            self.fields['status'].read_only = False
            self.fields['coordinator_response'].read_only = False

    def validate_functional_needs(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("functional_needs must be a list of adjustment requirements.")
        return value

    def get_guest_token(self, obj):
        request = self.context.get('request')
        if request and request.method == 'POST' and obj.learner_id is None:
            return obj.guest_token
        return ''


class JobAlertSubscriptionSerializer(serializers.ModelSerializer):
    guest_token = serializers.SerializerMethodField()

    class Meta:
        model = JobAlertSubscription
        fields = [
            'id',
            'contact_identity',
            'channel',
            'keywords',
            'location_preference',
            'is_active',
            'guest_token',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'guest_token', 'created_at', 'updated_at']

    def validate_keywords(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("keywords must be a list of search terms.")
        return value

    def get_guest_token(self, obj):
        request = self.context.get('request')
        if request and request.method == 'POST' and obj.learner_id is None:
            return obj.guest_token
        return ''
