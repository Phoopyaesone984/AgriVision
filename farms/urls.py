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
]