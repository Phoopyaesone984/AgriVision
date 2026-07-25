from django.contrib import admin
from .models import Crop

@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ['name', 'farm', 'crop_type', 'planting_date', 'expected_harvest_date', 'status', 'is_active']
    list_filter = ['farm', 'crop_type', 'status', 'is_active']
    search_fields = ['name', 'farm__name']
    date_hierarchy = 'planting_date'
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'farm', 'crop_type')
        }),
        ('Dates', {
            'fields': ('planting_date', 'expected_harvest_date')
        }),
        ('Details', {
            'fields': ('area_acres', 'status', 'is_active')
        }),
    )