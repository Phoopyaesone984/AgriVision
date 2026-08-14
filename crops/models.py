from django.db import models
from django.urls import reverse
from decimal import Decimal
# Don't import Farm directly - use string reference

class Crop(models.Model):
    CROP_TYPE_CHOICES = [
        ('CORN', 'Corn'),
        ('WHEAT', 'Wheat'),
        ('SOYBEAN', 'Soybean'),
        ('RICE', 'Rice'),
        ('COTTON', 'Cotton'),
        ('VEGETABLE', 'Vegetable'),
        ('FRUIT', 'Fruit'),
        ('OTHER', 'Other'),
    ]
    
    CROP_STATUS_CHOICES = [
        ('PLANNED', 'Planned'),
        ('PLANTED', 'Planted'),
        ('GROWING', 'Growing'),
        ('HARVESTED', 'Harvested'),
        ('FAILED', 'Failed'),
    ]
    
    # Use string reference to avoid circular import
    farm = models.ForeignKey('farms.Farm', on_delete=models.CASCADE, related_name='crops')
    name = models.CharField(max_length=100)
    crop_type = models.CharField(max_length=20, choices=CROP_TYPE_CHOICES)
    planting_date = models.DateField()
    expected_harvest_date = models.DateField()
    area_acres = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=CROP_STATUS_CHOICES, default='PLANNED')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-planting_date']
    
    def __str__(self):
        return f"{self.name} ({self.farm.name})"
    
    def get_absolute_url(self):
        return reverse('crops:crop_detail', kwargs={'pk': self.pk})

    @property
    def total_material_cost(self):
        return sum((u.total_cost for u in self.material_usages.all()), Decimal("0"))

    @property
    def total_harvest_revenue(self):
        return sum((h.total_revenue for h in self.harvests.all()), Decimal("0"))

    @property
    def net_profit(self):
        return self.total_harvest_revenue - self.total_material_cost