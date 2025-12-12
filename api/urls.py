"""
API URL Configuration for Warranty Registration System

Defines all API endpoints for:
- Warranty registration (main endpoint for Next.js app)
- Warranty management
- Reference data sync
- Authentication
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from .views import (
    RegisterWarrantyView,
    CheckWarrantyView,
    WarrantyRegistrationViewSet,
    WarrantyAuditLogViewSet,
    SyncDepartmentsView,
    SyncCategoriesView,
    SyncProfilesView,
    api_health_check,
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'warranties', WarrantyRegistrationViewSet, basename='warranty')
router.register(r'audit-logs', WarrantyAuditLogViewSet, basename='audit-log')

app_name = 'api'

urlpatterns = [
    # Health check
    path('health/', api_health_check, name='health-check'),
    
    # Main warranty registration endpoint (for Next.js app)
    path('warranty/register/', RegisterWarrantyView.as_view(), name='register-warranty'),
    
    # Check warranty status (for Next.js app)
    path('warranty/check/<str:asset_id>/', CheckWarrantyView.as_view(), name='check-warranty'),
    
    # Reference data sync endpoints (for Next.js app)
    path('sync/departments/', SyncDepartmentsView.as_view(), name='sync-departments'),
    path('sync/categories/', SyncCategoriesView.as_view(), name='sync-categories'),
    path('sync/profiles/', SyncProfilesView.as_view(), name='sync-profiles'),
    
    # JWT Authentication endpoints
    path('auth/token/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token-verify'),
    
    # Router URLs (warranties CRUD, audit logs)
    path('', include(router.urls)),
]
