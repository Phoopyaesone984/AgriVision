from django import forms

from .models import (
    StockTransaction,
    StockAlertSetting,
    Material,
    MaterialPurchase,
    MaterialUsage,
)


class StockTransactionForm(forms.ModelForm):
    class Meta:
        model = StockTransaction
        fields = ["transaction_type", "quantity_tonnes", "price_per_tonne", "buyer", "transaction_date", "notes"]
        widgets = {
            "transaction_type": forms.Select(attrs={"class": "field-select"}),
            "quantity_tonnes": forms.NumberInput(attrs={"class": "field-input", "placeholder": "e.g. 2"}),
            "price_per_tonne": forms.NumberInput(attrs={"class": "field-input", "placeholder": "Price per tonne (MMK)"}),
            "buyer": forms.TextInput(attrs={"class": "field-input", "placeholder": "Buyer name (optional)"}),
            "transaction_date": forms.DateInput(attrs={"class": "field-input", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "field-textarea", "rows": 2}),
        }

    def clean(self):
        cleaned_data = super().clean()
        ttype = cleaned_data.get("transaction_type")
        price = cleaned_data.get("price_per_tonne")
        if ttype == "sell" and not price:
            self.add_error("price_per_tonne", "Price is required for a sale.")
        return cleaned_data


class StockAlertSettingForm(forms.ModelForm):
    class Meta:
        model = StockAlertSetting
        fields = ["low_stock_threshold_tonnes"]
        widgets = {
            "low_stock_threshold_tonnes": forms.NumberInput(attrs={"class": "field-input"}),
        }


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ["name", "category", "unit", "reorder_threshold", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "field-input", "placeholder": "e.g. Urea Fertilizer"}),
            "category": forms.Select(attrs={"class": "field-select"}),
            "unit": forms.Select(attrs={"class": "field-select"}),
            "reorder_threshold": forms.NumberInput(attrs={"class": "field-input"}),
            "notes": forms.Textarea(attrs={"class": "field-textarea", "rows": 2}),
        }

class MaterialPurchaseForm(forms.ModelForm):
    class Meta:
        model = MaterialPurchase
        fields = ["quantity", "cost_per_unit", "supplier", "purchase_date", "notes"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"class": "field-input", "placeholder": "Quantity purchased"}),
            "cost_per_unit": forms.NumberInput(attrs={"class": "field-input", "placeholder": "Cost per unit (MMK)"}),
            "supplier": forms.TextInput(attrs={"class": "field-input", "placeholder": "Supplier (optional)"}),
            "purchase_date": forms.DateInput(attrs={"class": "field-input", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "field-textarea", "rows": 2, "placeholder": "Notes (optional)"}),
        }


class MaterialUsageForm(forms.ModelForm):
    class Meta:
        model = MaterialUsage
        fields = ["crop", "quantity_used", "usage_date", "notes"]
        widgets = {
            "crop": forms.Select(attrs={"class": "field-select"}),
            "quantity_used": forms.NumberInput(attrs={"class": "field-input", "placeholder": "Quantity used"}),
            "usage_date": forms.DateInput(attrs={"class": "field-input", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "field-textarea", "rows": 2, "placeholder": "Notes (optional)"}),
        }

    def __init__(self, *args, farm=None, **kwargs):
        super().__init__(*args, **kwargs)
        if farm is not None:
            self.fields["crop"].queryset = self.fields["crop"].queryset.filter(farm=farm)


class MaterialThresholdForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ["reorder_threshold"]
        widgets = {
            "reorder_threshold": forms.NumberInput(attrs={
                "class": "field-input",
                "placeholder": "e.g. 20",
            }),
        }