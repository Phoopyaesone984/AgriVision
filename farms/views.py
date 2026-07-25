from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg
from django.utils import timezone
from .models import Farm, Crop, Activity, SoilReading
from .forms import FarmForm


# ============================================================
# DASHBOARD VIEW
# ============================================================
@login_required
def dashboard(request):
    """Main dashboard with real data from database"""
    user = request.user
    farms = Farm.objects.filter(owner=user)
    
    # ===== DEBUG: Force print to terminal =====
    print("="*60)
    print("🔍 FARMS DASHBOARD VIEW CALLED")
    print(f"👤 User: {user.username} (ID: {user.id})")
    print(f"📊 Farms found: {farms.count()}")
    for farm in farms:
        print(f"   - {farm.name} (ID: {farm.id})")
    print("="*60)
    
    # ===== CALCULATE STATISTICS =====
    total_farms = farms.count()
    total_crops = Crop.objects.filter(farm__in=farms, is_active=True).count()
    
    soil_stats = SoilReading.objects.filter(
        crop__farm__in=farms
    ).aggregate(avg_moisture=Avg('moisture_percent'))
    avg_moisture = round(soil_stats.get('avg_moisture', 0) or 0, 1)
    soil_score = int(avg_moisture) if avg_moisture else 0
    
    tomorrow = timezone.now().date() + timezone.timedelta(days=1)
    weather_alerts = Activity.objects.filter(
        farm__in=farms,
        due_date=tomorrow,
        status='pending'
    ).count()
    
    recent_activities = Activity.objects.filter(
        farm__in=farms
    ).order_by('-created_at')[:5]
    
    farm_location = farms.first().location if farms.exists() else 'Pyin Oo Lwin'
    
    # ===== BUILD CONTEXT =====
    context = {
        'stats': {
            'total_farms': total_farms,
            'active_crops': total_crops,
            'soil_score': soil_score,
            'weather_alerts': weather_alerts,
        },
        'recent_activities': recent_activities,
        'farm_location': farm_location,
        'user': user,
    }
    
    # ===== DEBUG: Print context =====
    print("📤 CONTEXT BEING SENT:")
    print(f"   total_farms: {context['stats']['total_farms']}")
    print(f"   active_crops: {context['stats']['active_crops']}")
    print(f"   soil_score: {context['stats']['soil_score']}")
    print(f"   weather_alerts: {context['stats']['weather_alerts']}")
    print(f"   farm_location: {context['farm_location']}")
    print("="*60)
    
    return render(request, 'dashboard.html', context)


# ============================================================
# FARM MANAGEMENT VIEWS
# ============================================================

@login_required
def farm_list(request):
    """Display all farms for the logged-in user"""
    farms = Farm.objects.filter(owner=request.user)
    return render(request, 'farm_list.html', {'farms': farms})


@login_required
def farm_create(request):
    """Add a new farm"""
    if request.method == 'POST':
        form = FarmForm(request.POST)
        if form.is_valid():
            farm = form.save(commit=False)
            farm.owner = request.user
            farm.save()
            messages.success(request, f'✅ Farm "{farm.name}" created successfully!')
            return redirect('farms:farm_list')
    else:
        form = FarmForm()
    
    return render(request, 'farm_form.html', {
        'form': form,
        'title': 'Add New Farm',
        'button_text': 'Create Farm',
    })


@login_required
def farm_edit(request, pk):
    """Edit an existing farm"""
    farm = get_object_or_404(Farm, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = FarmForm(request.POST, instance=farm)
        if form.is_valid():
            form.save()
            messages.success(request, f'✅ Farm "{farm.name}" updated successfully!')
            return redirect('farms:farm_list')
    else:
        form = FarmForm(instance=farm)
    
    return render(request, 'farm_form.html', {
        'form': form,
        'title': 'Edit Farm',
        'button_text': 'Update Farm',
        'farm': farm,
    })


@login_required
def farm_delete(request, pk):
    """Delete a farm"""
    farm = get_object_or_404(Farm, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        farm_name = farm.name
        farm.delete()
        messages.success(request, f'✅ Farm "{farm_name}" deleted successfully!')
        return redirect('farms:farm_list')
    
    return render(request, 'farm_confirm_delete.html', {'farm': farm})