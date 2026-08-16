from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Crop
from .forms import CropForm
from farms.models import Farm
from decimal import Decimal
from datetime import date, datetime
from django.db.models import Avg
from django.utils.translation import gettext as _
from marketPrice.models import Crop as PriceCrop, HarvestPrice


@login_required
def crop_list(request):
    farms = Farm.objects.filter(owner=request.user)
    crops = Crop.objects.filter(farm__in=farms).select_related('farm')

    status_filter = request.GET.get('status')
    if status_filter:
        crops = crops.filter(status=status_filter)

    return render(request, 'crops/crop_list.html', {
        'crops': crops,
        'status_filter': status_filter,
    })


@login_required
def crop_create(request):
    if not Farm.objects.filter(owner=request.user).exists():
        messages.warning(request, 'Please create a farm first before adding crops.')
        return redirect('farms:farm_list')

    if request.method == 'POST':
        form = CropForm(request.POST, user=request.user)
        if form.is_valid():
            crop = form.save()
            messages.success(request, f'✅ Crop "{crop.name}" created successfully!')

            # 🔄 Crop List သို့ မသွားတော့ဘဲ Material Plan Page သို့ တိုက်ရိုက် Redirect လုပ်မည်

            return redirect('stock:crop_material_plan', pk=crop.pk)
    else:
        form = CropForm(user=request.user)

    return render(request, 'crops/crop_form.html', {
        'form': form,
        'title': 'Add New Crop',
        'submit_text': 'Create Crop'
    })


@login_required
def crop_edit(request, pk):
    crop = get_object_or_404(Crop, pk=pk, farm__owner=request.user)

    old_status = crop.status  # capture BEFORE the form binds/validates new POST data


    if request.method == 'POST':
        old_status = crop.status
        form = CropForm(request.POST, instance=crop, user=request.user)
        if form.is_valid():
            crop = form.save()
            messages.success(request, f'✅ Crop "{crop.name}" updated successfully!')


            if old_status != 'HARVESTED' and crop.status == 'HARVESTED':
                messages.info(request, 'Now log your actual harvest results below.')
                return redirect('farms:harvest_create', crop_pk=crop.pk)

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
    crop = get_object_or_404(Crop, pk=pk, farm__owner=request.user)

    if request.method == 'POST':
        crop_name = crop.name
        crop.delete()
        messages.success(request, f'🗑️ Crop "{crop_name}" deleted successfully!')
        return redirect('crops:crop_list')

    return render(request, 'crops/crop_confirm_delete.html', {'crop': crop})


@login_required
def crop_detail(request, pk):

    crop = get_object_or_404(Crop, pk=pk, farm__owner=request.user)
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
    RETAIL_MARKUP = 1.2
    
    recommendations = []
    hold_count = 0
    sell_count = 0
    monitor_count = 0
    
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
                'crop_name_translated': _(crop.name),
                'farm_name_translated': _(crop.farm.name),
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
        min_price_viss = int(min(price_values) / TON_TO_VISS)
        
        # Apply 3x Retail Markup for market price display
        current_market_price = int(current_price_viss * RETAIL_MARKUP)
        peak_market_price = int(peak_price_viss * RETAIL_MARKUP)
        avg_market_price = int(avg_price_viss * RETAIL_MARKUP)
        
        # Determine Trend - FIXED LOGIC
        viss_values = [p / TON_TO_VISS for p in price_values]
        
        # FIXED: Prices increasing = HOLD, Prices decreasing = SELL
        if viss_values[0] < viss_values[1] < viss_values[2]:
            # Price is increasing over 3 years
            recommendation = "HOLD"
            hold_count += 1
        elif viss_values[0] > viss_values[1] > viss_values[2]:
            # Price is decreasing over 3 years
            recommendation = "SELL"
            sell_count += 1
        elif current_price_viss > avg_price_viss:
            # Current price is above average - HOLD for better price
            recommendation = "HOLD"
            hold_count += 1
        elif current_price_viss < avg_price_viss:
            # Current price is below average - SELL before it drops more
            recommendation = "SELL"
            sell_count += 1
        else:
            recommendation = "MONITOR"
            monitor_count += 1

        days_to_harvest = (crop.expected_harvest_date - date.today()).days
        
        # Translate the month
        harvest_month_num = crop.expected_harvest_date.month
        best_sell_month = MONTH_NAMES.get(harvest_month_num, _("Peak Season"))
        
        recommendations.append({
            'crop': crop,
            'crop_name_translated': _(crop.name),
            'farm_name_translated': _(crop.farm.name),
            'recommendation': recommendation,
            'current_price_viss': current_market_price,
            'avg_price_viss': avg_market_price,
            'target_price_viss': peak_market_price,
            'best_sell_month': best_sell_month,
            'days_to_harvest': days_to_harvest,
            'price_trend': 'up' if recommendation == 'HOLD' else 'down' if recommendation == 'SELL' else 'stable',
        })
    
    context = {
        'recommendations': recommendations,
        'hold_count': hold_count,
        'sell_count': sell_count,
        'monitor_count': monitor_count,
        'page_title': _('Harvest & Price Advisor'),
        'now': datetime.now(),  # FIXED: Added now for template
    }
    return render(request, 'crops/harvest_recommendations.html', context)


@login_required
def crop_growth_advisor(request):
    """Display crops with actionable advice based on planting vs harvest dates."""
    farms = Farm.objects.filter(owner=request.user)
    crops = Crop.objects.filter(farm__in=farms, is_active=True).select_related('farm')
    
    advisor_data = []
    
    for crop in crops:
        days_since_planting = (date.today() - crop.planting_date).days
        days_to_harvest = (crop.expected_harvest_date - date.today()).days
        
        # Determine Stage and Advice
        if days_to_harvest < 0:
            stage = "danger"
            stage_label = _("Past Harvest Date")
            advice = _("Harvest date has passed. Check crop condition immediately.")
            
        elif days_to_harvest <= 14:
            stage = "success"
            stage_label = _("Ready to Harvest")
            advice = _("Stop watering 2 weeks before harvest to improve quality. Prepare your harvesting tools.")
            
        elif days_since_planting <= 7:
            stage = "info"
            stage_label = _("Just Planted")
            advice = _("Ensure consistent moisture for germination. Watch for pests.")
            
        else:
            stage = "warning"
            stage_label = _("Active Growing")
            advice = _("Apply fertilizer based on growth stage. Monitor for pests. Ensure adequate irrigation.")

        advisor_data.append({
            'crop': crop,
            'crop_name_translated': _(crop.name),
            'farm_name_translated': _(crop.farm.name),
            'stage_label': stage_label,
            'advice': advice,
            'stage_color': stage,
            'days_to_harvest': days_to_harvest,
            'planting_date': crop.planting_date,
            'harvest_date': crop.expected_harvest_date,
        })
    
    context = {
        'advisor_data': advisor_data,
        'page_title': _('Growth Advisor'),
        'now': datetime.now(),  # Added for consistency
    }
    return render(request, 'crops/crop_growth_advisor.html', context)

# crops/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum
from django.utils.translation import gettext as _
from marketPrice.models import Crop as PriceCrop, HarvestPrice, RegionalProduction, Profitability
from farms.models import Farm
from datetime import datetime
from decimal import Decimal

@login_required
def crop_planting_advisor(request):
    """
    Recommend which crops to plant based on:
    - Regional production trends
    - Price history
    - Profitability
    - Seasonality
    """
    
    # Get user's farms
    user_farms = Farm.objects.filter(owner=request.user)
    
    # Get unique farm locations (deduplicated)
    user_farm_locations = list(user_farms.values_list('location', flat=True).distinct())
    
    # Get selected location from request
    selected_location = request.GET.get('location')
    
    # Determine which locations to check
    if selected_location and selected_location != 'all':
        locations_to_check = [selected_location]
    elif user_farm_locations:
        # Use the user's farm locations
        locations_to_check = user_farm_locations
    else:
        # If no farms, check all regions
        locations_to_check = None
    
    # Get all market crops
    market_crops = PriceCrop.objects.all()
    
    recommendations = []
    
    for crop in market_crops:
        try:
            # 1. Get price data
            prices = HarvestPrice.objects.filter(crop=crop).order_by('-year')
            if prices.count() < 2:
                continue
            
            # Get latest price
            latest_price_obj = prices.first()
            if not latest_price_obj:
                continue
            latest_price = float(latest_price_obj.price)
            
            # Get all prices for average
            all_prices = [float(p.price) for p in prices]
            avg_price = sum(all_prices) / len(all_prices) if all_prices else 0
            
            # 2. Get regional production data based on farm locations
            if locations_to_check:
                regional_data = RegionalProduction.objects.filter(
                    crop_category=crop.name,
                    region__in=locations_to_check
                ).order_by('year')
            else:
                regional_data = RegionalProduction.objects.filter(
                    crop_category=crop.name
                ).order_by('year')
            
            # If no data for this crop, skip it
            if not regional_data.exists():
                continue
            
            # Get latest production
            latest_prod = regional_data.last()
            
            # Calculate average production
            avg_prod = regional_data.aggregate(Avg('production_tons'))['production_tons__avg'] or 0
            
            # 3. Calculate growth trend
            yearly = regional_data.values('year').annotate(
                total=Sum('production_tons')
            ).order_by('year')
            
            growth_trend = 'stable'
            yearly_list = list(yearly)
            if len(yearly_list) >= 2:
                first_val = float(yearly_list[0]['total']) if yearly_list[0]['total'] else 0
                last_val = float(yearly_list[-1]['total']) if yearly_list[-1]['total'] else 0
                if first_val > 0:
                    growth = ((last_val - first_val) / first_val) * 100
                    if growth > 15:
                        growth_trend = 'growing'
                    elif growth < -15:
                        growth_trend = 'declining'
            
            # 4. Get profitability
            profit = Profitability.objects.filter(crop=crop).order_by('-year').first()
            if profit:
                profit_per_acre = float(profit.profit_per_acre) if profit.profit_per_acre else 0
                from marketPrice.views import get_production_cost
                production_cost = float(get_production_cost(crop.name))
                roi = (profit_per_acre / production_cost) * 100 if production_cost > 0 else 0
            else:
                profit_per_acre = 0
                roi = 0
            
            # 5. Calculate recommendation score
            score = 0
            
            # Price factor
            if latest_price > avg_price:
                score += 20
            elif latest_price > avg_price * 0.9:
                score += 10
            
            # Growth factor
            if growth_trend == 'growing':
                score += 30
            elif growth_trend == 'stable':
                score += 10
            
            # Profitability factor
            if roi > 100:
                score += 30
            elif roi > 50:
                score += 15
            elif roi > 20:
                score += 5
            
            # Regional demand
            if latest_prod and latest_prod.production_tons and latest_prod.production_tons > 0:
                score += 10
            
            # Determine recommendation
            if score >= 60:
                recommendation = 'STRONG_BUY'
                reason = _('High demand and profitability. Great time to plant!')
                css_class = 'success'
            elif score >= 40:
                recommendation = 'BUY'
                reason = _('Good potential. Consider planting.')
                css_class = 'info'
            elif score >= 20:
                recommendation = 'CONSIDER'
                reason = _('Moderate potential. Monitor market.')
                css_class = 'warning'
            else:
                recommendation = 'AVOID'
                reason = _('Low demand or declining market. Consider other crops.')
                css_class = 'danger'
            
            # Convert price to Viss (1 Ton = 612.4 Viss)
            TON_TO_VISS = 612.4
            
            # Get translated crop name
            crop_name_translated = _(crop.name)
            
            recommendations.append({
                'crop': crop,
                'crop_name': crop_name_translated,
                'crop_name_original': crop.name,
                'latest_price': latest_price / TON_TO_VISS,
                'avg_price': avg_price / TON_TO_VISS,
                'growth_trend': growth_trend,
                'growth_trend_translated': _(growth_trend),
                'profit_per_acre': profit_per_acre,
                'roi': round(roi, 1),
                'score': score,
                'recommendation': recommendation,
                'recommendation_translated': _(recommendation),
                'reason': reason,
                'css_class': css_class,
                'price_trend': 'up' if latest_price > avg_price else 'down',
                'price_trend_translated': _('Up') if latest_price > avg_price else _('Down'),
            })
            
        except Exception as e:
            # Skip this crop if there's an error
            continue
    
    # Sort by score (highest first)
    recommendations.sort(key=lambda x: x['score'], reverse=True)
    
    # Get all available regions for the filter (deduplicated and sorted)
    all_locations = RegionalProduction.objects.values_list('region', flat=True).distinct().order_by('region')
    
    # Get recommendations for each farm location
    farm_recommendations = []
    for farm in user_farms:
        farm_crops = []
        for rec in recommendations:
            # Check if this crop has data for this farm's location
            has_data = RegionalProduction.objects.filter(
                crop_category=rec['crop_name_original'],
                region=farm.location
            ).exists()
            if has_data:
                farm_crops.append(rec['crop_name'])
        farm_recommendations.append({
            'farm': farm,
            'crops': farm_crops[:3],  # Top 3 recommendations
        })
    
    context = {
        'recommendations': recommendations,
        'locations': list(all_locations),
        'selected_location': selected_location or 'all',
        'user_farms': user_farms,
        'user_farm_locations': user_farm_locations,
        'farm_recommendations': farm_recommendations,
        'total_crops': len(recommendations),
        'has_farms': user_farms.exists(),
        'page_title': _('What to Plant - Crop Advisor'),
    }
    
    return render(request, 'crops/planting_advisor.html', context)

