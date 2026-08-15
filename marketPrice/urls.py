from django.urls import path
from . import views

app_name = 'marketPrice'

urlpatterns = [
    # Dashboard / Home
    path('', views.index, name='index'),
    
    # Crop views
    path('crops/', views.crop_list, name='crop_list'),
    path('crops/<int:crop_id>/', views.crop_detail, name='crop_detail'),
    
    # Daily market prices
    path('daily-prices/', views.daily_prices, name='daily_prices'),
    
    # Profitability
    path('profitability/', views.profitability, name='profitability'),
    
    # Compare crops
    path('compare/', views.compare, name='compare'),
    
    # Regional analysis - ORIGINAL URL
    path('regions/', views.regions_view, name='regions'),  # <-- CHANGED from 'regional-data/' to 'regions/'
    
    # Recommendations
    path('recommendations/', views.crop_recommendation, name='recommendations'),
    path('recommendations/<int:crop_id>/', views.crop_recommendation, name='crop_recommendation'),
     path('best-market/', views.best_market_finder, name='best_market_finder'),
    # API endpoints
    path('api/crop-prices/<int:crop_id>/', views.api_crop_prices, name='api_crop_prices'),
    path('api/daily-prices/', views.api_daily_prices, name='api_daily_prices'),
]