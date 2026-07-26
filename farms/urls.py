from django.urls import path
from . import views

app_name = 'farms'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Farm Management
    path('farms/', views.farm_list, name='farm_list'),
    path('farms/add/', views.farm_create, name='farm_create'),
    path('farms/<int:pk>/edit/', views.farm_edit, name='farm_edit'),
    path('farms/<int:pk>/delete/', views.farm_delete, name='farm_delete'),
    
    # Activity/Task Management - ADD THESE NEW URLS
    path('activities/', views.activity_list, name='activity_list'),
    path('activities/add/', views.activity_create, name='activity_create'),
    path('activities/<int:pk>/edit/', views.activity_edit, name='activity_edit'),
    path('activities/<int:pk>/delete/', views.activity_delete, name='activity_delete'),
    path('activities/<int:pk>/complete/', views.activity_complete, name='activity_complete'),
     path('price-alert/create/', views.price_alert_create, name='price_alert_create'),
     path('market-prices/', views.market_prices, name='market_prices'),
]