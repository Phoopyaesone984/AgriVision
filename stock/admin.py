from django.contrib import admin

from .models import (
    StockTransaction,
    StockAlertSetting,
    Material,
    MaterialPurchase,
    MaterialUsage,
    DefaultCropRecipe,
    DefaultCropRecipeItem,
    CropMaterialPlan,
    CropMaterialPlanItem,
)


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("harvest", "transaction_type", "quantity_tonnes", "price_per_tonne", "transaction_date", "logged_by")
    list_filter = ("transaction_type",)
    search_fields = ("harvest__crop__name", "buyer")


admin.site.register(StockAlertSetting)
admin.site.register(Material)
admin.site.register(MaterialPurchase)
admin.site.register(MaterialUsage)


class DefaultCropRecipeItemInline(admin.TabularInline):
    model = DefaultCropRecipeItem
    extra = 1


@admin.register(DefaultCropRecipe)
class DefaultCropRecipeAdmin(admin.ModelAdmin):
    list_display = ("crop_type",)
    inlines = [DefaultCropRecipeItemInline]


class CropMaterialPlanItemInline(admin.TabularInline):
    model = CropMaterialPlanItem
    extra = 0


@admin.register(CropMaterialPlan)
class CropMaterialPlanAdmin(admin.ModelAdmin):
    list_display = ("crop", "total_estimated_cost", "created_at")
    inlines = [CropMaterialPlanItemInline]