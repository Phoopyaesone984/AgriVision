from django.contrib import admin
from .models import Crop, HarvestPrice, YieldData, DailyMarketPrice, Profitability

@admin.register(Crop)
class CropAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'unit']
    search_fields = ['name']

@admin.register(HarvestPrice)
class HarvestPriceAdmin(admin.ModelAdmin):
    list_display = ['crop', 'year', 'price']
    list_filter = ['year', 'crop']
    search_fields = ['crop__name']

@admin.register(YieldData)
class YieldDataAdmin(admin.ModelAdmin):
    list_display = ['crop', 'year', 'yield_value', 'unit']
    list_filter = ['year', 'crop']

@admin.register(DailyMarketPrice)
class DailyMarketPriceAdmin(admin.ModelAdmin):
    list_display = ['commodity', 'category', 'price', 'unit', 'recorded_date']
    list_filter = ['category', 'recorded_date']

@admin.register(Profitability)
class ProfitabilityAdmin(admin.ModelAdmin):
    list_display = ['crop', 'year', 'profit_per_acre']
    list_filter = ['year', 'crop']