# landing/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'landing'

urlpatterns = [
    # Landing page
    path('', views.landing_page, name='landing'),
    
    # Dashboard (protected)
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Authentication URLs (using your existing auth system)
    path('login/', auth_views.LoginView.as_view(
        template_name='authentication/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]