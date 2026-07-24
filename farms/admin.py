from django.contrib import admin
from .models import Farm, Crop, Activity, SoilReading, Harvest

@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'location', 'size_acres', 'created_at']
    list_filter = ['owner']
    search_fields = ['name', 'location']
    date_hierarchy = 'created_at'

@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ['name', 'farm', 'crop_type', 'planting_date', 'status', 'is_active']
    list_filter = ['crop_type', 'status', 'farm', 'is_active']
    search_fields = ['name']
    date_hierarchy = 'planting_date'

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'farm', 'due_date', 'priority', 'status']
    list_filter = ['priority', 'status', 'farm']
    search_fields = ['title']
    date_hierarchy = 'due_date'

@admin.register(SoilReading)
class SoilReadingAdmin(admin.ModelAdmin):
    list_display = ['crop', 'reading_date', 'moisture_percent', 'ph_level']
    list_filter = ['crop__farm']
    date_hierarchy = 'reading_date'

@admin.register(Harvest)
class HarvestAdmin(admin.ModelAdmin):
    list_display = ['crop', 'harvest_date', 'quantity_tonnes']
    list_filter = ['crop__farm']
    date_hierarchy = 'harvest_date'