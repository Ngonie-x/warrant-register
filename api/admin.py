"""
Admin configuration for API models.
"""

from django.contrib import admin
from .models import (
    WarrantyRegistration, 
    WarrantyAuditLog, 
    Department, 
    Category, 
    Profile
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'external_id', 'created_at', 'synced_at']
    search_fields = ['name', 'external_id']
    ordering = ['name']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'external_id', 'created_at', 'synced_at']
    search_fields = ['name', 'external_id']
    ordering = ['name']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'role', 'department', 'external_id', 'synced_at']
    search_fields = ['full_name', 'external_id', 'department']
    list_filter = ['role', 'department']
    ordering = ['full_name']


class WarrantyAuditLogInline(admin.TabularInline):
    model = WarrantyAuditLog
    extra = 0
    readonly_fields = [
        'action', 'performed_by', 'performed_by_name', 
        'old_value', 'new_value', 'ip_address', 'timestamp'
    ]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(WarrantyRegistration)
class WarrantyRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'asset_name', 'asset_external_id', 'category', 'department',
        'status', 'registered_by_name', 'registered_at', 
        'warranty_end_date', 'is_warranty_active'
    ]
    list_filter = ['status', 'category', 'department', 'registered_at']
    search_fields = [
        'asset_name', 'asset_external_id', 'serial_number',
        'registered_by_name', 'manufacturer', 'model_number'
    ]
    readonly_fields = ['registered_at', 'updated_at', 'is_warranty_active', 'days_until_expiry']
    ordering = ['-registered_at']
    date_hierarchy = 'registered_at'
    inlines = [WarrantyAuditLogInline]
    
    fieldsets = (
        ('Asset Information', {
            'fields': (
                'asset_external_id', 'asset_name', 'category', 
                'department', 'cost', 'date_purchased'
            )
        }),
        ('Asset Creator (Next.js)', {
            'fields': ('asset_created_by', 'asset_created_at'),
            'classes': ('collapse',)
        }),
        ('Warranty Details', {
            'fields': (
                'status', 'warranty_start_date', 'warranty_end_date',
                'warranty_duration_months', 'is_warranty_active', 'days_until_expiry'
            )
        }),
        ('Registration Info', {
            'fields': (
                'registered_by', 'registered_by_name', 
                'registered_by_external_id', 'registered_at', 'updated_at'
            )
        }),
        ('Device Details', {
            'fields': ('serial_number', 'manufacturer', 'model_number'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def is_warranty_active(self, obj):
        return obj.is_warranty_active
    is_warranty_active.boolean = True
    is_warranty_active.short_description = 'Active?'

    def days_until_expiry(self, obj):
        days = obj.days_until_expiry
        if days is None:
            return 'N/A'
        if days < 0:
            return f'Expired {abs(days)} days ago'
        return f'{days} days'
    days_until_expiry.short_description = 'Days Until Expiry'


@admin.register(WarrantyAuditLog)
class WarrantyAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'warranty', 'action', 'performed_by_name', 
        'ip_address', 'timestamp'
    ]
    list_filter = ['action', 'timestamp']
    search_fields = ['warranty__asset_name', 'performed_by_name']
    readonly_fields = [
        'warranty', 'action', 'performed_by', 'performed_by_name',
        'old_value', 'new_value', 'ip_address', 'user_agent', 'timestamp'
    ]
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
