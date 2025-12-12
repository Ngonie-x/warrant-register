"""
API Models for Warranty Registration System

This module defines the data models that store warranty registration information
received from the Next.js application.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Department(models.Model):
    """
    Mirror of the departments table in Next.js app.
    Stores department information for reference.
    """
    external_id = models.CharField(
        max_length=255, 
        unique=True, 
        db_index=True,
        help_text="ID from the Next.js application"
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_departments'
        ordering = ['name']
        indexes = [
            models.Index(fields=['external_id']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class Category(models.Model):
    """
    Mirror of the categories table in Next.js app.
    Stores category information for reference.
    """
    external_id = models.CharField(
        max_length=255, 
        unique=True, 
        db_index=True,
        help_text="ID from the Next.js application"
    )
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_categories'
        verbose_name_plural = 'Categories'
        ordering = ['name']
        indexes = [
            models.Index(fields=['external_id']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name


class Profile(models.Model):
    """
    Mirror of the profiles table in Next.js app.
    Stores user profile information from the external system.
    """
    external_id = models.CharField(
        max_length=255, 
        unique=True, 
        db_index=True,
        help_text="ID from the Next.js application"
    )
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'api_profiles'
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['external_id']),
            models.Index(fields=['full_name']),
            models.Index(fields=['department']),
        ]

    def __str__(self):
        return self.full_name


class WarrantyRegistration(models.Model):
    """
    Main model for storing warranty registrations.
    Receives asset data from the Next.js application when 
    a user clicks "Register Warranty".
    """
    
    class WarrantyStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        REGISTERED = 'registered', 'Warranty Registered'
        EXPIRED = 'expired', 'Warranty Expired'
        CLAIMED = 'claimed', 'Warranty Claimed'
        VOID = 'void', 'Void'
    
    # Asset information from Next.js app
    asset_external_id = models.CharField(
        max_length=255, 
        unique=True, 
        db_index=True,
        help_text="Asset ID from the Next.js application"
    )
    asset_name = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=255, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    cost = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    date_purchased = models.DateField(null=True, blank=True)
    
    # Who created the asset in the Next.js app
    asset_created_by = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="User ID who created the asset in Next.js app"
    )
    asset_created_at = models.DateTimeField(null=True, blank=True)
    
    # Warranty registration details
    status = models.CharField(
        max_length=20,
        choices=WarrantyStatus.choices,
        default=WarrantyStatus.REGISTERED,
        db_index=True
    )
    registered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='warranty_registrations',
        help_text="Django user who registered the warranty"
    )
    registered_by_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        help_text="Name of user who registered (from Next.js app)"
    )
    registered_by_external_id = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        db_index=True,
        help_text="User ID from Next.js app who registered"
    )
    
    # Timestamps
    registered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Warranty period
    warranty_start_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Warranty start date (defaults to registration date)"
    )
    warranty_end_date = models.DateField(
        null=True, 
        blank=True,
        help_text="Warranty expiration date"
    )
    warranty_duration_months = models.PositiveIntegerField(
        default=12,
        help_text="Warranty duration in months"
    )
    
    # Additional metadata
    notes = models.TextField(blank=True, null=True)
    serial_number = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        db_index=True
    )
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    model_number = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'api_warranty_registrations'
        ordering = ['-registered_at']
        verbose_name = 'Warranty Registration'
        verbose_name_plural = 'Warranty Registrations'
        indexes = [
            # Composite indexes for common queries
            models.Index(fields=['status', 'registered_at']),
            models.Index(fields=['department', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['registered_by_external_id', 'registered_at']),
            # Individual indexes
            models.Index(fields=['asset_external_id']),
            models.Index(fields=['asset_name']),
            models.Index(fields=['registered_at']),
            models.Index(fields=['warranty_end_date']),
        ]

    def __str__(self):
        return f"{self.asset_name} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        """Set warranty dates if not provided."""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        if not self.warranty_start_date:
            self.warranty_start_date = timezone.now().date()
        
        if not self.warranty_end_date and self.warranty_start_date:
            try:
                self.warranty_end_date = self.warranty_start_date + relativedelta(
                    months=self.warranty_duration_months
                )
            except ImportError:
                # Fallback if dateutil not installed
                self.warranty_end_date = self.warranty_start_date + timedelta(
                    days=self.warranty_duration_months * 30
                )
        
        super().save(*args, **kwargs)

    @property
    def is_warranty_active(self):
        """Check if warranty is still active."""
        if self.warranty_end_date:
            return timezone.now().date() <= self.warranty_end_date
        return True

    @property
    def days_until_expiry(self):
        """Calculate days until warranty expires."""
        if self.warranty_end_date:
            delta = self.warranty_end_date - timezone.now().date()
            return delta.days
        return None


class WarrantyAuditLog(models.Model):
    """
    Audit log for tracking changes to warranty registrations.
    Useful for compliance and debugging.
    """
    
    class ActionType(models.TextChoices):
        CREATE = 'create', 'Created'
        UPDATE = 'update', 'Updated'
        STATUS_CHANGE = 'status_change', 'Status Changed'
        DELETE = 'delete', 'Deleted'
    
    warranty = models.ForeignKey(
        WarrantyRegistration,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=20, choices=ActionType.choices)
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    performed_by_name = models.CharField(max_length=255, blank=True, null=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'api_warranty_audit_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['warranty', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} - {self.warranty.asset_name} at {self.timestamp}"
