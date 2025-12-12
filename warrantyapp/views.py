"""
Warranty Centre Views

Provides web interface for viewing and managing warranty registrations.
Users can log in and view a list of assets that have been registered 
for warranty along with the user who registered them.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta

from api.models import WarrantyRegistration, WarrantyAuditLog


def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('warrantyapp:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'warrantyapp:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'warrantyapp/login.html')


def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('warrantyapp:login')


@login_required
def dashboard(request):
    """
    Main dashboard showing warranty registration statistics.
    """
    # Get statistics
    total_registrations = WarrantyRegistration.objects.count()
    
    # Count by status
    status_counts = dict(
        WarrantyRegistration.objects
        .values('status')
        .annotate(count=Count('id'))
        .values_list('status', 'count')
    )
    
    # Expiring within 30 days
    thirty_days = timezone.now().date() + timedelta(days=30)
    expiring_soon = WarrantyRegistration.objects.filter(
        status=WarrantyRegistration.WarrantyStatus.REGISTERED,
        warranty_end_date__lte=thirty_days,
        warranty_end_date__gte=timezone.now().date()
    ).count()
    
    # Recent registrations
    recent_registrations = WarrantyRegistration.objects.order_by('-registered_at')[:5]
    
    # Registrations by department
    by_department = list(
        WarrantyRegistration.objects
        .exclude(department__isnull=True)
        .exclude(department='')
        .values('department')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    
    # Registrations by category
    by_category = list(
        WarrantyRegistration.objects
        .exclude(category__isnull=True)
        .exclude(category='')
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )
    
    context = {
        'total_registrations': total_registrations,
        'registered_count': status_counts.get('registered', 0),
        'pending_count': status_counts.get('pending', 0),
        'expired_count': status_counts.get('expired', 0),
        'claimed_count': status_counts.get('claimed', 0),
        'expiring_soon': expiring_soon,
        'recent_registrations': recent_registrations,
        'by_department': by_department,
        'by_category': by_category,
    }
    
    return render(request, 'warrantyapp/dashboard.html', context)


@login_required
def warranty_list(request):
    """
    View list of assets registered for warranty and who registered them.
    Supports filtering, searching, and pagination.
    """
    warranties = WarrantyRegistration.objects.select_related('registered_by').all()
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        warranties = warranties.filter(
            Q(asset_name__icontains=search_query) |
            Q(serial_number__icontains=search_query) |
            Q(registered_by_name__icontains=search_query) |
            Q(asset_external_id__icontains=search_query) |
            Q(department__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        warranties = warranties.filter(status=status_filter)
    
    # Filter by department
    department_filter = request.GET.get('department', '')
    if department_filter:
        warranties = warranties.filter(department=department_filter)
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        warranties = warranties.filter(category=category_filter)
    
    # Filter by date range
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if start_date:
        warranties = warranties.filter(registered_at__date__gte=start_date)
    if end_date:
        warranties = warranties.filter(registered_at__date__lte=end_date)
    
    # Ordering
    order_by = request.GET.get('order_by', '-registered_at')
    valid_orders = [
        'registered_at', '-registered_at', 
        'asset_name', '-asset_name',
        'warranty_end_date', '-warranty_end_date',
        'status', '-status'
    ]
    if order_by in valid_orders:
        warranties = warranties.order_by(order_by)
    
    # Pagination
    paginator = Paginator(warranties, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get unique departments and categories for filter dropdowns
    departments = (
        WarrantyRegistration.objects
        .exclude(department__isnull=True)
        .exclude(department='')
        .values_list('department', flat=True)
        .distinct()
        .order_by('department')
    )
    
    categories = (
        WarrantyRegistration.objects
        .exclude(category__isnull=True)
        .exclude(category='')
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'department_filter': department_filter,
        'category_filter': category_filter,
        'start_date': start_date,
        'end_date': end_date,
        'order_by': order_by,
        'departments': departments,
        'categories': categories,
        'status_choices': WarrantyRegistration.WarrantyStatus.choices,
    }
    
    return render(request, 'warrantyapp/warranty_list.html', context)


@login_required
def warranty_detail(request, pk):
    """View details of a specific warranty registration."""
    warranty = get_object_or_404(WarrantyRegistration, pk=pk)
    audit_logs = WarrantyAuditLog.objects.filter(warranty=warranty).order_by('-timestamp')[:10]
    
    context = {
        'warranty': warranty,
        'audit_logs': audit_logs,
    }
    
    return render(request, 'warrantyapp/warranty_detail.html', context)


@login_required
def warranty_update_status(request, pk):
    """Update the status of a warranty registration."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    warranty = get_object_or_404(WarrantyRegistration, pk=pk)
    new_status = request.POST.get('status')
    
    if new_status not in dict(WarrantyRegistration.WarrantyStatus.choices):
        return JsonResponse({'error': 'Invalid status'}, status=400)
    
    old_status = warranty.status
    warranty.status = new_status
    warranty.save()
    
    # Create audit log
    WarrantyAuditLog.objects.create(
        warranty=warranty,
        action=WarrantyAuditLog.ActionType.STATUS_CHANGE,
        performed_by=request.user,
        performed_by_name=request.user.get_full_name() or request.user.username,
        old_value={'status': old_status},
        new_value={'status': new_status},
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )
    
    messages.success(request, f'Status updated to {warranty.get_status_display()}')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'status': warranty.status,
            'status_display': warranty.get_status_display()
        })
    
    return redirect('warrantyapp:warranty_detail', pk=pk)


@login_required
def expiring_warranties(request):
    """View warranties expiring soon."""
    days = int(request.GET.get('days', 30))
    
    warranties = WarrantyRegistration.objects.filter(
        status=WarrantyRegistration.WarrantyStatus.REGISTERED,
        warranty_end_date__lte=timezone.now().date() + timedelta(days=days),
        warranty_end_date__gte=timezone.now().date()
    ).order_by('warranty_end_date')
    
    paginator = Paginator(warranties, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'days': days,
    }
    
    return render(request, 'warrantyapp/expiring_warranties.html', context)


@login_required
def audit_log_list(request):
    """View audit logs."""
    logs = WarrantyAuditLog.objects.select_related('warranty', 'performed_by').all()
    
    # Filter by action
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    # Filter by date
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    if start_date:
        logs = logs.filter(timestamp__date__gte=start_date)
    if end_date:
        logs = logs.filter(timestamp__date__lte=end_date)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'action_filter': action_filter,
        'start_date': start_date,
        'end_date': end_date,
        'action_choices': WarrantyAuditLog.ActionType.choices,
    }
    
    return render(request, 'warrantyapp/audit_log_list.html', context)
