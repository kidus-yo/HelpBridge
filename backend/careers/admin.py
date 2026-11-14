from django.contrib import admin
from careers.models import JobListing, AccommodationRequest, JobAlertSubscription


@admin.register(JobListing)
class JobListingAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'organization', 'location', 'employment_type', 'remote_policy', 'status', 'is_demo', 'deadline', 'created_at']
    list_filter = ['status', 'employment_type', 'remote_policy', 'is_demo']
    search_fields = ['title', 'organization', 'description', 'location', 'id']


@admin.register(AccommodationRequest)
class AccommodationRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'job_listing', 'preferred_contact_method', 'contact_details', 'status', 'created_at']
    list_filter = ['status', 'preferred_contact_method']
    search_fields = ['contact_details', 'description', 'id']


@admin.register(JobAlertSubscription)
class JobAlertSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'contact_identity', 'channel', 'location_preference', 'is_active', 'created_at']
    list_filter = ['channel', 'is_active']
    search_fields = ['contact_identity', 'location_preference', 'id']
