from django.contrib import admin
from channels.models import ChannelIdentity, MessageDelivery

@admin.register(ChannelIdentity)
class ChannelIdentityAdmin(admin.ModelAdmin):
    list_display = ('channel', 'external_id', 'phone_number', 'preferred_language', 'is_active', 'created_at')
    list_filter = ('channel', 'preferred_language', 'is_active')
    search_fields = ('external_id', 'phone_number', 'username', 'session_id')


@admin.register(MessageDelivery)
class MessageDeliveryAdmin(admin.ModelAdmin):
    list_display = ('id', 'channel', 'recipient', 'status', 'created_at', 'delivered_at')
    list_filter = ('channel', 'status', 'created_at')
    search_fields = ('recipient', 'content')
