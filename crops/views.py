from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Crop
from .forms import CropForm
from farms.models import Farm

@login_required
def crop_list(request):
    farms = Farm.objects.filter(owner=request.user)  # Changed: user -> owner
    crops = Crop.objects.filter(farm__in=farms).select_related('farm')
    
    # Optional: Add filtering
    status_filter = request.GET.get('status')
    if status_filter:
        crops = crops.filter(status=status_filter)
    
    return render(request, 'crops/crop_list.html', {
        'crops': crops,
        'status_filter': status_filter,
    })

@login_required
def crop_create(request):
    # Check if user has any farms
    if not Farm.objects.filter(owner=request.user).exists():  # Changed: user -> owner
        messages.warning(request, 'Please create a farm first before adding crops.')
        return redirect('farms:farm_list')
    
    if request.method == 'POST':
        form = CropForm(request.POST, user=request.user)
        if form.is_valid():
            crop = form.save()
            messages.success(request, f'✅ Crop "{crop.name}" created successfully!')
            return redirect('crops:crop_list')
    else:
        form = CropForm(user=request.user)
    
    return render(request, 'crops/crop_form.html', {
        'form': form,
        'title': 'Add New Crop',
        'submit_text': 'Create Crop'
    })

@login_required
def crop_edit(request, pk):
    crop = get_object_or_404(Crop, pk=pk, farm__owner=request.user)  # Changed: farm__user -> farm__owner
    
    if request.method == 'POST':
        form = CropForm(request.POST, instance=crop, user=request.user)
        if form.is_valid():
            crop = form.save()
            messages.success(request, f'✅ Crop "{crop.name}" updated successfully!')
            return redirect('crops:crop_list')
    else:
        form = CropForm(instance=crop, user=request.user)
    
    return render(request, 'crops/crop_form.html', {
        'form': form,
        'title': 'Edit Crop',
        'submit_text': 'Update Crop',
        'crop': crop
    })

@login_required
def crop_delete(request, pk):
    crop = get_object_or_404(Crop, pk=pk, farm__owner=request.user)  # Changed: farm__user -> farm__owner
    
    if request.method == 'POST':
        crop_name = crop.name
        crop.delete()
        messages.success(request, f'🗑️ Crop "{crop_name}" deleted successfully!')
        return redirect('crops:crop_list')
    
    return render(request, 'crops/crop_confirm_delete.html', {'crop': crop})

@login_required
def crop_detail(request, pk):
    crop = get_object_or_404(Crop, pk=pk, farm__owner=request.user)  # Changed: farm__user -> farm__owner
    return render(request, 'crops/crop_detail.html', {'crop': crop})
from decimal import Decimal
from datetime import date
from django.db.models import Avg
from django.utils.translation import gettext as _  # <-- Import this!
from marketPrice.models import Crop as PriceCrop, HarvestPrice

@login_required
def harvest_recommendations(request):
    """Analyze user's crops and recommend based on historical market price trends"""
    farms = Farm.objects.filter(owner=request.user)
    user_crops = Crop.objects.filter(farm__in=farms, is_active=True).select_related('farm')
    
    # === EXACT CONVERSION CONSTANTS ===
    TON_TO_VISS = 612.4
    RETAIL_MARKUP = 3.0
    
    recommendations = []
    hold_count = 0
    sell_count = 0
    
    # Month translation lookup
    MONTH_NAMES = {
        1: _("January"), 2: _("February"), 3: _("March"), 4: _("April"),
        5: _("May"), 6: _("June"), 7: _("July"), 8: _("August"),
        9: _("September"), 10: _("October"), 11: _("November"), 12: _("December")
    }
    
    for crop in user_crops:
        try:
            price_crop = PriceCrop.objects.filter(name__icontains=crop.name).first()
            if not price_crop:
                continue
        except PriceCrop.DoesNotExist:
            continue
            
        prices = HarvestPrice.objects.filter(crop=price_crop).order_by('-year')[:3]
        
        if prices.count() < 2:
            recommendations.append({
                'crop': crop,
                'crop_name_translated': _(crop.name),  # <-- Translate crop name
                'farm_name_translated': _(crop.farm.name),  # <-- Translate farm name
                'recommendation': 'N/A',
                'current_price_viss': 0,
                'avg_price_viss': 0,
                'target_price_viss': 0,
                'best_sell_month': _("N/A"),
                'days_to_harvest': (crop.expected_harvest_date - date.today()).days,
            })
            continue
            
        price_values = [float(p.price) for p in prices]
        
        # Convert to Viss
        current_price_viss = int(price_values[0] / TON_TO_VISS)
        avg_price_viss = int((sum(price_values) / len(price_values)) / TON_TO_VISS)
        peak_price_viss = int(max(price_values) / TON_TO_VISS)
        
        # Apply 3x Retail Markup
        current_market_price = int(current_price_viss * RETAIL_MARKUP)
        peak_market_price = int(peak_price_viss * RETAIL_MARKUP)
        
        # Determine Trend
        viss_values = [p / TON_TO_VISS for p in price_values]
        
        if viss_values[0] > viss_values[1] > viss_values[2]:
            recommendation = "HOLD"
            hold_count += 1
        elif viss_values[0] < viss_values[1] < viss_values[2]:
            recommendation = "SELL"
            sell_count += 1
        elif viss_values[0] > (sum(viss_values)/len(viss_values)):
            recommendation = "HOLD"
            hold_count += 1
        elif viss_values[0] < (sum(viss_values)/len(viss_values)):
            recommendation = "SELL"
            sell_count += 1
        else:
            recommendation = "MONITOR"

        days_to_harvest = (crop.expected_harvest_date - date.today()).days
        
        # Translate the month
        harvest_month_num = crop.expected_harvest_date.month
        best_sell_month = MONTH_NAMES.get(harvest_month_num, _("Peak Season"))
        
        recommendations.append({
            'crop': crop,
            'crop_name_translated': _(crop.name),          # <-- Translated name
            'farm_name_translated': _(crop.farm.name),      # <-- Translated farm
            'recommendation': recommendation,
            'current_price_viss': current_market_price,
            'target_price_viss': peak_market_price,
            'best_sell_month': best_sell_month,             # <-- Translated month
            'days_to_harvest': days_to_harvest,
        })
    
    context = {
        'recommendations': recommendations,
        'hold_count': hold_count,
        'sell_count': sell_count,
        'page_title': _('Harvest & Price Advisor'),
    }
    return render(request, 'crops/harvest_recommendations.html', context)