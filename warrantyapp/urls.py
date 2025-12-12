"""
Warranty Centre URL Configuration

URLs for the web interface where users can:
- Log in to view warranty registrations
- View list of registered assets
- See who registered each warranty
- View warranty details
- Manage warranty status
"""

from django.urls import path
from . import views

app_name = 'warrantyapp'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Warranty list and management
    path('warranties/', views.warranty_list, name='warranty_list'),
    path('warranties/<int:pk>/', views.warranty_detail, name='warranty_detail'),
    path('warranties/<int:pk>/update-status/', views.warranty_update_status, name='warranty_update_status'),
    
    # Special views
    path('expiring/', views.expiring_warranties, name='expiring_warranties'),
    path('audit-logs/', views.audit_log_list, name='audit_log_list'),
]
