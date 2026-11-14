from django.contrib import admin
from support.models import SupportRequest, SupportMessage


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0
    readonly_fields = ['id', 'sender_type', 'sender', 'content', 'is_snapshot', 'created_at']


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'subject', 'category', 'priority', 'status', 'assigned_agent', 'screen_share_active', 'created_at']
    list_filter = ['status', 'category', 'priority', 'screen_share_active', 'language']
    search_fields = ['subject', 'description', 'id', 'guest_token']
    inlines = [SupportMessageInline]


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'support_request', 'sender_type', 'sender', 'is_read', 'is_snapshot', 'created_at']
    list_filter = ['sender_type', 'is_read', 'is_snapshot']
    search_fields = ['content', 'id']
