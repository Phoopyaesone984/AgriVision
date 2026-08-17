from django.urls import path
from . import views

app_name = "community"

urlpatterns = [
    path("", views.feed, name="feed"),
    path("post/<int:pk>/", views.post_detail, name="post_detail"),
    path("post/<int:pk>/comment/", views.add_comment, name="add_comment"),
    path("post/<int:pk>/delete/", views.delete_post, name="delete_post"),
    path("post/<int:pk>/report/", views.report_post, name="report_post"),
    path("like/<str:model_name>/<int:pk>/", views.toggle_like, name="toggle_like"),

    path("notifications/", views.notifications_dropdown, name="notifications_dropdown"),
    path("notifications/read-all/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
    path("notifications/<int:pk>/go/", views.notification_redirect, name="notification_redirect"),
]