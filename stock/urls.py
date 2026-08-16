from django.urls import path
from . import views

app_name = "stock"

urlpatterns = [
    # Harvest stock (output side)
    path("", views.stock_list, name="stock_list"),
    path("harvest/<int:pk>/", views.harvest_stock_detail, name="harvest_detail"),
    path("harvest/<int:pk>/alert-setting/", views.update_alert_setting, name="update_alert_setting"),
    path("transaction/<int:pk>/delete/", views.delete_transaction, name="delete_transaction"),

    # Materials (input side)
    path("materials/", views.material_list, name="material_list"),
    path("materials/stock/", views.material_stock, name="material_stock"),
    path("materials/<int:pk>/", views.material_detail, name="material_detail"),
    path("materials/<int:pk>/delete/", views.delete_material, name="delete_material"),
    path("materials/purchase/<int:pk>/delete/", views.delete_purchase, name="delete_purchase"),
    path("materials/usage/<int:pk>/delete/", views.delete_usage, name="delete_usage"),
   
    path("crop/<int:pk>/plan/", views.crop_material_plan, name="crop_material_plan"),
    path("plan-item/<int:pk>/toggle-purchased/", views.toggle_item_purchased, name="toggle_item_purchased"),
    path("plan-item/<int:pk>/toggle-applied/", views.toggle_item_applied, name="toggle_item_applied"),
    path("plan-item/<int:pk>/reschedule/", views.reschedule_item, name="reschedule_item"),

    # Demand planning (learns from farmer's own historical usage)
    path("demand-planning/", views.demand_planning, name="demand_planning"),
]