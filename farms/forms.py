from django import forms
from .models import Farm, Activity  # Added Activity
from crops.models import Crop  # Import Crop from crops app

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

class ActivityForm(forms.ModelForm):
    """Form for creating and editing activities"""
    
    class Meta:
        model = Activity
        fields = ['farm', 'crop', 'title', 'description', 'due_date', 'priority', 'status']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter task title',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter task description',
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'farm': forms.Select(attrs={'class': 'form-control'}),
            'crop': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'farm': 'Farm',
            'crop': 'Crop (Optional)',
            'title': 'Task Title',
            'description': 'Description',
            'due_date': 'Due Date',
            'priority': 'Priority',
            'status': 'Status',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['farm'].queryset = Farm.objects.filter(owner=user)
            self.fields['crop'].queryset = Crop.objects.filter(farm__owner=user)
            self.fields['crop'].required = False