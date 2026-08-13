from django.shortcuts import render, get_object_or_404
from django.db.models import Avg, Max, Min, Count, Q, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Crop, HarvestPrice, YieldData, DailyMarketPrice, Profitability
from datetime import datetime, timedelta
import json
import logging
from farms.models import Farm  
from .models import Crop, HarvestPrice, YieldData, DailyMarketPrice, Profitability, RegionalProduction
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

logger = logging.getLogger(__name__)

def index(request):
    """Dashboard with summary cards and key metrics"""
    try:
        total_crops = Crop.objects.count()
        latest_date = DailyMarketPrice.objects.latest('recorded_date').recorded_date
        daily_prices = DailyMarketPrice.objects.filter(recorded_date=latest_date)
        total_markets = daily_prices.values('market').distinct().count()
        total_commodities = daily_prices.count()
        
        latest_year = HarvestPrice.objects.latest('year').year
        harvest_prices = HarvestPrice.objects.filter(year=latest_year)
        
        top_harvest_prices = harvest_prices.order_by('-price')[:5]
        top_daily_prices = daily_prices.order_by('-price')[:5]
        
        price_trends = {}
        years = HarvestPrice.objects.values_list('year', flat=True).distinct().order_by('year')
        years_list = list(years)
        
        for crop in top_harvest_prices.select_related('crop'):
            prices = HarvestPrice.objects.filter(
                crop=crop.crop,
                year__in=years_list
            ).order_by('year')
            if prices.count() >= 3:
                # Keep English for the charts
                price_trends[crop.crop.name] = [float(p.price) for p in prices]
        
        categories = Crop.objects.values('category').annotate(count=Count('id'))
        category_labels = [_(c['category']) if c['category'] else _('Uncategorized') for c in categories]
        category_counts = [c['count'] for c in categories]
        
        # ==========================================
        # FIX: Translate the crop names here in Python
        # ==========================================
        top_harvest_data = []
        for item in top_harvest_prices:
            translated_name = _(item.crop.name)  # Translates to Burmese
            top_harvest_data.append({
                'id': item.crop.id,
                'name_translated': translated_name,
                'name_original': item.crop.name,
                'price': item.price,
            })
            
        top_daily_data = []
        for item in top_daily_prices:
            translated_commodity = _(item.commodity) # Translates to Burmese
            translated_category = _(item.category) if item.category else ''
            top_daily_data.append({
                'commodity_translated': translated_commodity,
                'category_translated': translated_category,
                'price': item.price,
            })
        # ==========================================

        context = {
            'total_crops': total_crops,
            'total_markets': total_markets,
            'total_commodities': total_commodities,
            'latest_date': latest_date,
            'latest_year': latest_year,
            'top_harvest_prices': top_harvest_data, # Use the new list
            'top_daily_prices': top_daily_data,     # Use the new list
            'price_trends': json.dumps(price_trends),
            'years_list': json.dumps(years_list),
            'category_labels': json.dumps(category_labels),
            'category_counts': json.dumps(category_counts),
        }
    except Exception as e:
        logger.error(f"Error in index view: {e}")
        context = {
            'total_crops': 0,
            'total_markets': 0,
            'total_commodities': 0,
            'latest_date': None,
            'latest_year': None,
            'top_harvest_prices': [],
            'top_daily_prices': [],
            'price_trends': '{}',
            'years_list': '[]',
            'category_labels': '[]',
            'category_counts': '[]',
        }
    
    return render(request, 'marketPrice/index.html', context)
def crop_list(request):
    """List all crops with latest price information and statistics"""
    crops = Crop.objects.all().prefetch_related('harvest_prices', 'daily_prices')
    
    # --- EXACT CONVERSION RATE ---
    TON_TO_VISS = 612.4
    
    crop_data = []
    for crop in crops:
        translated_name = _(crop.name)
        translated_category = _(crop.category) if crop.category else ''
        
        # --- 1. Yearly Harvest Data ---
        latest_harvest = crop.harvest_prices.order_by('-year').first()
        yearly_unit = crop.unit if crop.unit else ''
        
        # --- 2. Daily Data ---
        latest_daily = crop.daily_prices.order_by('-recorded_date').first()
        
        # --- 3. Calculate Converted Yearly Price (Per Viss) ---
        yearly_price_per_viss = None
        if latest_harvest and yearly_unit and "Ton" in yearly_unit:
            yearly_price_per_viss = float(latest_harvest.price) / TON_TO_VISS
        
        # --- 4. MOCK DAILY DATA (Only if real data is missing) ---
        if not latest_daily and latest_harvest:
            # Create a realistic mock: Retail is roughly 3x the wholesale price
            mock_daily_price = yearly_price_per_viss * 3 if yearly_price_per_viss else (float(latest_harvest.price) / 12)
            mock_daily_unit = "Viss"
            
            # Temporarily inject the mock into a dictionary so the HTML doesn't crash
            latest_daily = {
                'price': mock_daily_price,
                'unit': mock_daily_unit,
                'is_mock': True  # We will use this in the HTML
            }
        elif latest_daily:
            # If real data exists, mark it as real
            latest_daily.is_mock = False

        # --- 5. Stats & Calculations ---
        price_change = None
        trend_direction = "stable"
        price_change_percentage = None
        
        all_prices = crop.harvest_prices.all().order_by('year')
        prices_list = [float(p.price) for p in all_prices]
        
        min_price = min(prices_list) if prices_list else 0
        max_price = max(prices_list) if prices_list else 0
        avg_price = sum(prices_list) / len(prices_list) if prices_list else 0
        
        if latest_harvest and len(prices_list) >= 2:
            previous_harvest = all_prices[len(all_prices)-2]
            if previous_harvest and previous_harvest.price:
                price_change = float(latest_harvest.price) - float(previous_harvest.price)
                price_change_percentage = (price_change / float(previous_harvest.price)) * 100
                
                if price_change > 0:
                    trend_direction = "up"
                elif price_change < 0:
                    trend_direction = "down"
                else:
                    trend_direction = "stable"

        crop_data.append({
            'crop': crop,
            'crop_name': translated_name,
            'crop_category': translated_category,
            'latest_harvest': latest_harvest,
            'latest_daily': latest_daily, # Now holds the Mock dict OR the real object
            
            'yearly_price_per_viss': yearly_price_per_viss,
            'crop_unit': yearly_unit, 
            
            'price_change': price_change,
            'price_change_percentage': price_change_percentage,
            'trend_direction': trend_direction,
            'min_price': min_price,
            'max_price': max_price,
            'avg_price': avg_price,
            'prices_list_length': len(prices_list),
        })
    
    # Filter by category if provided
    category = request.GET.get('category')
    if category:
        crop_data = [c for c in crop_data if c['crop'].category == category]
    
    # Search by name
    search = request.GET.get('search')
    if search:
        crop_data = [c for c in crop_data if search.lower() in c['crop'].name.lower()]
    
    # Unique Categories Logic
    raw_categories = Crop.objects.values_list('category', flat=True).exclude(category__isnull=True).exclude(category='')
    unique_raw_categories = sorted(list(set(raw_categories)))
    
    categories = []
    for cat in unique_raw_categories:
        categories.append({
            'value': cat,
            'label': _(cat)
        })
    
    context = {
        'crop_data': crop_data,
        'categories': categories,
        'selected_category': category,
        'search_query': search,
    }
    return render(request, 'marketPrice/crop_list.html', context)

def crop_detail(request, crop_id):
    """Detailed view for a single crop with price charts"""
    crop = get_object_or_404(Crop, id=crop_id)
    
    translated_name = _(crop.name)
    translated_category = _(crop.category) if crop.category else ''
    
    harvest_prices = crop.harvest_prices.all().order_by('year')
    harvest_years = [hp.year for hp in harvest_prices]
    harvest_values = [float(hp.price) for hp in harvest_prices]
    
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    daily_prices = crop.daily_prices.filter(
        recorded_date__gte=thirty_days_ago
    ).order_by('recorded_date')
    daily_dates = [dp.recorded_date.strftime('%Y-%m-%d') for dp in daily_prices]
    daily_values = [float(dp.price) for dp in daily_prices]
    
    yields = crop.yields.all().order_by('year')
    yield_years = [y.year for y in yields]
    yield_values = [float(y.yield_value) for y in yields]
    
    profitability = crop.profitability.all().order_by('year')
    profit_years = [p.year for p in profitability]
    profit_values = [float(p.profit_per_acre) for p in profitability]
    
    latest_harvest = harvest_prices.last() if harvest_prices else None
    latest_daily = daily_prices.last() if daily_prices else None
    
    stats = {}
    if harvest_values:
        stats['max_price'] = max(harvest_values)
        stats['min_price'] = min(harvest_values)
        stats['avg_price'] = sum(harvest_values) / len(harvest_values)
        stats['latest_price'] = harvest_values[-1]
    
    context = {
        'crop': crop,
        'crop_name': translated_name,
        'crop_category': translated_category,
        'harvest_years': json.dumps(harvest_years),
        'harvest_values': json.dumps(harvest_values),
        'daily_dates': json.dumps(daily_dates),
        'daily_values': json.dumps(daily_values),
        'yield_years': json.dumps(yield_years),
        'yield_values': json.dumps(yield_values),
        'profit_years': json.dumps(profit_years),
        'profit_values': json.dumps(profit_values),
        'latest_harvest': latest_harvest,
        'latest_daily': latest_daily,
        'stats': stats,
        'has_harvest_data': bool(harvest_values),
        'has_daily_data': bool(daily_values),
        'has_yield_data': bool(yield_values),
        'has_profit_data': bool(profit_values),
    }
    return render(request, 'marketPrice/crop_detail.html', context)


def daily_prices(request):
    """Daily market prices table with filters"""
    daily_prices = DailyMarketPrice.objects.all().order_by('-recorded_date', 'category', 'commodity')
    
    category = request.GET.get('category')
    if category:
        daily_prices = daily_prices.filter(category=category)
    
    market = request.GET.get('market')
    if market:
        daily_prices = daily_prices.filter(market=market)
    
    date = request.GET.get('date')
    if date:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            daily_prices = daily_prices.filter(recorded_date=date_obj)
        except ValueError:
            pass
    
    raw_categories = DailyMarketPrice.objects.values_list('category', flat=True).distinct().order_by('category')
    raw_markets = DailyMarketPrice.objects.values_list('market', flat=True).distinct().order_by('market')
    dates = DailyMarketPrice.objects.values_list('recorded_date', flat=True).distinct().order_by('-recorded_date')
    
    categories = []
    for cat in raw_categories:
        if cat:
            categories.append({
                'value': cat,
                'label': _(cat)
            })
    
    markets = list(raw_markets)
    
    daily_prices_data = []
    for item in daily_prices:
        translated_commodity = _(item.commodity)
        translated_category = _(item.category) if item.category else ''
        
        price_data = {
            'commodity_name': translated_commodity,
            'category': translated_category,
            'market': item.market,
            'price': float(item.price) if item.price else 0,
            'unit': item.unit,
            'recorded_date': item.recorded_date,
        }
        daily_prices_data.append(price_data)
    
    latest_date = DailyMarketPrice.objects.latest('recorded_date').recorded_date if daily_prices.exists() else None
    
    context = {
        'daily_prices': daily_prices_data,
        'categories': categories,
        'markets': markets,
        'dates': dates[:10],
        'selected_category': category,
        'selected_market': market,
        'selected_date': date,
        'latest_date': latest_date,
    }
    return render(request, 'marketPrice/daily_prices.html', context)


def profitability(request):
    """Display crop profitability ranking"""
    years = Profitability.objects.values_list('year', flat=True).distinct().order_by('-year')
    
    if not years:
        context = {'has_data': False}
        return render(request, 'marketPrice/profitability.html', context)
    
    selected_year = request.GET.get('year')
    if selected_year:
        try:
            selected_year = int(selected_year)
            if selected_year not in years:
                selected_year = years.first()
        except ValueError:
            selected_year = years.first()
    else:
        selected_year = years.first()
    
    profitability_qs = Profitability.objects.filter(
        year=selected_year
    ).select_related('crop').order_by('-profit_per_acre')
    
    profitability_data = []
    chart_labels = []
    chart_values = []
    
    for item in profitability_qs:
        translated_name = _(item.crop.name)
        roi = 0
        if item.price_per_ton and item.price_per_ton > 0:
            roi = (item.profit_per_acre / item.price_per_ton) * 100
        
        crop_data = {
            'crop_id': item.crop.id,
            'crop_name': translated_name,
            'year': item.year,
            'price_per_ton': float(item.price_per_ton) if item.price_per_ton else 0,
            'yield_tons_per_acre': float(item.yield_tons_per_acre) if item.yield_tons_per_acre else 0,
            'profit_per_acre': float(item.profit_per_acre) if item.profit_per_acre else 0,
            'roi': roi,
        }
        profitability_data.append(crop_data)
        chart_labels.append(translated_name)
        chart_values.append(float(item.profit_per_acre) if item.profit_per_acre else 0)
    
    context = {
        'has_data': True,
        'profitability_data': profitability_data,
        'years': list(years),
        'selected_year': selected_year,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
    }
    return render(request, 'marketPrice/profitability.html', context)


def compare(request):
    """Compare multiple crops side by side"""
    crop_ids = request.GET.getlist('crops')
    all_crops = Crop.objects.all().order_by('name')
    
    if not crop_ids:
        context = {
            'all_crops': all_crops,
            'comparison_data': [],
            'years': [],
            'selected_ids': [],
        }
        return render(request, 'marketPrice/compare.html', context)
    
    selected_crops = Crop.objects.filter(id__in=crop_ids).prefetch_related('harvest_prices', 'daily_prices')
    
    if not selected_crops:
        context = {
            'all_crops': all_crops,
            'comparison_data': [],
            'years': [],
            'selected_ids': [],
        }
        return render(request, 'marketPrice/compare.html', context)
    
    years = HarvestPrice.objects.values_list('year', flat=True).distinct().order_by('year')
    years_list = list(years)
    
    comparison_data = []
    for crop in selected_crops:
        translated_name = _(crop.name)
        price_history = []
        for year in years_list:
            price = crop.harvest_prices.filter(year=year).first()
            price_history.append({
                'year': year,
                'price': float(price.price) if price else None
            })
        
        crop_data = {
            'crop_id': crop.id,
            'crop_name': translated_name,
            'crop_category': _(crop.category) if crop.category else '',
            'price_history': price_history,
            'latest_harvest': {
                'price': float(crop.harvest_prices.order_by('-year').first().price) if crop.harvest_prices.exists() else None,
                'year': crop.harvest_prices.order_by('-year').first().year if crop.harvest_prices.exists() else None,
            } if crop.harvest_prices.exists() else None,
            'latest_daily': {
                'price': float(crop.daily_prices.order_by('-recorded_date').first().price) if crop.daily_prices.exists() else None,
                'market': crop.daily_prices.order_by('-recorded_date').first().market if crop.daily_prices.exists() else None,
                'recorded_date': crop.daily_prices.order_by('-recorded_date').first().recorded_date.isoformat() if crop.daily_prices.exists() else None,
            } if crop.daily_prices.exists() else None,
        }
        comparison_data.append(crop_data)
    
    selected_ids = [int(id) for id in crop_ids]
    
    context = {
        'all_crops': all_crops,
        'comparison_data': comparison_data,
        'years': years_list,
        'selected_ids': selected_ids,
    }
    return render(request, 'marketPrice/compare.html', context)


def regions_view(request):
    """Display regional production data on a map or table"""
    regional_data = RegionalProduction.objects.all().order_by('region', 'crop_category', 'year')
    raw_regions = RegionalProduction.objects.values_list('region', flat=True)
    regions = sorted(list(set(raw_regions)))
    
    raw_categories = RegionalProduction.objects.values_list('crop_category', flat=True)
    categories = sorted(list(set(raw_categories)))
    translated_categories = [_(cat) for cat in categories if cat]
    
    selected_region = request.GET.get('region')
    if selected_region:
        regional_data = regional_data.filter(region=selected_region)
    
    selected_category = request.GET.get('category')
    if selected_category:
        regional_data = regional_data.filter(crop_category=selected_category)
    
    regional_data_list = []
    for item in regional_data:
        regional_data_list.append({
            'region': item.region,
            'crop_category': _(item.crop_category) if item.crop_category else '',
            'year': item.year,
            'sown_acres': float(item.sown_acres) if item.sown_acres else 0,
            'harvested_acres': float(item.harvested_acres) if item.harvested_acres else 0,
            'production_tons': float(item.production_tons) if item.production_tons else 0,
            'measurement_type': item.measurement_type,
        })
    
    context = {
        'regional_data': regional_data_list,
        'regions': regions,
        'categories': translated_categories,
        'selected_region': selected_region,
        'selected_category': selected_category,
        'has_data': True,
    }
    return render(request, 'marketPrice/region_analysis.html', context)


@require_http_methods(["GET"])
def api_crop_prices(request, crop_id):
    """API endpoint for crop price data (for AJAX charts)"""
    crop = get_object_or_404(Crop, id=crop_id)
    harvest_prices = crop.harvest_prices.all().order_by('year')
    data = {
        'crop_name': _(crop.name),
        'years': [hp.year for hp in harvest_prices],
        'prices': [float(hp.price) for hp in harvest_prices],
    }
    return JsonResponse(data)


@require_http_methods(["GET"])
def api_daily_prices(request):
    """API endpoint for daily prices (for AJAX updates)"""
    category = request.GET.get('category')
    date = request.GET.get('date')
    queryset = DailyMarketPrice.objects.all()
    
    if category:
        queryset = queryset.filter(category=category)
    if date:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            queryset = queryset.filter(recorded_date=date_obj)
        except ValueError:
            pass
    
    data = []
    for item in queryset.order_by('category', 'commodity'):
        data.append({
            'commodity': _(item.commodity),
            'category': _(item.category) if item.category else '',
            'market': item.market,
            'price': float(item.price),
            'unit': item.unit,
            'date': item.recorded_date.strftime('%Y-%m-%d'),
        })
    return JsonResponse({'data': data})


def crop_recommendation(request, crop_id=None):
    """Get recommendations for specific crop or all crops in user's farms"""
    from datetime import datetime
    import math
    
    user_crops = set()
    if request.user.is_authenticated:
        user_farms = Farm.objects.filter(owner=request.user)
        for farm in user_farms:
            farm_activities = farm.activities.all()
            for activity in farm_activities:
                if activity.crop:
                    user_crops.add(activity.crop)

    if crop_id:
        crops = [get_object_or_404(Crop, id=crop_id)]
    elif request.user.is_authenticated and user_crops:
        crops = list(user_crops)
    else:
        crops = Crop.objects.filter(harvest_prices__isnull=False).distinct()
        
    recommendations = []
    for crop in crops:
        latest_price = crop.harvest_prices.order_by('-year').first()
        latest_profit = crop.profitability.order_by('-year').first()
        
        if not latest_price or not latest_profit:
            continue
        
        price_history = crop.harvest_prices.all().order_by('year')
        prices = [float(p.price) for p in price_history]
        
        trend = "stable"
        price_change = 0
        if len(prices) >= 2:
            price_change = ((prices[-1] - prices[-2]) / prices[-2]) * 100
            if price_change > 5:
                trend = "up"
            elif price_change < -5:
                trend = "down"
        
        recommendation = "HOLD"
        recommendation_reason = ""
        if trend == "up" and price_change > 10:
            recommendation = "HOLD"
            recommendation_reason = _lazy("Prices are rising strongly. Consider holding for better price.")
        elif trend == "down" and price_change < -10:
            recommendation = "SELL"
            recommendation_reason = _lazy("Prices are falling. Consider selling before further decline.")
        elif trend == "up" and price_change > 5:
            recommendation = "HOLD"
            recommendation_reason = _lazy("Prices are trending up. Good time to monitor.")
        elif trend == "down" and price_change < -5:
            recommendation = "SELL"
            recommendation_reason = _lazy("Prices are trending down. Consider selling soon.")
        else:
            recommendation = "MONITOR"
            recommendation_reason = _lazy("Prices are stable. Monitor market conditions.")
        
        current_price = float(latest_price.price)
        current_profit = float(latest_profit.profit_per_acre)
        export_price = current_price * 0.85
        export_profit = current_profit * 0.80
        local_profit = current_profit
        
        export_recommendation = "LOCAL"
        if export_profit > local_profit * 1.1:
            export_recommendation = "EXPORT"
        elif export_profit > local_profit * 0.9:
            export_recommendation = "CONSIDER_EXPORT"
        
        avg_price = sum(prices[-3:]) / 3 if len(prices) >= 3 else prices[-1]
        season_rec = "SELL" if current_price > avg_price * 1.1 else "HOLD"
        
        translated_crop_name = _(crop.name)
        recommendations.append({
            'crop': crop,
            'crop_name': translated_crop_name,
            'latest_price': latest_price,
            'latest_profit': latest_profit,
            'price_change': price_change,
            'trend': trend,
            'recommendation': recommendation,
            'recommendation_reason': recommendation_reason,
            'export_recommendation': export_recommendation,
            'season_recommendation': season_rec,
            'avg_price': avg_price,
            'current_price': current_price,
        })
    
    recommendations.sort(key=lambda x: float(x['latest_profit'].profit_per_acre), reverse=True)
    context = {
        'recommendations': recommendations,
        'current_date': datetime.now(),
    }
    return render(request, 'marketPrice/recommendations.html', context)