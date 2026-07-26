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



from django.contrib import admin
from .models import MarketPrice, PriceAlert, MarketNews

@admin.register(MarketPrice)
class MarketPriceAdmin(admin.ModelAdmin):
    list_display = ['crop', 'market_name', 'price_per_tonne', 'recorded_date', 'source']
    list_filter = ['market_name', 'source', 'recorded_date']
    search_fields = ['crop__name', 'market_name']
    date_hierarchy = 'recorded_date'
    ordering = ['-recorded_date']

@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ['user', 'crop', 'target_price', 'condition', 'is_active', 'created_at']
    list_filter = ['condition', 'is_active', 'created_at']
    search_fields = ['user__username', 'crop__name']
    readonly_fields = ['triggered_at']

@admin.register(MarketNews)
class MarketNewsAdmin(admin.ModelAdmin):
    list_display = ['title', 'source', 'published_date', 'is_important']
    list_filter = ['is_important', 'source', 'published_date']
    search_fields = ['title', 'content']
    date_hierarchy = 'published_date'