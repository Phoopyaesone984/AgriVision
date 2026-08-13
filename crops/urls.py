from django.urls import path
from . import views

app_name = 'crops'

urlpatterns = [
    path('', views.crop_list, name='crop_list'),
    path('create/', views.crop_create, name='crop_create'),
    path('<int:pk>/', views.crop_detail, name='crop_detail'),
    path('<int:pk>/edit/', views.crop_edit, name='crop_edit'),
    path('harvest-recommendations/', views.harvest_recommendations, name='harvest_recommendations'),
    path('<int:pk>/delete/', views.crop_delete, name='crop_delete'),
]