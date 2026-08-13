from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from crops.models import Crop


# ============================================================
# OUTPUT SIDE — what happens to harvested crop (sell/use/waste)
# ============================================================

class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ("sell", "Sold"),
        ("use", "Used / Consumed"),
        ("waste", "Waste / Spoilage"),
        ("restock", "Restock / Correction"),
    ]

    harvest = models.ForeignKey("farms.Harvest", on_delete=models.CASCADE, related_name="transactions")
    logged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stock_transactions")
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    quantity_tonnes = models.IntegerField()
    price_per_tonne = models.IntegerField(
        null=True, blank=True,
        help_text="Only used for 'Sold' transactions"
    )
    buyer = models.CharField(max_length=150, blank=True)
    transaction_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-transaction_date", "-created_at"]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.harvest.crop.name} - {self.quantity_tonnes}t"

    @property
    def total_value(self):
        if self.transaction_type == "sell" and self.price_per_tonne:
            return self.quantity_tonnes * self.price_per_tonne
        return 0


class StockAlertSetting(models.Model):
    harvest = models.OneToOneField("farms.Harvest", on_delete=models.CASCADE, related_name="alert_setting")
    low_stock_threshold_tonnes = models.IntegerField(default=0)

    def __str__(self):
        return f"Alert setting for {self.harvest}"


# ============================================================
# INPUT SIDE — materials farmer buys/uses to grow crops
# ============================================================

class Material(models.Model):
    CATEGORY_CHOICES = [
        ("seed", "Seed"),
        ("fertilizer", "Fertilizer"),
        ("pesticide", "Pesticide/Herbicide"),
        ("feed", "Animal Feed"),
        ("labor", "Labor"),
        ("other", "Other"),
    ]
    UNIT_CHOICES = [
        ("kg", "Kilogram"),
        ("g", "Gram"),
        ("l", "Liter"),
        ("bag", "Bag"),
        ("packet", "Packet"),
        ("unit", "Unit"),
        ("tree", "Tree"),
        ("person_day", "Person-Day"),
    ]

    farm = models.ForeignKey("farms.Farm", on_delete=models.CASCADE, related_name="materials")
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="other")
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="kg")
    reorder_threshold = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.farm.name})"

    @property
    def total_purchased(self):
        total = self.purchases.aggregate(total=models.Sum("quantity"))["total"]
        return total or 0

    @property
    def total_used(self):
        total = self.usages.aggregate(total=models.Sum("quantity_used"))["total"]
        return total or 0

    @property
    def quantity_on_hand(self):
        return self.total_purchased - self.total_used

    @property
    def latest_cost_per_unit(self):
        last_purchase = self.purchases.order_by("-purchase_date", "-created_at").first()
        return last_purchase.cost_per_unit if last_purchase else 0

    @property
    def is_low_stock(self):
        if self.reorder_threshold <= 0:
            return False
        return self.quantity_on_hand <= self.reorder_threshold


class MaterialPurchase(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="purchases")
    logged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="material_purchases")
    quantity = models.IntegerField()
    cost_per_unit = models.IntegerField()
    supplier = models.CharField(max_length=150, blank=True)
    purchase_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-purchase_date", "-created_at"]

    def __str__(self):
        return f"Purchase: {self.quantity} {self.material.unit} of {self.material.name}"

    @property
    def total_cost(self):
        return self.quantity * self.cost_per_unit


class MaterialUsage(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="usages")
    crop = models.ForeignKey("crops.Crop", on_delete=models.CASCADE, related_name="material_usages")
    logged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="material_usages_logged")
    quantity_used = models.IntegerField()
    unit_cost = models.IntegerField(
        null=True, blank=True,
        help_text="Cost per unit at time of use; auto-filled from material's latest purchase if left blank."
    )
    usage_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-usage_date", "-created_at"]

    def save(self, *args, **kwargs):
        if self.unit_cost is None:
            self.unit_cost = self.material.latest_cost_per_unit
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity_used} {self.material.unit} of {self.material.name} used on {self.crop.name}"

    @property
    def total_cost(self):
        return self.quantity_used * (self.unit_cost or 0)


# ============================================================
# ADMIN-MANAGED DEFAULT RECIPES — one per crop type, shared by everyone
# ============================================================

class DefaultCropRecipe(models.Model):
    crop_type = models.CharField(max_length=20, choices=Crop.CROP_TYPE_CHOICES, unique=True)

    class Meta:
        ordering = ["crop_type"]

    def __str__(self):
        return self.get_crop_type_display()


class DefaultCropRecipeItem(models.Model):
    recipe = models.ForeignKey(DefaultCropRecipe, on_delete=models.CASCADE, related_name="items")
    material_name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=Material.CATEGORY_CHOICES, default="other")
    unit = models.CharField(max_length=10, choices=Material.UNIT_CHOICES, default="kg")
    quantity_per_acre = models.IntegerField()
    days_after_planting = models.IntegerField(default=0, help_text="When to apply this, counted from planting date")
    default_unit_cost = models.IntegerField(
        default=0,
        help_text="Fallback estimated cost per unit (MMK), used until the farmer has actually purchased this material"
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["days_after_planting", "category"]

    def __str__(self):
        return f"{self.material_name} - {self.quantity_per_acre}/acre - Day {self.days_after_planting}"


# ============================================================
# PER-CROP MATERIAL PLAN — generated once from DefaultCropRecipe,
# then tracked/updated independently as the farmer works.
# ============================================================

class CropMaterialPlan(models.Model):
    crop = models.OneToOneField("crops.Crop", on_delete=models.CASCADE, related_name="material_plan")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Material Plan - {self.crop.name}"

    @property
    def total_estimated_cost(self):
        return sum((i.estimated_cost for i in self.items.all()), 0)

class CropMaterialPlanItem(models.Model):
    plan = models.ForeignKey(CropMaterialPlan, on_delete=models.CASCADE, related_name="items")
    material_name = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=Material.CATEGORY_CHOICES, default="other")
    unit = models.CharField(max_length=10, choices=Material.UNIT_CHOICES, default="kg")
    quantity = models.IntegerField()  # planned quantity
    actual_quantity = models.IntegerField(null=True, blank=True)  # what was really used
    material_usage = models.ForeignKey(
        "MaterialUsage", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="plan_item"
    )
    unit_cost = models.IntegerField(default=0)
    days_after_planting = models.IntegerField(default=0)
    is_purchased = models.BooleanField(default=False)
    is_applied = models.BooleanField(default=False)
    applied_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["days_after_planting", "category"]

    def __str__(self):
        return f"{self.material_name} ({self.plan.crop.name})"

    @property
    def estimated_cost(self):
        return self.quantity * self.unit_cost

    @property
    def scheduled_date(self):
        return self.plan.crop.planting_date + timedelta(days=self.days_after_planting)

    @property
    def quantity_difference(self):
        if self.actual_quantity is None:
            return None
        return self.actual_quantity - self.quantity

    @property
    def status(self):
        material = Material.objects.filter(
            farm=self.plan.crop.farm, name__iexact=self.material_name
        ).first()
        if material and material.quantity_on_hand >= self.quantity:
            return "in_stock"
        if self.is_purchased:
            return "purchased"
        return "pending"