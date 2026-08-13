from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.apps import apps  # Add this import
from django.contrib.auth.models import User
from decimal import Decimal
class Farm(models.Model):
    """Farm owned by a user"""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='farms')
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    size_acres = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['-created_at']


class Activity(models.Model):
    """Tasks and activities on the farm"""
    PRIORITY_CHOICES = [
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='activities')
    # Use string reference instead of importing Crop directly
    crop = models.ForeignKey('crops.Crop', on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    completed_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['due_date', '-priority']
        verbose_name_plural = 'Activities'


class SoilReading(models.Model):
    """Soil health measurements"""
    # Use string reference instead of importing Crop directly
    crop = models.ForeignKey('crops.Crop', on_delete=models.CASCADE, related_name='soil_readings')
    reading_date = models.DateTimeField(auto_now_add=True)
    moisture_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ph_level = models.DecimalField(max_digits=4, decimal_places=2, default=7.0)
    temperature_celsius = models.DecimalField(max_digits=5, decimal_places=2, default=25)
    nitrogen_ppm = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    phosphorus_ppm = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    potassium_ppm = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Soil reading - {self.crop.name} ({self.reading_date.strftime('%Y-%m-%d')})"
    
    class Meta:
        ordering = ['-reading_date']


class Harvest(models.Model):
    """Harvest records"""
    # Use string reference instead of importing Crop directly
    crop = models.ForeignKey('crops.Crop', on_delete=models.CASCADE, related_name='harvests')
    harvest_date = models.DateField()
    quantity_tonnes = models.DecimalField(max_digits=10, decimal_places=2)
    quality_grade = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Harvest: {self.crop.name} - {self.quantity_tonnes}t"
    
    class Meta:
        ordering = ['-harvest_date']

    @property
    def sold_quantity(self):
        total = self.transactions.filter(transaction_type="sell").aggregate(
            total=models.Sum("quantity_tonnes")
        )["total"]
        return total or Decimal("0")

    @property
    def used_or_wasted_quantity(self):
        total = self.transactions.filter(transaction_type__in=["use", "waste"]).aggregate(
            total=models.Sum("quantity_tonnes")
        )["total"]
        return total or Decimal("0")

    @property
    def restocked_quantity(self):
        total = self.transactions.filter(transaction_type="restock").aggregate(
            total=models.Sum("quantity_tonnes")
        )["total"]
        return total or Decimal("0")

    @property
    def remaining_stock(self):
        return self.quantity_tonnes + self.restocked_quantity - self.sold_quantity - self.used_or_wasted_quantity

    @property
    def total_revenue(self):
        total = Decimal("0")
        for t in self.transactions.filter(transaction_type="sell"):
            total += t.total_value
        return total

    @property
    def is_low_stock(self):
        setting = getattr(self, "alert_setting", None)
        if not setting or setting.low_stock_threshold_tonnes <= 0:
            return False
        return self.remaining_stock <= setting.low_stock_threshold_tonnes

# Add these models at the bottom of farms/models.py

class MarketPrice(models.Model):
    """Store crop prices from different markets"""
    
    MARKET_CHOICES = [
        ('Yangon', 'Yangon'),
        ('Mandalay', 'Mandalay'),
        ('Nay Pyi Taw', 'Nay Pyi Taw'),
        ('Mawlamyine', 'Mawlamyine'),
    ]
    
    # Use string reference to crops app (just like your Activity model does)
    crop = models.ForeignKey('crops.Crop', on_delete=models.CASCADE, related_name='market_prices')
    market_name = models.CharField(max_length=50, choices=MARKET_CHOICES)
    price_per_tonne = models.DecimalField(max_digits=12, decimal_places=2)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    recorded_date = models.DateField(auto_now_add=True)
    source = models.CharField(max_length=20, default='Manual')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-recorded_date']
    
    def __str__(self):
        return f"{self.crop.name} - {self.market_name} - {self.recorded_date}"


class PriceAlert(models.Model):
    """User-defined price alerts"""
    
    CONDITION_CHOICES = [
        ('above', 'Above'),
        ('below', 'Below'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='price_alerts')
    # Use string reference to crops app
    crop = models.ForeignKey('crops.Crop', on_delete=models.CASCADE, related_name='price_alerts')
    target_price = models.DecimalField(max_digits=12, decimal_places=2)
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES, default='above')
    is_active = models.BooleanField(default=True)
    triggered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.crop.name} - {self.condition} {self.target_price}"

class MarketNews(models.Model):
    """Agricultural market news"""
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    source = models.CharField(max_length=100)
    published_date = models.DateTimeField(auto_now_add=True)
    is_important = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-published_date']
        verbose_name_plural = "Market News"
    
    def __str__(self):
        return self.title


class UserProfile(models.Model):
    """Extended user profile for preferences"""
    
    UNIT_CHOICES = [
        ('kg', 'Per Kilogram (kg)'),
        ('tonne', 'Per Tonne (1000 kg)'),
        ('viss', 'Per Viss (1 viss = 1.63 kg)'),
        ('pyi', 'Per Pyi (1 pyi = ?)'),
        ('basket', 'Per Basket'),
    ]
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='farm_profile'
    )
    
    preferred_unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='tonne')
    preferred_currency = models.CharField(max_length=3, default='MMK')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"