from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .services import WeatherService
from farms.models import Farm

@login_required
def weather_dashboard(request):
    """Weather dashboard view with farm switching and alerts"""
    
    # Get all farms for the user
    user_farms = Farm.objects.filter(owner=request.user)
    
    # ===== GET SELECTED FARM =====
    selected_farm_id = request.GET.get('farm_id')
    
    if selected_farm_id:
        try:
            selected_farm = user_farms.get(id=selected_farm_id)
            request.session['selected_farm_id'] = str(selected_farm_id)
        except Farm.DoesNotExist:
            selected_farm = user_farms.first()
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
    
    print("="*60)
    print(f"📍 WEATHER DASHBOARD DEBUG")
    print(f"👤 User: {request.user.username}")
    print(f"🏠 Selected Farm: {selected_farm.name if selected_farm else 'None'}")
    print(f"📍 Location: {location}")
    print("="*60)
    
    # Get weather data for SELECTED farm
    weather_service = WeatherService()
    weather_data = weather_service.get_weather_data(location)
    
    # DEBUG: Print forecast data
    print("📊 FORECAST DATA:")
    for day in weather_data.get('forecast', []):
        print(f"  {day.get('day_name')}: {day.get('condition')} - Rain: {day.get('chance_of_rain')}%")
    print("="*60)
    
    # Get weather for ALL farms AND collect alerts
    farms_weather = []
    all_alerts = []
    
    for farm in user_farms:
        farm_weather = weather_service.get_weather_data(
            farm.location if hasattr(farm, 'location') else None
        )
        
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
    
    context = {
        'weather_data': weather_data,
        'farms_weather': farms_weather,
        'user_farms': user_farms,
        'selected_farm': selected_farm,
        'all_alerts': all_alerts,
        'has_alerts': len(all_alerts) > 0,
        'current_location': location or 'Yangon',
    }
    
    return render(request, 'weather/dashboard.html', context)