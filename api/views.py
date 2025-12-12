"""
API Views for Warranty Registration System

Provides endpoints for:
- Registering assets for warranty (from Next.js app)
- Checking warranty status
- Listing warranty registrations
- Updating warranty status
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q, Count
from django.utils import timezone
from django.core.cache import cache

from .models import (
    WarrantyRegistration, 
    WarrantyAuditLog,
    Department,
    Category,
    Profile
)
from .serializers import (
    WarrantyRegistrationSerializer,
    WarrantyRegistrationCreateSerializer,
    WarrantyRegistrationResponseSerializer,
    WarrantyAuditLogSerializer,
    WarrantyStatusUpdateSerializer,
    WarrantyCheckSerializer,
    WarrantyCheckResponseSerializer,
    DepartmentSerializer,
    CategorySerializer,
    ProfileSerializer,
)


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def create_audit_log(warranty, action, request, old_value=None, new_value=None):
    """Create an audit log entry."""
    WarrantyAuditLog.objects.create(
        warranty=warranty,
        action=action,
        performed_by=request.user if request.user.is_authenticated else None,
        performed_by_name=getattr(request.user, 'get_full_name', lambda: '')() or str(request.user),
        old_value=old_value,
        new_value=new_value,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )


class RegisterWarrantyView(APIView):
    """
    API endpoint for registering a device for warranty.
    
    This is the main endpoint that the Next.js app calls when 
    a user clicks "Register Warranty" on an asset.
    
    POST /api/warranty/register/
    
    Request Body:
    {
        "id": "asset-uuid-from-nextjs",
        "name": "MacBook Pro 16",
        "category": "Electronics",
        "department": "IT",
        "cost": 2499.99,
        "date_purchased": "2024-01-15",
        "created_by": "user-uuid",
        "created_at": "2024-01-15T10:30:00Z",
        "registered_by_id": "user-uuid",
        "registered_by_name": "John Doe",
        "warranty_duration_months": 12,
        "serial_number": "C02XL2RJJGH5",
        "manufacturer": "Apple",
        "model_number": "A2141"
    }
    
    Response (Success):
    {
        "success": true,
        "message": "Warranty registered successfully",
        "status": "registered",
        "status_label": "Warranty Registered",
        "warranty_id": 123,
        "asset_id": "asset-uuid-from-nextjs",
        "registered_at": "2024-01-20T14:30:00Z",
        "warranty_start_date": "2024-01-20",
        "warranty_end_date": "2025-01-20"
    }
    """
    # Allow unauthenticated access for Next.js app
    # In production, use API key authentication
    permission_classes = [AllowAny]

    def post(self, request):
        """Register a new warranty for an asset."""
        serializer = WarrantyRegistrationCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Create the warranty registration
            warranty = serializer.save()
            
            # Create audit log
            create_audit_log(
                warranty=warranty,
                action=WarrantyAuditLog.ActionType.CREATE,
                request=request,
                new_value={
                    'asset_id': warranty.asset_external_id,
                    'asset_name': warranty.asset_name,
                    'status': warranty.status,
                }
            )
            
            # Return success response in format expected by Next.js
            response_data = {
                'success': True,
                'message': 'Warranty registered successfully',
                'status': warranty.status,
                'status_label': 'Warranty Registered',
                'warranty_id': warranty.id,
                'asset_id': warranty.asset_external_id,
                'registered_at': warranty.registered_at.isoformat(),
                'warranty_start_date': warranty.warranty_start_date.isoformat() if warranty.warranty_start_date else None,
                'warranty_end_date': warranty.warranty_end_date.isoformat() if warranty.warranty_end_date else None,
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Failed to register warranty: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CheckWarrantyView(APIView):
    """
    Check if an asset is registered for warranty.
    
    GET /api/warranty/check/<asset_id>/
    
    Response:
    {
        "is_registered": true,
        "warranty_id": 123,
        "status": "registered",
        "status_label": "Warranty Registered",
        "registered_at": "2024-01-20T14:30:00Z",
        "warranty_end_date": "2025-01-20",
        "is_active": true
    }
    """
    permission_classes = [AllowAny]

    def get(self, request, asset_id):
        """Check warranty status for an asset."""
        try:
            warranty = WarrantyRegistration.objects.get(asset_external_id=asset_id)
            return Response({
                'is_registered': True,
                'warranty_id': warranty.id,
                'status': warranty.status,
                'status_label': warranty.get_status_display(),
                'registered_at': warranty.registered_at.isoformat(),
                'warranty_end_date': warranty.warranty_end_date.isoformat() if warranty.warranty_end_date else None,
                'is_active': warranty.is_warranty_active,
            })
        except WarrantyRegistration.DoesNotExist:
            return Response({
                'is_registered': False,
                'warranty_id': None,
                'status': None,
                'status_label': None,
                'registered_at': None,
                'warranty_end_date': None,
                'is_active': None,
            })


class WarrantyRegistrationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing warranty registrations.
    
    Provides CRUD operations and additional actions for warranty management.
    """
    queryset = WarrantyRegistration.objects.all()
    serializer_class = WarrantyRegistrationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Apply filters to queryset."""
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by department
        department = self.request.query_params.get('department')
        if department:
            queryset = queryset.filter(department__icontains=department)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(registered_at__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(registered_at__date__lte=end_date)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(asset_name__icontains=search) |
                Q(serial_number__icontains=search) |
                Q(registered_by_name__icontains=search) |
                Q(asset_external_id__icontains=search)
            )
        
        # Filter by registered_by
        registered_by = self.request.query_params.get('registered_by')
        if registered_by:
            queryset = queryset.filter(registered_by_external_id=registered_by)
        
        # Use select_related for performance
        queryset = queryset.select_related('registered_by')
        
        return queryset

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update the status of a warranty registration."""
        warranty = self.get_object()
        serializer = WarrantyStatusUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = warranty.status
        new_status = serializer.validated_data['status']
        
        warranty.status = new_status
        if serializer.validated_data.get('notes'):
            warranty.notes = serializer.validated_data['notes']
        warranty.save()
        
        # Create audit log
        create_audit_log(
            warranty=warranty,
            action=WarrantyAuditLog.ActionType.STATUS_CHANGE,
            request=request,
            old_value={'status': old_status},
            new_value={'status': new_status}
        )
        
        return Response({
            'success': True,
            'message': f'Status updated to {warranty.get_status_display()}',
            'status': warranty.status,
            'status_label': warranty.get_status_display()
        })

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get warranty registration statistics."""
        # Try to get from cache
        cache_key = 'warranty_statistics'
        stats = cache.get(cache_key)
        
        if not stats:
            total = WarrantyRegistration.objects.count()
            by_status = dict(
                WarrantyRegistration.objects
                .values('status')
                .annotate(count=Count('id'))
                .values_list('status', 'count')
            )
            
            # Expiring soon (within 30 days)
            expiring_soon = WarrantyRegistration.objects.filter(
                status=WarrantyRegistration.WarrantyStatus.REGISTERED,
                warranty_end_date__lte=timezone.now().date() + timezone.timedelta(days=30),
                warranty_end_date__gte=timezone.now().date()
            ).count()
            
            # By department
            by_department = list(
                WarrantyRegistration.objects
                .exclude(department__isnull=True)
                .exclude(department='')
                .values('department')
                .annotate(count=Count('id'))
                .order_by('-count')[:10]
            )
            
            stats = {
                'total_registrations': total,
                'by_status': {
                    'registered': by_status.get('registered', 0),
                    'pending': by_status.get('pending', 0),
                    'expired': by_status.get('expired', 0),
                    'claimed': by_status.get('claimed', 0),
                    'void': by_status.get('void', 0),
                },
                'expiring_soon': expiring_soon,
                'by_department': by_department,
            }
            
            # Cache for 5 minutes
            cache.set(cache_key, stats, 300)
        
        return Response(stats)

    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get warranties expiring within specified days."""
        days = int(request.query_params.get('days', 30))
        
        warranties = WarrantyRegistration.objects.filter(
            status=WarrantyRegistration.WarrantyStatus.REGISTERED,
            warranty_end_date__lte=timezone.now().date() + timezone.timedelta(days=days),
            warranty_end_date__gte=timezone.now().date()
        ).order_by('warranty_end_date')
        
        serializer = self.get_serializer(warranties, many=True)
        return Response(serializer.data)


class WarrantyAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing warranty audit logs."""
    queryset = WarrantyAuditLog.objects.all()
    serializer_class = WarrantyAuditLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by warranty
        warranty_id = self.request.query_params.get('warranty_id')
        if warranty_id:
            queryset = queryset.filter(warranty_id=warranty_id)
        
        # Filter by action
        action_filter = self.request.query_params.get('action')
        if action_filter:
            queryset = queryset.filter(action=action_filter)
        
        return queryset.select_related('warranty', 'performed_by')


# API endpoints for syncing reference data from Next.js
class SyncDepartmentsView(APIView):
    """Sync departments from Next.js app."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Bulk sync departments."""
        departments = request.data.get('departments', [])
        created_count = 0
        updated_count = 0
        
        for dept_data in departments:
            dept, created = Department.objects.update_or_create(
                external_id=dept_data['id'],
                defaults={
                    'name': dept_data['name'],
                    'created_at': dept_data.get('created_at'),
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        return Response({
            'success': True,
            'created': created_count,
            'updated': updated_count
        })


class SyncCategoriesView(APIView):
    """Sync categories from Next.js app."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Bulk sync categories."""
        categories = request.data.get('categories', [])
        created_count = 0
        updated_count = 0
        
        for cat_data in categories:
            cat, created = Category.objects.update_or_create(
                external_id=cat_data['id'],
                defaults={
                    'name': cat_data['name'],
                    'created_at': cat_data.get('created_at'),
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        return Response({
            'success': True,
            'created': created_count,
            'updated': updated_count
        })


class SyncProfilesView(APIView):
    """Sync user profiles from Next.js app."""
    permission_classes = [AllowAny]

    def post(self, request):
        """Bulk sync profiles."""
        profiles = request.data.get('profiles', [])
        created_count = 0
        updated_count = 0
        
        for profile_data in profiles:
            profile, created = Profile.objects.update_or_create(
                external_id=profile_data['id'],
                defaults={
                    'full_name': profile_data['full_name'],
                    'role': profile_data.get('role'),
                    'department': profile_data.get('department'),
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        return Response({
            'success': True,
            'created': created_count,
            'updated': updated_count
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def api_health_check(request):
    """Health check endpoint."""
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'Warranty Registration API'
    })
