from django.db import models
from django.contrib.auth.models import User

class Crop(models.Model):
    """Crop master data from CSO"""
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=50, blank=True, null=True)
    unit = models.CharField(max_length=50, blank=True, null=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class HarvestPrice(models.Model):
    """Annual harvest prices from Table 4.01 (2019-2025)"""
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='harvest_prices')
    year = models.CharField(max_length=20)  # "2019-20", "2020-21", etc.
    price = models.DecimalField(max_digits=15, decimal_places=2)
    
    def __str__(self):
        return f"{self.crop.name} - {self.year}: {self.price:,}"
    
    class Meta:
        unique_together = ['crop', 'year']
        ordering = ['crop', 'year']


class YieldData(models.Model):
    """Yield per acre from Table 3.04 (2016-2025)"""
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='yields')
    year = models.CharField(max_length=20)  # "2020-21", "2024-25", etc.
    yield_value = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=50)  # 46lb(basket), Viss, etc.
    
    def __str__(self):
        return f"{self.crop.name} - {self.year}: {self.yield_value} {self.unit}"
    
    class Meta:
        unique_together = ['crop', 'year']
        ordering = ['crop', 'year']


class DailyMarketPrice(models.Model):
    """Daily market prices from CSO (Yangon July 2026)"""
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='daily_prices', null=True, blank=True)
    commodity = models.CharField(max_length=200)
    category = models.CharField(max_length=50)  # Rice, Edible Oil, Pulses, Spices
    market = models.CharField(max_length=100, default='Yangon')
    price = models.DecimalField(max_digits=15, decimal_places=2)
    unit = models.CharField(max_length=50)  # Kyat/Viss, Kyat/Pyl
    recorded_date = models.DateField()
    
    def __str__(self):
        return f"{self.commodity} - {self.recorded_date}: {self.price:,}"
    
    class Meta:
        ordering = ['-recorded_date', 'category', 'commodity']


class Profitability(models.Model):
    """Calculated profitability (Price × Yield)"""
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='profitability')
    year = models.CharField(max_length=20)
    price_per_ton = models.DecimalField(max_digits=15, decimal_places=2)
    yield_tons_per_acre = models.DecimalField(max_digits=10, decimal_places=4)
    profit_per_acre = models.DecimalField(max_digits=15, decimal_places=2)
    
    def __str__(self):
        return f"{self.crop.name} - {self.year}: {self.profit_per_acre:,.0f} MMK/acre"
    
    class Meta:
        unique_together = ['crop', 'year']
        ordering = ['-profit_per_acre']
      


  # ... existing Crop, HarvestPrice, YieldData, DailyMarketPrice, Profitability models ...

class RegionalProduction(models.Model):
    region = models.CharField(max_length=100)
    crop_category = models.CharField(max_length=100)
    year = models.CharField(max_length=20)
    sown_acres = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    harvested_acres = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    production_tons = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    measurement_type = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        ordering = ['region', 'crop_category', 'year']

    def __str__(self):
        return f"{self.region} - {self.crop_category} ({self.year})"