"""
API Serializers for Warranty Registration System

Handles serialization and validation of warranty registration data
received from the Next.js application.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    WarrantyRegistration, 
    WarrantyAuditLog, 
    Department, 
    Category, 
    Profile
)


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for Department model."""
    
    class Meta:
        model = Department
        fields = ['id', 'external_id', 'name', 'created_at', 'synced_at']
        read_only_fields = ['id', 'synced_at']


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""
    
    class Meta:
        model = Category
        fields = ['id', 'external_id', 'name', 'created_at', 'synced_at']
        read_only_fields = ['id', 'synced_at']


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for Profile model."""
    
    class Meta:
        model = Profile
        fields = ['id', 'external_id', 'full_name', 'role', 'department', 'synced_at']
        read_only_fields = ['id', 'synced_at']


class WarrantyRegistrationSerializer(serializers.ModelSerializer):
    """
    Full serializer for WarrantyRegistration model.
    Used for listing and retrieving warranty registrations.
    """
    is_warranty_active = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    registered_by_username = serializers.CharField(
        source='registered_by.username', 
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = WarrantyRegistration
        fields = [
            'id',
            'asset_external_id',
            'asset_name',
            'category',
            'department',
            'cost',
            'date_purchased',
            'asset_created_by',
            'asset_created_at',
            'status',
            'status_display',
            'registered_by',
            'registered_by_username',
            'registered_by_name',
            'registered_by_external_id',
            'registered_at',
            'updated_at',
            'warranty_start_date',
            'warranty_end_date',
            'warranty_duration_months',
            'is_warranty_active',
            'days_until_expiry',
            'notes',
            'serial_number',
            'manufacturer',
            'model_number',
        ]
        read_only_fields = [
            'id', 
            'registered_at', 
            'updated_at',
            'is_warranty_active',
            'days_until_expiry',
        ]


class WarrantyRegistrationCreateSerializer(serializers.Serializer):
    """
    Serializer for creating warranty registrations from Next.js app.
    
    This accepts the asset data structure from the Next.js application
    and creates a warranty registration record.
    """
    
    # Asset data from Next.js (maps to assets table)
    id = serializers.CharField(
        help_text="Asset ID from Next.js app"
    )
    name = serializers.CharField(
        max_length=255,
        help_text="Asset name"
    )
    category = serializers.CharField(
        max_length=255, 
        required=False, 
        allow_null=True, 
        allow_blank=True,
        help_text="Category name or ID"
    )
    department = serializers.CharField(
        max_length=255, 
        required=False, 
        allow_null=True, 
        allow_blank=True,
        help_text="Department name or ID"
    )
    cost = serializers.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        required=False, 
        allow_null=True,
        help_text="Asset cost"
    )
    date_purchased = serializers.DateField(
        required=False, 
        allow_null=True,
        help_text="Purchase date"
    )
    created_by = serializers.CharField(
        required=False, 
        allow_null=True, 
        allow_blank=True,
        help_text="User ID who created the asset in Next.js"
    )
    created_at = serializers.DateTimeField(
        required=False, 
        allow_null=True,
        help_text="When the asset was created in Next.js"
    )
    
    # Registration metadata (who is registering the warranty)
    registered_by_id = serializers.CharField(
        required=False, 
        allow_null=True, 
        allow_blank=True,
        help_text="User ID from Next.js app performing registration"
    )
    registered_by_name = serializers.CharField(
        required=False, 
        allow_null=True, 
        allow_blank=True,
        help_text="Name of user performing registration"
    )
    
    # Optional warranty details
    warranty_duration_months = serializers.IntegerField(
        required=False, 
        default=12,
        min_value=1,
        max_value=120,
        help_text="Warranty duration in months"
    )
    serial_number = serializers.CharField(
        max_length=255, 
        required=False, 
        allow_null=True, 
        allow_blank=True,
        help_text="Device serial number"
    )
    manufacturer = serializers.CharField(
        max_length=255, 
        required=False, 
        allow_null=True, 
        allow_blank=True,
        help_text="Device manufacturer"
    )
    model_number = serializers.CharField(
        max_length=255, 
        required=False, 
        allow_null=True, 
        allow_blank=True,
        help_text="Device model number"
    )
    notes = serializers.CharField(
        required=False, 
        allow_null=True, 
        allow_blank=True,
        help_text="Additional notes"
    )

    def validate_id(self, value):
        """Check if asset is already registered."""
        if WarrantyRegistration.objects.filter(asset_external_id=value).exists():
            raise serializers.ValidationError(
                "This asset has already been registered for warranty."
            )
        return value

    def create(self, validated_data):
        """Create a new warranty registration."""
        warranty = WarrantyRegistration.objects.create(
            asset_external_id=validated_data['id'],
            asset_name=validated_data['name'],
            category=validated_data.get('category'),
            department=validated_data.get('department'),
            cost=validated_data.get('cost'),
            date_purchased=validated_data.get('date_purchased'),
            asset_created_by=validated_data.get('created_by'),
            asset_created_at=validated_data.get('created_at'),
            registered_by_external_id=validated_data.get('registered_by_id'),
            registered_by_name=validated_data.get('registered_by_name'),
            warranty_duration_months=validated_data.get('warranty_duration_months', 12),
            serial_number=validated_data.get('serial_number'),
            manufacturer=validated_data.get('manufacturer'),
            model_number=validated_data.get('model_number'),
            notes=validated_data.get('notes'),
            status=WarrantyRegistration.WarrantyStatus.REGISTERED,
        )
        return warranty


class WarrantyRegistrationResponseSerializer(serializers.Serializer):
    """
    Response serializer for successful warranty registration.
    Returns the expected response format for the Next.js app.
    """
    success = serializers.BooleanField()
    message = serializers.CharField()
    status = serializers.CharField()
    status_label = serializers.CharField()
    warranty_id = serializers.IntegerField()
    asset_id = serializers.CharField()
    registered_at = serializers.DateTimeField()
    warranty_start_date = serializers.DateField()
    warranty_end_date = serializers.DateField()


class WarrantyAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for warranty audit logs."""
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    asset_name = serializers.CharField(source='warranty.asset_name', read_only=True)
    
    class Meta:
        model = WarrantyAuditLog
        fields = [
            'id',
            'warranty',
            'asset_name',
            'action',
            'action_display',
            'performed_by',
            'performed_by_name',
            'old_value',
            'new_value',
            'ip_address',
            'timestamp',
        ]
        read_only_fields = ['id', 'timestamp']


class WarrantyStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating warranty status."""
    status = serializers.ChoiceField(choices=WarrantyRegistration.WarrantyStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True)


class WarrantyCheckSerializer(serializers.Serializer):
    """Serializer for checking if an asset is registered for warranty."""
    asset_id = serializers.CharField(help_text="Asset ID to check")


class WarrantyCheckResponseSerializer(serializers.Serializer):
    """Response for warranty check."""
    is_registered = serializers.BooleanField()
    warranty_id = serializers.IntegerField(allow_null=True)
    status = serializers.CharField(allow_null=True)
    status_label = serializers.CharField(allow_null=True)
    registered_at = serializers.DateTimeField(allow_null=True)
    warranty_end_date = serializers.DateField(allow_null=True)
    is_active = serializers.BooleanField(allow_null=True)
