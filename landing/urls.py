from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'landing'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(
        template_name='login.html',
        redirect_authenticated_user=True,
        next_page='/app/'  # 👈 ADD THIS
    ), name='login'),
    path('logout/', views.logout_view, name='logout'),
]