from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .services import WeatherService
from farms.models import Farm

@login_required
def weather_dashboard(request):
    """Weather dashboard view"""
    
    # Get user's farms - using 'owner' instead of 'user'
    user_farms = Farm.objects.filter(owner=request.user)
    
    # Get first farm location or use default
    if user_farms.exists():
        farm = user_farms.first()
        location = farm.location if hasattr(farm, 'location') else None
    else:
        location = None
    
    # Get weather data
    weather_service = WeatherService()
    weather_data = weather_service.get_weather_data(location)
    
    # Get weather for each farm (limit to 3)
    farms_weather = []
    for farm in user_farms[:3]:
        farm_weather = weather_service.get_weather_data(
            farm.location if hasattr(farm, 'location') else None
        )
        farms_weather.append({
            'farm': farm,
            'weather': farm_weather.get('current', {})
        })
    
    context = {
        'weather_data': weather_data,
        'farms_weather': farms_weather,
        'user_farms': user_farms,
        'current_location': location or 'Yangon',
    }
    
    return render(request, 'weather/dashboard.html', context)