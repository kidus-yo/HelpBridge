from django.contrib import admin

from platforms.models import Institution, Platform, PlatformIntegration


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "platform_type", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "institution_type", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PlatformIntegration)
class PlatformIntegrationAdmin(admin.ModelAdmin):
    list_display = ("name", "platform", "institution", "status", "api_key_prefix")
    readonly_fields = ("api_key_hash", "api_key_prefix")
    search_fields = ("name",)
