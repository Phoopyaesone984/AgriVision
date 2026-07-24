from django import forms
from .models import Farm

class FarmForm(forms.ModelForm):
    """Form for creating and editing farms"""
    
    class Meta:
        model = Farm
        fields = ['name', 'location', 'size_acres']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter farm name',
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter farm location',
            }),
            'size_acres': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter size in acres',
                'step': '0.01',
                'min': '0',
            }),
        }
        labels = {
            'name': 'Farm Name',
            'location': 'Location',
            'size_acres': 'Size (Acres)',
        }