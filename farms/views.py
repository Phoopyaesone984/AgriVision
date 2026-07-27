from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg
from django.utils import timezone
from .models import Farm, Activity, SoilReading, MarketPrice, PriceAlert, MarketNews,UserProfile
from crops.models import Crop
from .forms import FarmForm, ActivityForm
from .services.market_price import MarketPriceService

# Import weather service
from weather.services import WeatherService


# ============================================================
# DASHBOARD VIEW
# ============================================================
@login_required
def dashboard(request):
    """Main dashboard with real data from database"""
    user = request.user
    farms = Farm.objects.filter(owner=user)
    
    # ===== GET SELECTED FARM =====
    selected_farm_id = request.GET.get('farm_id')
    
    if selected_farm_id:
        try:
            selected_farm = farms.get(id=selected_farm_id)
            request.session['dashboard_farm_id'] = str(selected_farm_id)
        except Farm.DoesNotExist:
            selected_farm = farms.first()
    else:
        session_farm_id = request.session.get('dashboard_farm_id')
        if session_farm_id:
            try:
                selected_farm = farms.get(id=int(session_farm_id))
            except Farm.DoesNotExist:
                selected_farm = farms.first()
        else:
            selected_farm = farms.first()
    
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
    
    # ===== GET WEATHER FOR SELECTED FARM =====
    if selected_farm and hasattr(selected_farm, 'location'):
        location = selected_farm.location
    else:
        location = 'Yangon'
    
    weather_service = WeatherService()
    weather_data = weather_service.get_weather_data(location)
    
    current_weather = weather_data.get('current', {})
    forecast = weather_data.get('forecast', [])[:5]
    
    # ===== BUILD CONTEXT =====
    context = {
        'stats': {
            'total_farms': total_farms,
            'active_crops': total_crops,
            'soil_score': soil_score,
            'weather_alerts': weather_alerts,
        },
        'recent_activities': recent_activities,
        'farm_location': location,
        'selected_farm': selected_farm,
        'user': user,
        'weather': current_weather,
        'forecast': forecast,
        'farms': farms,
    }
    
    return render(request, 'dashboard.html', context)


# ============================================================
# WEATHER DASHBOARD VIEW
# ============================================================
@login_required
def weather_dashboard(request):
    """Weather dashboard with farm switching and alerts"""
    user = request.user
    user_farms = Farm.objects.filter(owner=user)
    
    # ===== GET SELECTED FARM =====
    selected_farm_id = request.GET.get('farm_id')
    
    if selected_farm_id:
        try:
            selected_farm = user_farms.get(id=selected_farm_id)
            request.session['selected_farm_id'] = str(selected_farm_id)
        except Farm.DoesNotExist:
            selected_farm = user_farms.first()
            if selected_farm:
                request.session['selected_farm_id'] = str(selected_farm.id)
    else:
        session_farm_id = request.session.get('selected_farm_id')
        if session_farm_id:
            try:
                selected_farm = user_farms.get(id=int(session_farm_id))
            except Farm.DoesNotExist:
                selected_farm = user_farms.first()
        else:
            selected_farm = user_farms.first()
    
    # ===== GET LOCATION =====
    if selected_farm and hasattr(selected_farm, 'location'):
        location = selected_farm.location
    else:
        location = None
    
    # ===== GET WEATHER DATA =====
    weather_service = WeatherService()
    weather_data = weather_service.get_weather_data(location)
    
    # Get weather for ALL farms
    farms_weather = []
    all_alerts = []
    
    for farm in user_farms:
        farm_location = farm.location if hasattr(farm, 'location') else None
        farm_weather = weather_service.get_weather_data(farm_location)
        
        farm_alerts = farm_weather.get('alerts', [])
        
        farms_weather.append({
            'farm': farm,
            'weather': farm_weather.get('current', {}),
            'alerts': farm_alerts,
            'has_alerts': len(farm_alerts) > 0,
            'is_selected': farm.id == selected_farm.id if selected_farm else False,
        })
        
        if farm_alerts:
            all_alerts.extend(farm_alerts)
    
    # ===== SORT ALERTS BY SEVERITY =====
    severity_order = {'warning': 0, 'watch': 1, 'advisory': 2}
    all_alerts.sort(key=lambda x: severity_order.get(x.get('severity', 'advisory'), 3))
    all_alerts = all_alerts[:10]
    
    # ===== GET FORECAST =====
    forecast = weather_data.get('forecast', [])
    
    context = {
        'weather_data': weather_data,
        'farms_weather': farms_weather,
        'user_farms': user_farms,
        'selected_farm': selected_farm,
        'all_alerts': all_alerts,
        'has_alerts': len(all_alerts) > 0,
        'current_location': location or 'Yangon',
        'forecast': forecast,
    }
    
    return render(request, 'weather/dashboard.html', context)


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


# ============================================================
# ACTIVITY/TASK MANAGEMENT VIEWS
# ============================================================
@login_required
def activity_list(request):
    """Display all activities for the logged-in user's farms"""
    farms = Farm.objects.filter(owner=request.user)
    activities = Activity.objects.filter(farm__in=farms).select_related('farm', 'crop')
    
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    
    if status_filter:
        activities = activities.filter(status=status_filter)
    if priority_filter:
        activities = activities.filter(priority=priority_filter)
    
    return render(request, 'activity_list.html', {
        'activities': activities,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'status_choices': Activity.STATUS_CHOICES,
        'priority_choices': Activity.PRIORITY_CHOICES,
        'today': timezone.now().date(),
    })


@login_required
def activity_create(request):
    """Add a new activity"""
    if not Farm.objects.filter(owner=request.user).exists():
        messages.warning(request, 'Please create a farm first before adding tasks.')
        return redirect('farms:farm_list')
    
    if request.method == 'POST':
        form = ActivityForm(request.POST, user=request.user)
        if form.is_valid():
            activity = form.save()
            messages.success(request, f'✅ Task "{activity.title}" created successfully!')
            return redirect('farms:activity_list')
    else:
        form = ActivityForm(user=request.user)
    
    return render(request, 'activity_form.html', {
        'form': form,
        'title': 'Add New Task',
        'submit_text': 'Create Task'
    })


@login_required
def activity_edit(request, pk):
    """Edit an existing activity"""
    activity = get_object_or_404(Activity, pk=pk, farm__owner=request.user)
    
    if request.method == 'POST':
        form = ActivityForm(request.POST, instance=activity, user=request.user)
        if form.is_valid():
            activity = form.save()
            messages.success(request, f'✅ Task "{activity.title}" updated successfully!')
            return redirect('farms:activity_list')
    else:
        form = ActivityForm(instance=activity, user=request.user)
    
    return render(request, 'activity_form.html', {
        'form': form,
        'title': 'Edit Task',
        'submit_text': 'Update Task',
        'activity': activity
    })


@login_required
def activity_delete(request, pk):
    """Delete an activity"""
    activity = get_object_or_404(Activity, pk=pk, farm__owner=request.user)
    
    if request.method == 'POST':
        activity_title = activity.title
        activity.delete()
        messages.success(request, f'🗑️ Task "{activity_title}" deleted successfully!')
        return redirect('farms:activity_list')
    
    return render(request, 'activity_confirm_delete.html', {'activity': activity})


@login_required
def activity_complete(request, pk):
    """Mark an activity as completed"""
    activity = get_object_or_404(Activity, pk=pk, farm__owner=request.user)
    
    if request.method == 'POST':
        activity.status = 'completed'
        activity.completed_date = timezone.now().date()
        activity.save()
        messages.success(request, f'✅ Task "{activity.title}" marked as completed!')
        return redirect('farms:activity_list')
    
    return render(request, 'activity_complete_confirm.html', {'activity': activity})


# ============================================================
# MARKET PRICE VIEWS
# ============================================================
@login_required
@login_required
def market_prices(request):
    """Market Price Dashboard with real data"""
    
    # Get user's preferred unit
    try:
        user_profile = request.user.farm_profile
        
        # Check if user selected a unit from the dropdown
        selected_unit = request.GET.get('unit')
        if selected_unit and selected_unit in ['tonne', 'kg', 'viss', 'pyi', 'basket']:
            preferred_unit = selected_unit
            # Save to user profile for next time
            user_profile.preferred_unit = selected_unit
            user_profile.save()
        else:
            preferred_unit = user_profile.preferred_unit
            
    except UserProfile.DoesNotExist:
        preferred_unit = 'tonne'  # Default
    
    # Get all crops with prices
    crops_with_prices = Crop.objects.filter(market_prices__isnull=False).distinct()
    
    # Get latest prices for each crop
    price_data = []
    for crop in crops_with_prices:
        crop_info = {
            'crop': crop,
            'prices': []
        }
        
        # Get latest price for each market
        markets = ['Yangon', 'Mandalay', 'Nay Pyi Taw', 'Mawlamyine']
        for market in markets:
            latest = MarketPrice.objects.filter(
                crop=crop,
                market_name=market
            ).order_by('-recorded_date').first()
            
            if latest:
                # Convert price to user's preferred unit
                from .services.market_price import UnitConverter
                converted_price = UnitConverter.convert_price(
                    float(latest.price_per_tonne), 
                    'tonne', 
                    preferred_unit
                )
                
                # Calculate trend
                from .services.market_price import MarketPriceService
                trend = MarketPriceService.calculate_trend(crop.id, market)
                crop_info['prices'].append({
                    'market': market,
                    'price': latest,
                    'converted_price': converted_price,
                    'unit': preferred_unit,
                    'trend': trend
                })
        
        if crop_info['prices']:
            price_data.append(crop_info)
    
    # Get recent news
    recent_news = MarketNews.objects.all()[:5]
    
    # Get user alerts
    user_alerts = PriceAlert.objects.filter(user=request.user, is_active=True)
    
    # Get all available units for the dropdown
    from .services.market_price import UnitConverter
    all_units = UnitConverter.UNIT_NAMES
    unit_symbol = UnitConverter.get_unit_symbol(preferred_unit)
    
    context = {
        'title': 'Market Prices',
        'page_title': 'Market Price Dashboard',
        'price_data': price_data,
        'recent_news': recent_news,
        'user_alerts': user_alerts,
        'markets': ['Yangon', 'Mandalay', 'Nay Pyi Taw', 'Mawlamyine'],
        'preferred_unit': preferred_unit,
        'all_units': all_units,
        'unit_symbol': unit_symbol,
    }
    
    return render(request, 'farms/market_prices.html', context)
@login_required
def price_alert_create(request):
    """Create a price alert (placeholder)"""
    messages.info(request, 'Price alert feature coming soon!')
    return redirect('farms:market_prices')