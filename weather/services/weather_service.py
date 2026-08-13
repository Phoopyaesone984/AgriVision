import requests
import logging
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from decouple import config
from urllib.parse import quote

logger = logging.getLogger(__name__)

class WeatherService:
    """Service class for fetching weather data from WeatherAPI.com"""
    
    CACHE_TIMEOUT = 3600  # 1 hour cache
    
    def __init__(self):
        self.api_key = config('WEATHER_API_KEY', default='')
        self.base_url = config('WEATHER_API_BASE_URL', default='http://api.weatherapi.com/v1')
        self.default_location = config('DEFAULT_LOCATION', default='Yangon')
        
        # Debug: Check if API key is loaded
        print(f"🔑 API Key loaded: {self.api_key[:5]}..." if self.api_key else "❌ No API Key found!")
        
    def get_weather_data(self, location=None):
        """Get current weather and 7-day forecast for a location"""
        if not location:
            location = self.default_location
            
        # Clean and encode location
        location = location.strip()
        encoded_location = quote(location)
        
        # Check cache
        cache_key = f'weather_data_{location.lower().replace(" ", "_")}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info(f"Returning cached weather data for {location}")
            return cached_data
            
        try:
            # Make API request with encoded location
            url = f"{self.base_url}/forecast.json"
            params = {
                'key': self.api_key,
                'q': encoded_location,  # Use encoded location
                'days': 7,
                'aqi': 'no',
                'alerts': 'yes'
            }
            
            logger.info(f"Fetching weather data for {location}")
            print(f"📡 Fetching weather for: {location} (encoded: {encoded_location})")
            print(f"📡 URL: {url}?key={self.api_key[:5]}...&q={encoded_location}")
            
            # Increase timeout for slower connections
            response = requests.get(url, params=params, timeout=15)
            print(f"📡 Response Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ Error Response: {response.text[:200]}")
                
            response.raise_for_status()
            
            data = response.json()
            formatted_data = self._format_weather_data(data, location)
            
            # Cache for 1 hour
            cache.set(cache_key, formatted_data, self.CACHE_TIMEOUT)
            
            print(f"✅ Weather data fetched successfully for {location}")
            return formatted_data
            
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout for {location}. Trying alternative location...")
            # Try with a simpler location name
            return self._try_alternative_location(location)
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {str(e)}")
            logger.error(f"Weather API request error: {str(e)}")
            return self._get_fallback_data(location)
            
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            logger.error(f"Weather API error: {str(e)}")
            return self._get_fallback_data(location)
    
    def _try_alternative_location(self, location):
        """Try alternative location names if the original fails"""
        # Common alternative names for locations
        alternatives = {
            'Pyin Oo Lwin': ['Pyin Oo Lwin', 'Maymyo', 'Pyinoolwin'],
            'Mandalay': ['Mandalay'],
            'Yangon': ['Yangon', 'Rangoon'],
        }
        
        # If location is in the alternatives dict, try the first alternative
        for key, alts in alternatives.items():
            if location == key and len(alts) > 1:
                for alt in alts:
                    if alt != location:
                        print(f"🔄 Trying alternative location: {alt}")
                        try:
                            url = f"{self.base_url}/forecast.json"
                            params = {
                                'key': self.api_key,
                                'q': alt,
                                'days': 7,
                                'aqi': 'no',
                                'alerts': 'yes'
                            }
                            response = requests.get(url, params=params, timeout=15)
                            if response.status_code == 200:
                                data = response.json()
                                formatted_data = self._format_weather_data(data, location)
                                print(f"✅ Success with alternative: {alt}")
                                return formatted_data
                        except:
                            continue
        
        # If all alternatives fail, use fallback
        print(f"⚠️ All alternatives failed for {location}")
        return self._get_fallback_data(location)
    
    def _format_weather_data(self, raw_data, location):
        """Format raw API response"""
        try:
            current = raw_data.get('current', {})
            location_data = raw_data.get('location', {})
            forecast = raw_data.get('forecast', {}).get('forecastday', [])
            
            # Debug: Print forecast data
            print("📊 FORECAST DATA FROM API:")
            for i, day in enumerate(forecast[:7]):
                day_data = day.get('day', {})
                condition_data = day_data.get('condition', {})
                date_obj = datetime.strptime(day.get('date', ''), '%Y-%m-%d') if day.get('date') else datetime.now()
                print(f"  {date_obj.strftime('%a')}: {condition_data.get('text', 'Unknown')} - Rain: {day_data.get('daily_chance_of_rain', 0)}%")
            
            # Current weather
            current_weather = {
                'location': location_data.get('name', location),
                'region': location_data.get('region', ''),
                'country': location_data.get('country', ''),
                'temperature': current.get('temp_c', 28),
                'feels_like': current.get('feelslike_c', 27),
                'condition': current.get('condition', {}).get('text', 'Partly cloudy'),
                'condition_icon': current.get('condition', {}).get('icon', ''),
                'humidity': current.get('humidity', 65),
                'wind_speed': current.get('wind_kph', 12),
                'uv_index': current.get('uv', 6),
                'visibility': current.get('vis_km', 10),
                'last_updated': current.get('last_updated', datetime.now().strftime('%Y-%m-%d %H:%M')),
            }
            
            # 7-day forecast
            forecast_data = []
            for day in forecast[:7]:
                day_data = day.get('day', {})
                condition_data = day_data.get('condition', {})
                date_obj = datetime.strptime(day.get('date', ''), '%Y-%m-%d') if day.get('date') else datetime.now()
                
                forecast_data.append({
                    'date': day.get('date', ''),
                    'day_name': date_obj.strftime('%a'),
                    'day_full': date_obj.strftime('%A'),
                    'max_temp': round(day_data.get('maxtemp_c', 25)),
                    'min_temp': round(day_data.get('mintemp_c', 18)),
                    'condition': condition_data.get('text', 'Clear'),
                    'condition_icon': condition_data.get('icon', ''),
                    'chance_of_rain': day_data.get('daily_chance_of_rain', 0),
                    'humidity': day_data.get('avghumidity', 60),
                })
            
            # Extract alerts
            alerts = self._extract_alerts(raw_data)
            
            return {
                'current': current_weather,
                'forecast': forecast_data,
                'alerts': alerts,
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error formatting weather data: {str(e)}")
            logger.error(f"Error formatting weather data: {str(e)}")
            return self._get_fallback_data(location)
    
    def _extract_alerts(self, raw_data):
        """Extract weather alerts"""
        alerts = []
        alert_data = raw_data.get('alerts', {}).get('alert', [])
        
        for alert in alert_data:
            alerts.append({
                'headline': alert.get('headline', 'Weather Alert'),
                'severity': alert.get('severity', 'moderate'),
                'description': alert.get('desc', ''),
                'instruction': alert.get('instruction', ''),
                'effective': alert.get('effective', ''),
                'expires': alert.get('expires', ''),
            })
            
        return alerts
    
    def _get_fallback_data(self, location):
        """Fallback data when API fails - with varied weather"""
        print(f"⚠️ Using fallback weather data for {location}")
        return {
            'current': {
                'location': location,
                'region': '',
                'country': '',
                'temperature': 28,
                'feels_like': 27,
                'condition': 'Partly cloudy',
                'condition_icon': '//cdn.weatherapi.com/weather/64x64/day/116.png',
                'humidity': 65,
                'wind_speed': 12,
                'uv_index': 6,
                'visibility': 10,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
            },
            'forecast': self._get_fallback_forecast(),
            'alerts': [],
            'success': False,
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_fallback_forecast(self):
        """Generate fallback 7-day forecast - ONLY SOME DAYS HAVE RAIN"""
        forecast = []
        conditions = ['Sunny', 'Partly cloudy', 'Cloudy', 'Clear', 'Sunny', 'Partly cloudy', 'Clear']
        rain_chances = [0, 0, 15, 0, 0, 25, 0]
        
        for i in range(7):
            date_obj = datetime.now() + timedelta(days=i)
            forecast.append({
                'date': date_obj.strftime('%Y-%m-%d'),
                'day_name': date_obj.strftime('%a'),
                'day_full': date_obj.strftime('%A'),
                'max_temp': 30 - i,
                'min_temp': 22 - i,
                'condition': conditions[i % len(conditions)],
                'condition_icon': '//cdn.weatherapi.com/weather/64x64/day/116.png',
                'chance_of_rain': rain_chances[i % len(rain_chances)],
                'humidity': 60 + i * 2,
            })
        return forecast