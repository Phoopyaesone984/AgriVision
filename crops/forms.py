from django import forms
from .models import Crop
from farms.models import Farm
from marketPrice.models import Crop as PriceCrop  # Import the Price Crop model

class CropForm(forms.ModelForm):
    class Meta:
        model = Crop
        fields = ['farm', 'name', 'crop_type', 'planting_date', 'expected_harvest_date', 'area_acres', 'status', 'is_active']
        widgets = {
            'planting_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_harvest_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 1. Filter farms to only the user's farms
        if user:
            self.fields['farm'].queryset = Farm.objects.filter(owner=user)
        
        # 2. REPLACE the name text input with a dropdown of existing Market Crops
        # This ensures the user can ONLY select crops that have price data.
        self.fields['name'] = forms.ModelChoiceField(
            queryset=PriceCrop.objects.all().order_by('name'),
            empty_label="Select a Crop (Must exist in Price Data)",
            widget=forms.Select(attrs={'class': 'form-select'}),
            label="Crop Name"
        )

    def clean(self):
        cleaned_data = super().clean()
        farm = cleaned_data.get("farm")
        name = cleaned_data.get("name")
        
        # 3. Prevent Duplicates: Ensure this crop isn't already planted on this farm
        if farm and name:
            if Crop.objects.filter(farm=farm, name=name).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(f"A crop named '{name}' is already planted on this farm.")
        
        return cleaned_data