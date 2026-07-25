from django.db import models
from django.conf import settings

class WeatherAlert(models.Model):
    """Model to store weather alerts"""
    
    SEVERITY_CHOICES = [
        ('warning', '⚠️ Warning'),
        ('watch', '👀 Watch'),
        ('advisory', '📢 Advisory'),
    ]
    
    farm = models.ForeignKey(
        'farms.Farm', 
        on_delete=models.CASCADE,
        related_name='weather_alerts',
        null=True,
        blank=True
    )
    alert_type = models.CharField(max_length=50)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    headline = models.CharField(max_length=200)
    description = models.TextField()
    instruction = models.TextField(blank=True)
    effective_date = models.DateTimeField()
    expires_date = models.DateTimeField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-effective_date']
        verbose_name = 'Weather Alert'
        verbose_name_plural = 'Weather Alerts'
    
    def __str__(self):
        return f"{self.headline} - {self.severity}"