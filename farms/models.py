from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.apps import apps  # Add this import

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