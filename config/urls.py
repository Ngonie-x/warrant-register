"""
URL Configuration for Warranty Registration System

Routes:
- /api/         - REST API endpoints (warranty registration, management)
- /warranty/    - Warranty Centre web interface
- /admin/       - Django admin interface
"""

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def home_redirect(request):
    """Redirect home to warranty centre."""
    return redirect('warrantyapp:dashboard')

urlpatterns = [
    path('', home_redirect, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls', namespace='api')),
    path('warranty/', include('warrantyapp.urls', namespace='warrantyapp')),
]
