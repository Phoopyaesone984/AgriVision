from django import forms
from .models import Crop
from farms.models import Farm  

class CropForm(forms.ModelForm):
    class Meta:
        model = Crop
        fields = ['farm', 'name', 'crop_type', 'planting_date', 'expected_harvest_date', 'area_acres', 'status', 'is_active']
        widgets = {
            'planting_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expected_harvest_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'area_acres': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'farm': forms.Select(attrs={'class': 'form-control'}),
            'crop_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['farm'].queryset = Farm.objects.filter(owner=user)  # Changed: user -> owner