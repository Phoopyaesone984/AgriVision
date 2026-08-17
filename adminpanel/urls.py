from django.urls import path
from . import views

app_name = "adminpanel"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("users/<int:pk>/toggle-active/", views.toggle_user_active, name="toggle_user_active"),
    path("users/<int:pk>/posts-api/", views.get_user_posts_json, name="user_posts_api"),
    path("posts/<int:pk>/delete-api/", views.delete_post_admin, name="delete_post_admin"),
]