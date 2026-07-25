from django.contrib import admin
from .models import Farm, Activity, SoilReading, Harvest
# Remove Crop from import - it's now in crops app

@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'location', 'size_acres', 'created_at']
    list_filter = ['owner']
    search_fields = ['name', 'location']

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['title', 'farm', 'crop', 'due_date', 'priority', 'status']
    list_filter = ['priority', 'status', 'farm']
    search_fields = ['title', 'description']

@admin.register(SoilReading)
class SoilReadingAdmin(admin.ModelAdmin):
    list_display = ['crop', 'reading_date', 'moisture_percent', 'ph_level']
    list_filter = ['crop']
    search_fields = ['crop__name', 'notes']

@admin.register(Harvest)
class HarvestAdmin(admin.ModelAdmin):
    list_display = ['crop', 'harvest_date', 'quantity_tonnes', 'quality_grade']
    list_filter = ['crop']
    search_fields = ['crop__name', 'quality_grade']