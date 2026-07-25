from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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

class Crop(models.Model):
    """Crops planted on a farm"""
    CROP_TYPES = [
        ('rice', 'Rice'),
        ('corn', 'Corn'),
        ('wheat', 'Wheat'),
        ('coffee', 'Coffee'),
        ('vegetable', 'Vegetable'),
        ('fruit', 'Fruit'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('planted', 'Planted'),
        ('growing', 'Growing'),
        ('harvesting', 'Harvesting'),
        ('completed', 'Completed'),
    ]
    
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='crops')
    name = models.CharField(max_length=100)
    crop_type = models.CharField(max_length=20, choices=CROP_TYPES, default='other')
    planting_date = models.DateField()
    expected_harvest_date = models.DateField(null=True, blank=True)
    area_acres = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planted')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.farm.name})"
    
    class Meta:
        ordering = ['-planting_date']

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
    crop = models.ForeignKey(Crop, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities')
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
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='soil_readings')
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
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='harvests')
    harvest_date = models.DateField()
    quantity_tonnes = models.DecimalField(max_digits=10, decimal_places=2)
    quality_grade = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Harvest: {self.crop.name} - {self.quantity_tonnes}t"
    
    class Meta:
        ordering = ['-harvest_date']