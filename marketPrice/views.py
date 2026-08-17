from django.shortcuts import render, get_object_or_404
from django.db.models import Avg, Max, Min, Count, Q, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
import json
import logging
from decimal import Decimal
from types import SimpleNamespace

from farms.models import Farm
from .models import Crop, HarvestPrice, YieldData, DailyMarketPrice, Profitability, RegionalProduction
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy

logger = logging.getLogger(__name__)

# ==========================================
# CONSTANTS - Centralized for consistency
# ==========================================
TON_TO_VISS = 612.4
CALENDAR_YEARS = ['2022', '2023', '2024', '2025', '2026']

# =========================================================
# REALISTIC PRODUCTION COSTS PER ACRE (Kyat)
# Based on actual Myanmar farming data
# =========================================================
PRODUCTION_COSTS = {
    'rice': Decimal("3500000"),
    'paddy': Decimal("3500000"),
    'maize': Decimal("4000000"),
    'sugarcane': Decimal("6000000"),
    'tapioca': Decimal("3500000"),
    'onion': Decimal("5000000"),
    'potato': Decimal("5500000"),
    'garlic': Decimal("8000000"),
    'chillies': Decimal("7000000"),
    'tomato': Decimal("6000000"),
    'pulse': Decimal("2500000"),
    'bean': Decimal("2500000"),
    'groundnut': Decimal("3000000"),
    'sesamum': Decimal("2000000"),
    'coffee': Decimal("5000000"),
    'tea': Decimal("4000000"),
    'tobacco': Decimal("8000000"),
    'cotton': Decimal("4500000"),
    'default': Decimal("4000000"),
}
DEFAULT_COST = Decimal("4000000")

# =========================================================
# REALISTIC YIELD PER ACRE (in tons)
# =========================================================
YIELD_PER_ACRE = {
    'rice': Decimal("3.5"),
    'paddy': Decimal("3.5"),
    'maize': Decimal("4.0"),
    'sugarcane': Decimal("50.0"),
    'tapioca': Decimal("25.0"),
    'onion': Decimal("12.0"),
    'potato': Decimal("15.0"),
    'garlic': Decimal("5.0"),
    'chillies': Decimal("1.5"),
    'tomato': Decimal("10.0"),
    'pulse': Decimal("1.2"),
    'bean': Decimal("1.2"),
    'groundnut': Decimal("1.5"),
    'sesamum': Decimal("0.8"),
    'coffee': Decimal("0.8"),
    'tea': Decimal("1.2"),
    'tobacco': Decimal("2.0"),
    'cotton': Decimal("1.5"),
    'default': Decimal("5.0"),
}
DEFAULT_YIELD = Decimal("5.0")

# Retail markups by crop category
RETAIL_MARKUP = {
    'rice': 1.10,
    'paddy': 1.10,
    'onion': 1.25,
    'potato': 1.25,
    'garlic': 1.30,
    'pulse': 1.20,
    'bean': 1.20,
    'coffee': 1.40,
    'tea': 1.35,
    'chillies': 1.35,
    'tobacco': 1.40,
    'sugarcane': 1.15,
    'tapioca': 1.15,
    'groundnut': 1.20,
    'sesamum': 1.20,
    'cotton': 1.25,
}
DEFAULT_MARKUP = 1.25

# Export cost factors
EXPORT_COSTS = {
    'rice': 0.12,
    'pulses': 0.18,
    'fruits': 0.25,
    'vegetables': 0.28,
    'default': 0.20
}

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def get_markup_for_crop(crop_name):
    crop_name_lower = crop_name.lower()
    for key, markup in RETAIL_MARKUP.items():
        if key in crop_name_lower:
            return markup
    return DEFAULT_MARKUP

def get_production_cost(crop_name):
    crop_name_lower = crop_name.lower()
    for key, cost in PRODUCTION_COSTS.items():
        if key in crop_name_lower:
            return cost
    return DEFAULT_COST

def get_yield_per_acre(crop_name):
    crop_name_lower = crop_name.lower()
    for key, yield_val in YIELD_PER_ACRE.items():
        if key in crop_name_lower:
            return yield_val
    return DEFAULT_YIELD

def get_export_cost_for_crop(crop_name, crop_category=None):
    crop_name_lower = crop_name.lower()
    for key, cost in EXPORT_COSTS.items():
        if key in crop_name_lower:
            return cost
    if crop_category:
        category_lower = crop_category.lower()
        for key, cost in EXPORT_COSTS.items():
            if key in category_lower:
                return cost
    return EXPORT_COSTS['default']

# =========================================================
# INDEX / DASHBOARD
# =========================================================
def index(request):
    try:
        total_crops = Crop.objects.count()
        
        latest_daily = DailyMarketPrice.objects.order_by('-recorded_date').first()
        if latest_daily:
            latest_date = latest_daily.recorded_date
            daily_prices = DailyMarketPrice.objects.filter(recorded_date=latest_date)
            total_markets = daily_prices.values('market').distinct().count()
            total_commodities = daily_prices.count()
        else:
            latest_date = None
            daily_prices = DailyMarketPrice.objects.none()
            total_markets = 0
            total_commodities = 0
        
        latest_harvest = HarvestPrice.objects.filter(year__in=CALENDAR_YEARS).order_by('-year').first()
        if latest_harvest:
            latest_year = latest_harvest.year
            harvest_prices = HarvestPrice.objects.filter(year=latest_year)
        else:
            latest_year = None
            harvest_prices = HarvestPrice.objects.none()
        
        top_harvest_prices = harvest_prices.select_related('crop').order_by('-price')[:5]
        top_harvest_data = []
        for item in top_harvest_prices:
            price_per_ton = float(item.price)
            price_per_viss = price_per_ton / 612.4 if price_per_ton else 0
            top_harvest_data.append({
                'id': item.crop.id,
                'name_translated': _(item.crop.name),
                'name_original': item.crop.name,
                'price': price_per_viss,
                'price_per_ton': price_per_ton,
                'price_per_viss': price_per_viss,
                'unit': 'Viss',
            })
        
        top_daily_prices = daily_prices.order_by('-price')[:5]
        top_daily_data = []
        for item in top_daily_prices:
            top_daily_data.append({
                'commodity_translated': _(item.commodity),
                'category_translated': _(item.category) if item.category else '',
                'price': item.price,
                'unit': item.unit or 'Viss',
            })
        
        price_trends = {}
        years_list = []
        years = HarvestPrice.objects.filter(year__in=CALENDAR_YEARS).values_list('year', flat=True).distinct().order_by('year')
        years_list = list(years)
        
        if years_list:
            crops_with_data = []
            for crop in Crop.objects.all():
                crop_prices = HarvestPrice.objects.filter(crop=crop, year__in=CALENDAR_YEARS).order_by('year')
                if crop_prices.count() >= 2:
                    crops_with_data.append({
                        'crop': crop,
                        'count': crop_prices.count(),
                        'last_price': crop_prices.last().price if crop_prices.exists() else 0,
                    })
            
            crops_with_data.sort(key=lambda x: x['last_price'], reverse=True)
            top_crops = crops_with_data[:5]
            
            for crop_info in top_crops:
                crop = crop_info['crop']
                crop_prices = HarvestPrice.objects.filter(
                    crop=crop,
                    year__in=years_list
                ).order_by('year')
                
                if crop_prices.count() >= 2:
                    crop_name = _(crop.name)
                    price_values = [float(p.price) / 612.4 for p in crop_prices]
                    price_trends[crop_name] = price_values
        
        categories = Crop.objects.values('category').annotate(count=Count('id'))
        category_labels = []
        category_counts = []
        for c in categories:
            if c['category']:
                category_labels.append(_(c['category']))
                category_counts.append(c['count'])
        
        context = {
            'total_crops': total_crops,
            'total_markets': total_markets,
            'total_commodities': total_commodities,
            'latest_date': latest_date,
            'latest_year': latest_year,
            'top_harvest_prices': top_harvest_data,
            'top_daily_prices': top_daily_data,
            'price_trends': json.dumps(price_trends),
            'years_list': json.dumps(years_list),
            'category_labels': json.dumps(category_labels),
            'category_counts': json.dumps(category_counts),
        }
        
    except Exception as e:
        logger.error(f"Error in index view: {e}", exc_info=True)
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

# =========================================================
# CROP LIST - FIXED to use only calendar years
# =========================================================
def crop_list(request):
    crops = Crop.objects.all().prefetch_related('harvest_prices', 'daily_prices')
    
    crop_data = []
    for crop in crops:
        translated_name = _(crop.name)
        translated_category = _(crop.category) if crop.category else ''
        
        harvest_prices = crop.harvest_prices.filter(year__in=CALENDAR_YEARS).order_by('-year')
        latest_harvest = harvest_prices.first()
        yearly_unit = crop.unit if crop.unit else ''
        
        latest_daily = crop.daily_prices.order_by('-recorded_date').first()
        
        yearly_price_per_viss = None
        if latest_harvest and yearly_unit and "Ton" in yearly_unit:
            yearly_price_per_viss = float(latest_harvest.price) / TON_TO_VISS
        
        if not latest_daily and latest_harvest:
            markup = get_markup_for_crop(crop.name)
            if yearly_price_per_viss:
                mock_daily_price = yearly_price_per_viss * markup
            else:
                mock_daily_price = float(latest_harvest.price) / 12
            
            latest_daily = SimpleNamespace(
                price=mock_daily_price,
                unit="Viss",
                is_mock=True,
                recorded_date=datetime.now().date()
            )
        elif latest_daily:
            latest_daily.is_mock = False

        price_change = None
        trend_direction = "stable"
        price_change_percentage = None
        
        all_prices = crop.harvest_prices.filter(year__in=CALENDAR_YEARS).order_by('year')
        prices_list = [float(p.price) for p in all_prices]
        
        min_price = min(prices_list) if prices_list else 0
        max_price = max(prices_list) if prices_list else 0
        avg_price = sum(prices_list) / len(prices_list) if prices_list else 0
        
        if latest_harvest and len(prices_list) >= 2:
            previous_harvest = all_prices[len(all_prices)-2] if len(all_prices) >= 2 else None
            if previous_harvest and previous_harvest.price:
                prev_price = float(previous_harvest.price)
                curr_price = float(latest_harvest.price)
                price_change = curr_price - prev_price
                if prev_price > 0:
                    price_change_percentage = (price_change / prev_price) * 100
                else:
                    price_change_percentage = 0
                
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
            'latest_daily': latest_daily,
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
    
    category = request.GET.get('category')
    if category:
        crop_data = [c for c in crop_data if c['crop'].category == category]
    
    search = request.GET.get('search')
    if search:
        crop_data = [c for c in crop_data if search.lower() in c['crop'].name.lower()]
    
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

# =========================================================
# CROP DETAIL - FIXED to use only calendar years
# =========================================================
def crop_detail(request, crop_id):
    crop = get_object_or_404(Crop, id=crop_id)
    
    translated_name = _(crop.name)
    translated_category = _(crop.category) if crop.category else ''
    
    harvest_prices = crop.harvest_prices.filter(year__in=CALENDAR_YEARS).order_by('year')
    harvest_years = [hp.year for hp in harvest_prices]
    harvest_values = [float(hp.price) / TON_TO_VISS for hp in harvest_prices]
    
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    daily_prices = crop.daily_prices.filter(
        recorded_date__gte=thirty_days_ago
    ).order_by('recorded_date')
    daily_dates = [dp.recorded_date.strftime('%Y-%m-%d') for dp in daily_prices]
    daily_values = [float(dp.price) for dp in daily_prices]
    
    yields = crop.yields.all().order_by('year')
    yield_years = [y.year for y in yields]
    yield_values = [float(y.yield_value) for y in yields]
    
    profitability = crop.profitability.filter(year__in=CALENDAR_YEARS).order_by('year')
    profit_years = [p.year for p in profitability]
    profit_values = [float(p.profit_per_acre) for p in profitability]
    
    latest_harvest = harvest_prices.last() if harvest_prices else None
    
    stats = {}
    if harvest_values:
        stats['max_price'] = max(harvest_values)
        stats['min_price'] = min(harvest_values)
        stats['avg_price'] = sum(harvest_values) / len(harvest_values)
        stats['latest_price'] = harvest_values[-1]
        
    table_data = []
    for i, hp in enumerate(harvest_prices):
        price_viss = float(hp.price) / TON_TO_VISS
        change_viss = 0
        change_percentage = 0
        if i > 0:
            prev_price = float(harvest_prices[i-1].price) / TON_TO_VISS
            change_viss = price_viss - prev_price
            if prev_price > 0:
                change_percentage = (change_viss / prev_price) * 100
        table_data.append({
            'year': hp.year,
            'price_viss': price_viss,
            'change_viss': change_viss,
            'change_percentage': change_percentage,
        })
    
    context = {
        'crop': crop,
        'crop_name': translated_name,
        'crop_category': translated_category,
        'harvest_years': json.dumps(harvest_years),
        'harvest_values': json.dumps(harvest_values),
        'table_data': table_data,
        'daily_dates': json.dumps(daily_dates),
        'daily_values': json.dumps(daily_values),
        'yield_years': json.dumps(yield_years),
        'yield_values': json.dumps(yield_values),
        'profit_years': json.dumps(profit_years),
        'profit_values': json.dumps(profit_values),
        'latest_harvest': latest_harvest,
        'stats': stats,
        'has_harvest_data': bool(harvest_values),
        'has_daily_data': bool(daily_values),
        'has_yield_data': bool(yield_values),
        'has_profit_data': bool(profit_values),
    }
    return render(request, 'marketPrice/crop_detail.html', context)

# =========================================================
# DAILY PRICES
# =========================================================
def daily_prices(request):
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
            logger.warning(f"Invalid date format: {date}")
    
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

# =========================================================
# PROFITABILITY - FIXED to use only calendar years
# =========================================================
def profitability(request):
    years = Profitability.objects.filter(year__in=CALENDAR_YEARS).values_list('year', flat=True).distinct().order_by('-year')
    
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
        
        price_per_ton = float(item.price_per_ton) if item.price_per_ton else 0
        farmgate_viss = price_per_ton / TON_TO_VISS if price_per_ton > 0 else 0
        markup = get_markup_for_crop(item.crop.name)
        retail_viss = farmgate_viss * markup
        
        trader_margin = 0
        if retail_viss > 0:
            trader_margin = ((retail_viss - farmgate_viss) / retail_viss) * 100
        
        yield_tons = float(item.yield_tons_per_acre) if item.yield_tons_per_acre else 0
        profit_per_acre = float(item.profit_per_acre) if item.profit_per_acre else 0
        
        revenue_per_acre = price_per_ton * yield_tons if yield_tons > 0 else 0
        production_cost = float(get_production_cost(item.crop.name))
        
        if profit_per_acre <= 0:
            profit_per_acre = revenue_per_acre - production_cost
        
        farmer_profit_margin = 0
        if revenue_per_acre > 0:
            farmer_profit_margin = (profit_per_acre / revenue_per_acre) * 100
            if farmer_profit_margin > 80:
                farmer_profit_margin = 80
        
        roi = 0
        if production_cost > 0:
            roi = (profit_per_acre / production_cost) * 100
            if roi > 300:
                roi = 300
        
        crop_data = {
            'crop_id': item.crop.id,
            'crop_name': translated_name,
            'year': item.year,
            'farmgate_viss': int(farmgate_viss),
            'retail_viss': int(retail_viss),
            'trader_margin': int(trader_margin),
            'farmer_profit_margin': int(farmer_profit_margin),
            'profit_margin': int(farmer_profit_margin),
            'roi': int(roi),
            'profit_per_acre': int(profit_per_acre),
            'revenue_per_acre': int(revenue_per_acre),
            'production_cost': int(production_cost),
            'yield_tons_per_acre': yield_tons,
        }
        profitability_data.append(crop_data)
        
        chart_labels.append(translated_name)
        chart_values.append(float(retail_viss))
    
    context = {
        'has_data': True,
        'profitability_data': profitability_data,
        'years': list(years),
        'selected_year': selected_year,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
    }
    return render(request, 'marketPrice/profitability.html', context)

# =========================================================
# COMPARE
# =========================================================
def compare(request):
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
    
    years = HarvestPrice.objects.filter(year__in=CALENDAR_YEARS).values_list('year', flat=True).distinct().order_by('year')
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
                'price': float(crop.harvest_prices.filter(year__in=CALENDAR_YEARS).order_by('-year').first().price) if crop.harvest_prices.filter(year__in=CALENDAR_YEARS).exists() else None,
                'year': crop.harvest_prices.filter(year__in=CALENDAR_YEARS).order_by('-year').first().year if crop.harvest_prices.filter(year__in=CALENDAR_YEARS).exists() else None,
            } if crop.harvest_prices.filter(year__in=CALENDAR_YEARS).exists() else None,
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

# =========================================================
# REGIONS VIEW
# =========================================================
def regions_view(request):
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

# =========================================================
# API ENDPOINTS
# =========================================================
@require_http_methods(["GET"])
def api_crop_prices(request, crop_id):
    crop = get_object_or_404(Crop, id=crop_id)
    harvest_prices = crop.harvest_prices.filter(year__in=CALENDAR_YEARS).order_by('year')
    data = {
        'crop_name': _(crop.name),
        'years': [hp.year for hp in harvest_prices],
        'prices': [float(hp.price) for hp in harvest_prices],
    }
    return JsonResponse(data)

@require_http_methods(["GET"])
def api_daily_prices(request):
    try:
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
                logger.warning(f"Invalid date format in API: {date}")
        
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
        return JsonResponse({'data': data, 'success': True})
    except Exception as e:
        logger.error(f"API error in daily_prices: {e}")
        return JsonResponse({'error': str(e), 'success': False}, status=500)

# =========================================================
# CROP RECOMMENDATION - SINGLE VERSION (FIXED)
# =========================================================
def crop_recommendation(request, crop_id=None):
    """Get recommendations for specific crop or all crops in user's farms"""
    from datetime import datetime
    import math
    
    from marketPrice.models import Crop as MarketCrop, HarvestPrice, Profitability
    from farms.models import Farm
    
    recommendations = []
    sell_count = 0
    hold_count = 0
    monitor_count = 0
    
    # Get crops to process
    if crop_id:
        crops_to_process = [get_object_or_404(MarketCrop, id=crop_id)]
    else:
        # Show all crops with prices (filtered to calendar years)
        crops_to_process = MarketCrop.objects.filter(harvest_prices__year__in=CALENDAR_YEARS).distinct()
    
    for crop in crops_to_process:
        # Only use calendar years
        calendar_prices = crop.harvest_prices.filter(year__in=CALENDAR_YEARS)
        latest_price = calendar_prices.order_by('-year').first()
        
        if not latest_price:
            continue
        
        # Try to get profitability, but don't fail if it doesn't exist
        latest_profit = crop.profitability.filter(year__in=CALENDAR_YEARS).order_by('-year').first()
        
        # If no profit data exists, create a mock one
        if not latest_profit:
            # Get price history
            price_history = calendar_prices.order_by('year')
            prices = [float(p.price) for p in price_history]
            
            if not prices:
                continue
            
            # Estimate profit (simplified)
            avg_price = sum(prices) / len(prices)
            yield_tons = 1.5  # Default yield estimate
            production_cost = 4000000  # Default cost estimate
            
            # Adjust for specific crops
            crop_name_lower = crop.name.lower()
            if 'rice' in crop_name_lower or 'paddy' in crop_name_lower:
                yield_tons = 3.5
            elif 'sugarcane' in crop_name_lower:
                yield_tons = 50.0
            elif 'potato' in crop_name_lower or 'onion' in crop_name_lower:
                yield_tons = 12.0
            elif 'coffee' in crop_name_lower or 'tea' in crop_name_lower:
                yield_tons = 0.8
            elif 'betel' in crop_name_lower:
                yield_tons = 1.2
            
            revenue = avg_price * yield_tons
            estimated_profit = revenue - production_cost
            
            # Create mock profit object
            latest_profit = SimpleNamespace(
                year=latest_price.year,
                profit_per_acre=estimated_profit,
                yield_tons_per_acre=yield_tons,
                price_per_ton=latest_price.price
            )
        
        # Now continue with the rest of the function
        price_history = calendar_prices.order_by('year')
        prices = [float(p.price) for p in price_history]
        
        trend = "stable"
        price_change = 0
        if len(prices) >= 2:
            prev_price = prices[-2]
            curr_price = prices[-1]
            if prev_price > 0:
                price_change = ((curr_price - prev_price) / prev_price) * 100
            
            if price_change > 5:
                trend = "up"
            elif price_change < -5:
                trend = "down"
        
        # Get REAL data from database
        yield_tons = float(latest_profit.yield_tons_per_acre) if latest_profit.yield_tons_per_acre else 1.5
        profit_per_acre = float(latest_profit.profit_per_acre) if latest_profit.profit_per_acre else 0
        current_price = float(latest_price.price)
        
        # Calculate revenue
        revenue_per_acre = current_price * yield_tons if yield_tons > 0 else 0
        
        # Get production cost from constants
        production_cost = float(get_production_cost(crop.name))
        
        # If profit is 0 or negative, calculate it
        if profit_per_acre <= 0:
            profit_per_acre = revenue_per_acre - production_cost
        
        avg_price = sum(prices) / len(prices) if prices else 0
        
        current_price_viss = int(current_price / TON_TO_VISS)
        avg_price_viss = int(avg_price / TON_TO_VISS)
        
        # Calculate REALISTIC ROI
        roi = 0
        if production_cost > 0:
            roi = (profit_per_acre / production_cost) * 100
            if roi > 300:
                roi = 300
        
        # Make recommendations based on REAL data
        if roi > 200 and price_change > 10:
            recommendation = "SELL"
            recommendation_reason = _lazy("Exceptional profitability with rising prices. Sell now!")
            sell_count += 1
        elif roi > 150 and price_change > 5:
            recommendation = "SELL"
            recommendation_reason = _lazy("High profitability with upward trend. Consider selling.")
            sell_count += 1
        elif roi > 100 and price_change > 0:
            recommendation = "HOLD"
            recommendation_reason = _lazy("Strong profitability with stable prices. Hold for better returns.")
            hold_count += 1
        elif roi > 60 and price_change > -5:
            recommendation = "HOLD"
            recommendation_reason = _lazy("Good profitability with stable market. Hold and monitor.")
            hold_count += 1
        elif roi < 30 and price_change < -10:
            recommendation = "SELL"
            recommendation_reason = _lazy("Low profitability with falling prices. Consider selling.")
            sell_count += 1
        else:
            recommendation = "MONITOR"
            recommendation_reason = _lazy("Monitor market conditions. Wait for better opportunities.")
            monitor_count += 1
        
        export_cost_factor = get_export_cost_for_crop(crop.name, crop.category)
        export_profit = profit_per_acre * (1 - export_cost_factor)
        local_profit = profit_per_acre
        
        export_recommendation = "LOCAL"
        if export_profit > local_profit * 1.1:
            export_recommendation = "EXPORT"
        elif export_profit > local_profit * 0.9:
            export_recommendation = "CONSIDER_EXPORT"
        
        season_rec = "HOLD"
        if avg_price > 0 and current_price > avg_price * 1.15:
            season_rec = "SELL"
        elif avg_price > 0 and current_price < avg_price * 0.85:
            season_rec = "HOLD"
        
        recommendations.append({
            'crop': crop,
            'crop_name': _(crop.name),
            'latest_price': latest_price,
            'latest_profit': latest_profit,
            'current_price_viss': current_price_viss,
            'avg_price_viss': avg_price_viss,
            'profit_acre': int(profit_per_acre),
            'roi': int(roi),
            'yield_tons_per_acre': yield_tons,
            'production_cost': int(production_cost),
            'revenue_per_acre': int(revenue_per_acre),
            'price_change': price_change,
            'trend': trend,
            'recommendation': recommendation,
            'recommendation_reason': recommendation_reason,
            'export_recommendation': export_recommendation,
            'season_recommendation': season_rec,
        })
    
    recommendations.sort(key=lambda x: x['profit_acre'], reverse=True)
    context = {
        'recommendations': recommendations,
        'current_date': datetime.now(),
        'total_crops': len(recommendations),
        'sell_count': sell_count,
        'hold_count': hold_count,
        'monitor_count': monitor_count,
    }
    return render(request, 'marketPrice/recommendations.html', context)

# =========================================================
# REGIONS VIEW (Full Analytics Version)
# =========================================================
import json
import logging
from django.db.models import Sum, Avg, Max, Min, Count

logger = logging.getLogger(__name__)

def regions_analytics_view(request):
    """Display regional production data with insights and analytics"""
    
    regional_data = RegionalProduction.objects.all().order_by('region', 'crop_category', 'year')
    
    selected_region = request.GET.get('region')
    selected_category = request.GET.get('category')
    
    if selected_region:
        regional_data = regional_data.filter(region=selected_region)
    if selected_category:
        regional_data = regional_data.filter(crop_category=selected_category)
    
    raw_regions = RegionalProduction.objects.values_list('region', flat=True).distinct()
    regions = sorted(list(set(raw_regions)))
    
    raw_categories = RegionalProduction.objects.values_list('crop_category', flat=True).distinct()
    categories = sorted(list(set(raw_categories)))
    
    total_production = regional_data.aggregate(Sum('production_tons'))['production_tons__sum'] or 0
    total_sown = regional_data.aggregate(Sum('sown_acres'))['sown_acres__sum'] or 0
    total_harvested = regional_data.aggregate(Sum('harvested_acres'))['harvested_acres__sum'] or 0
    record_count = regional_data.count()
    
    avg_yield = 0
    if total_harvested > 0:
        avg_yield = total_production / total_harvested
    
    harvest_rate = 0
    if total_sown > 0:
        harvest_rate = (total_harvested / total_sown) * 100
    
    top_region_data = regional_data.values('region').annotate(
        total_prod=Sum('production_tons')
    ).order_by('-total_prod').first()
    top_region = top_region_data['region'] if top_region_data else 'N/A'
    top_region_prod = float(top_region_data['total_prod']) if top_region_data else 0
    
    top_crop_data = regional_data.values('crop_category').annotate(
        total_prod=Sum('production_tons')
    ).order_by('-total_prod').first()
    top_crop = top_crop_data['crop_category'] if top_crop_data else 'N/A'
    top_crop_prod = float(top_crop_data['total_prod']) if top_crop_data else 0
    
    years = regional_data.values_list('year', flat=True).distinct().order_by('year')
    years_list = list(years)
    yoy_growth = 0
    
    if len(years_list) >= 2:
        latest_year = years_list[-1]
        prev_year = years_list[-2]
        
        latest_prod = regional_data.filter(year=latest_year).aggregate(Sum('production_tons'))['production_tons__sum'] or 0
        prev_prod = regional_data.filter(year=prev_year).aggregate(Sum('production_tons'))['production_tons__sum'] or 0
        
        if prev_prod > 0:
            yoy_growth = ((latest_prod - prev_prod) / prev_prod) * 100
    
    yearly_production = {}
    for year in years_list:
        yearly_production[year] = regional_data.filter(year=year).aggregate(Sum('production_tons'))['production_tons__sum'] or 0
    
    regional_data_list = []
    region_years = {}
    all_records = list(regional_data)
    
    prev_record_lookup = {}
    for item in all_records:
        key = (item.region, item.crop_category, item.year)
        prev_records = [r for r in all_records if r.region == item.region and r.crop_category == item.crop_category and r.year < item.year]
        if prev_records:
            prev_record_lookup[key] = max(prev_records, key=lambda x: x.year)
    
    for item in all_records:
        growth = 0
        key = (item.region, item.crop_category, item.year)
        prev_record = prev_record_lookup.get(key)
        
        if prev_record and prev_record.production_tons and prev_record.production_tons > 0:
            growth = ((float(item.production_tons) - float(prev_record.production_tons)) / float(prev_record.production_tons)) * 100
        
        harvest_rate_item = 0
        if item.sown_acres and item.sown_acres > 0:
            harvest_rate_item = (float(item.harvested_acres) / float(item.sown_acres)) * 100
        
        regional_data_list.append({
            'region': item.region,
            'crop_category': _(item.crop_category) if item.crop_category else '',
            'crop_category_raw': item.crop_category,
            'year': item.year,
            'sown_acres': float(item.sown_acres) if item.sown_acres else 0,
            'harvested_acres': float(item.harvested_acres) if item.harvested_acres else 0,
            'production_tons': float(item.production_tons) if item.production_tons else 0,
            'measurement_type': item.measurement_type,
            'growth_percentage': growth,
            'harvest_rate': harvest_rate_item,
        })
        
        if item.region not in region_years:
            region_years[item.region] = {}
        if item.year not in region_years[item.region]:
            region_years[item.region][item.year] = 0
        region_years[item.region][item.year] += float(item.production_tons or 0)
    
    chart_regions = list(region_years.keys())
    chart_years = sorted(set([y for region in region_years.values() for y in region.keys()]))
    
    chart_datasets = []
    colors = ['#2e7d32', '#4caf50', '#8bc34a', '#cddc39', '#ff9800', '#ff5722', '#1976d2', '#9c27b0', '#00bcd4', '#f44336']
    
    for i, region in enumerate(chart_regions):
        region_data = []
        for year in chart_years:
            region_data.append(region_years[region].get(year, 0))
        chart_datasets.append({
            'label': region,
            'data': region_data,
            'backgroundColor': colors[i % len(colors)] + '80',
            'borderColor': colors[i % len(colors)],
            'borderWidth': 2,
            'borderRadius': 4,
        })
    
    insights = []
    
    if yoy_growth > 10:
        insights.append({
            'title': _('Strong Growth'),
            'description': _('Production increased by {:.1f}% compared to last year').format(yoy_growth),
            'icon': 'bi-arrow-up-circle-fill',
            'color': 'success',
            'value': '{:.1f}%'.format(yoy_growth)
        })
    elif yoy_growth > 0:
        insights.append({
            'title': _('Moderate Growth'),
            'description': _('Production grew by {:.1f}% year-over-year').format(yoy_growth),
            'icon': 'bi-arrow-up-circle',
            'color': 'info',
            'value': '{:.1f}%'.format(yoy_growth)
        })
    elif yoy_growth < -5:
        insights.append({
            'title': _('Significant Decline'),
            'description': _('Production decreased by {:.1f}% compared to last year').format(abs(yoy_growth)),
            'icon': 'bi-arrow-down-circle-fill',
            'color': 'danger',
            'value': '{:.1f}%'.format(yoy_growth)
        })
    else:
        insights.append({
            'title': _('Stable Production'),
            'description': _('Production remained stable with {:.1f}% change').format(yoy_growth),
            'icon': 'bi-dash-circle',
            'color': 'secondary',
            'value': '{:.1f}%'.format(yoy_growth)
        })
    
    if harvest_rate > 85:
        insights.append({
            'title': _('Excellent Harvest Rate'),
            'description': _('{:.1f}% of sown area was successfully harvested').format(harvest_rate),
            'icon': 'bi-check-circle-fill',
            'color': 'success',
            'value': '{:.1f}%'.format(harvest_rate)
        })
    elif harvest_rate > 70:
        insights.append({
            'title': _('Good Harvest Rate'),
            'description': _('{:.1f}% of sown area was harvested').format(harvest_rate),
            'icon': 'bi-check-circle',
            'color': 'warning',
            'value': '{:.1f}%'.format(harvest_rate)
        })
    else:
        insights.append({
            'title': _('Low Harvest Rate'),
            'description': _('Only {:.1f}% of sown area was harvested - investigate crop losses').format(harvest_rate),
            'icon': 'bi-exclamation-triangle-fill',
            'color': 'danger',
            'value': '{:.1f}%'.format(harvest_rate)
        })
    
    insights.append({
        'title': _('Top Producing Region'),
        'description': _('{} leads with {:,} tons of production').format(top_region, int(top_region_prod)),
        'icon': 'bi-trophy-fill',
        'color': 'warning',
        'value': top_region
    })
    
    insights.append({
        'title': _('Most Produced Crop'),
        'description': _('{} is the most produced crop with {:,} tons').format(top_crop, int(top_crop_prod)),
        'icon': 'bi-seedling-fill',
        'color': 'success',
        'value': top_crop
    })
    
    if total_production > 1000000:
        prod_display = '{:.1f}M'.format(total_production / 1000000)
    elif total_production > 1000:
        prod_display = '{:,}'.format(int(total_production))
    else:
        prod_display = '{:.0f}'.format(total_production)
    
    insights.append({
        'title': _('Total Production'),
        'description': _('Total production across all regions and crops'),
        'icon': 'bi-box-seam-fill',
        'color': 'primary',
        'value': '{} {}'.format(prod_display, _('tons'))
    })
    
    context = {
        'regional_data': regional_data_list,
        'regions': regions,
        'categories': [_(cat) for cat in categories],
        'selected_region': selected_region,
        'selected_category': selected_category,
        'has_data': bool(regional_data_list),
        'record_count': record_count,
        'total_production': total_production,
        'total_sown_acres': total_sown,
        'total_harvested_acres': total_harvested,
        'avg_yield_per_acre': avg_yield,
        'harvest_rate': harvest_rate,
        'yoy_growth': yoy_growth,
        'top_region': top_region,
        'top_region_production': top_region_prod,
        'top_crop': top_crop,
        'top_crop_production': top_crop_prod,
        'yearly_production': yearly_production,
        'years': years_list,
        'chart_regions': json.dumps(chart_regions),
        'chart_years': json.dumps(chart_years),
        'chart_datasets': json.dumps(chart_datasets),
        'insights': insights,
    }
    
    return render(request, 'marketPrice/region_analysis.html', context)

# =========================================================
# BEST MARKET FINDER - FIXED
# =========================================================
@login_required
def best_market_finder(request):
    from marketPrice.models import Crop as MarketCrop, HarvestPrice, RegionalProduction
    from farms.models import Farm
    
    user_farms = Farm.objects.filter(owner=request.user)
    user_locations = list(user_farms.values_list('location', flat=True).distinct())
    
    selected_crop_id = request.GET.get('crop')
    selected_crop = None
    
    all_crops = MarketCrop.objects.filter(harvest_prices__year__in=CALENDAR_YEARS).distinct().order_by('name')
    
    if selected_crop_id and selected_crop_id.isdigit():
        try:
            selected_crop = MarketCrop.objects.get(id=int(selected_crop_id))
        except MarketCrop.DoesNotExist:
            selected_crop = None
    
    if not selected_crop:
        context = {
            'all_crops': all_crops,
            'selected_crop': None,
            'market_data': [],
            'recommendations': [],
            'user_locations': user_locations,
            'has_data': False,
            'page_title': _('Best Market Finder'),
        }
        return render(request, 'marketPrice/best_market_finder.html', context)
    
    latest_price = selected_crop.harvest_prices.filter(year__in=CALENDAR_YEARS).order_by('-year').first()
    if not latest_price:
        context = {
            'all_crops': all_crops,
            'selected_crop': selected_crop,
            'market_data': [],
            'recommendations': [],
            'user_locations': user_locations,
            'has_data': False,
            'page_title': _('Best Market Finder'),
            'error': _('No price data available for this crop'),
        }
        return render(request, 'marketPrice/best_market_finder.html', context)
    
    base_price_per_ton = float(latest_price.price)
    base_price_per_viss = base_price_per_ton / 612.4
    
    regional_data = RegionalProduction.objects.filter(
        crop_category=selected_crop.name
    ).order_by('region', '-year')
    
    market_data = []
    seen_regions = set()
    
    REGION_MULTIPLIERS = {
        'Yangon': 1.10,
        'Mandalay': 1.08,
        'Nay Pyi Taw': 1.05,
        'Bago': 0.98,
        'Ayeyawady': 0.95,
        'Sagaing': 0.92,
        'Magway': 0.95,
        'Shan': 0.90,
        'Kachin': 0.85,
        'Kayah': 0.82,
        'Kayin': 0.85,
        'Mon': 0.92,
        'Rakhine': 0.88,
        'Tanintharyi': 0.85,
        'Chin': 0.88,
    }
    
    for item in regional_data:
        region = item.region
        if region in seen_regions:
            continue
        seen_regions.add(region)
        
        region_records = RegionalProduction.objects.filter(
            region=region,
            crop_category=selected_crop.name
        ).order_by('-year')
        
        if not region_records.exists():
            continue
        
        latest_record = region_records.first()
        
        production_trend = 'stable'
        if region_records.count() >= 2:
            records_list = list(region_records.order_by('year'))
            first_prod = float(records_list[0].production_tons) if records_list[0].production_tons else 0
            last_prod = float(records_list[-1].production_tons) if records_list[-1].production_tons else 0
            if first_prod > 0:
                growth = ((last_prod - first_prod) / first_prod) * 100
                if growth > 15:
                    production_trend = 'growing'
                elif growth < -15:
                    production_trend = 'declining'
        
        region_multiplier = REGION_MULTIPLIERS.get(region, 1.0)
        
        prod_factor = 1.0
        if latest_record.production_tons:
            prod_tons = float(latest_record.production_tons)
            if prod_tons < 100:
                prod_factor = 1.25
            elif prod_tons < 500:
                prod_factor = 1.15
            elif prod_tons < 2000:
                prod_factor = 1.05
            elif prod_tons < 5000:
                prod_factor = 0.95
            else:
                prod_factor = 0.85
        
        estimated_price_per_viss = base_price_per_viss * region_multiplier * prod_factor
        
        demand_rating = 'medium'
        if production_trend == 'declining' and prod_factor > 1.0:
            demand_rating = 'high'
        elif production_trend == 'growing' and prod_factor < 1.0:
            demand_rating = 'low'
        elif prod_factor > 1.15:
            demand_rating = 'high'
        
        is_user_region = region in user_locations
        
        market_data.append({
            'region': region,
            'region_translated': _(region),
            'estimated_price': round(estimated_price_per_viss, 0),
            'production_tons': float(latest_record.production_tons) if latest_record.production_tons else 0,
            'demand_rating': demand_rating,
            'demand_rating_translated': _(demand_rating.title()),
            'demand_color': 'success' if demand_rating == 'high' else 'warning' if demand_rating == 'medium' else 'danger',
            'is_user_region': is_user_region,
            'trend': production_trend,
            'trend_translated': _(production_trend.title()),
        })
    
    if not market_data:
        default_regions = ['Yangon', 'Mandalay', 'Nay Pyi Taw', 'Bago', 'Ayeyawady', 'Sagaing']
        for region in default_regions:
            if region not in seen_regions:
                region_multiplier = REGION_MULTIPLIERS.get(region, 1.0)
                estimated_price = base_price_per_viss * region_multiplier
                is_user_region = region in user_locations
                market_data.append({
                    'region': region,
                    'region_translated': _(region),
                    'estimated_price': round(estimated_price, 0),
                    'production_tons': 0,
                    'demand_rating': 'medium',
                    'demand_rating_translated': _('Medium'),
                    'demand_color': 'warning',
                    'is_user_region': is_user_region,
                    'trend': 'stable',
                    'trend_translated': _('Stable'),
                })
    
    market_data.sort(key=lambda x: x['estimated_price'], reverse=True)
    
    recommendations = []
    
    if market_data:
        best = market_data[0]
        recommendations.append({
            'type': 'best_price',
            'title': _('💰 Best Price'),
            'description': _('Sell {crop} in {region} for the best price of {price:,} Ks/Viss').format(
                crop=_(selected_crop.name),
                region=best['region_translated'],
                price=int(best['estimated_price'])
            ),
            'region': best['region'],
            'icon': 'bi-trophy',
            'color': 'success',
        })
        
        if user_locations:
            user_region_data = [m for m in market_data if m['is_user_region']]
            if user_region_data:
                user_best = user_region_data[0]
                recommendations.append({
                    'type': 'local',
                    'title': _('📍 Your Location'),
                    'description': _('In your region ({region}), price is {price:,} Ks/Viss').format(
                        region=user_best['region_translated'],
                        price=int(user_best['estimated_price'])
                    ),
                    'region': user_best['region'],
                    'icon': 'bi-house',
                    'color': 'info',
                })
        
        high_demand = [m for m in market_data if m['demand_rating'] == 'high']
        if high_demand:
            top_demand = high_demand[0]
            recommendations.append({
                'type': 'high_demand',
                'title': _('📈 High Demand'),
                'description': _('{region} has high demand for {crop} with price {price:,} Ks/Viss').format(
                    crop=_(selected_crop.name),
                    region=top_demand['region_translated'],
                    price=int(top_demand['estimated_price'])
                ),
                'region': top_demand['region'],
                'icon': 'bi-graph-up-arrow',
                'color': 'warning',
            })
    
    chart_regions = [m['region'] for m in market_data[:10]]
    chart_prices = [m['estimated_price'] for m in market_data[:10]]
    chart_demand = [m['demand_rating'] for m in market_data[:10]]
    
    context = {
        'all_crops': all_crops,
        'selected_crop': selected_crop,
        'selected_crop_name': _(selected_crop.name),
        'market_data': market_data,
        'recommendations': recommendations,
        'user_locations': user_locations,
        'has_data': bool(market_data),
        'chart_regions': json.dumps(chart_regions),
        'chart_prices': json.dumps(chart_prices),
        'chart_demand': json.dumps(chart_demand),
        'page_title': _('Best Market Finder'),
    }
    
    return render(request, 'marketPrice/best_market_finder.html', context)

# =========================================================
# AI CHAT API
# =========================================================
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# Try to import RAG service
try:
    from .services.rag_service import AgriRAGService
    rag_service = AgriRAGService()
    print("✓ RAG service initialized")
except Exception as e:
    print(f"⚠ RAG service error: {e}")
    rag_service = None

@csrf_exempt
def chat_api(request):
    """
    Chat API endpoint for AgriVision AI
    GET: Returns a friendly message
    POST: Expects JSON with {"query": "your question"}
    """
    
    if request.method == "GET":
        return JsonResponse({
            'success': True,
            'message': 'AgriVision AI Chat API is running. Send a POST request with your query.',
            'example': {'query': 'What is the price of bean?'}
        })
    
    if request.method != "POST":
        return JsonResponse({
            'success': False,
            'error': 'Method not allowed. Use POST for chat requests.'
        }, status=405)
    
    if rag_service is None:
        return JsonResponse({
            'success': False,
            'error': 'AI service is not available. Please try again later.'
        }, status=503)
    
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        k = data.get('k', 8)
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Please enter a question.'
            }, status=400)
        
        result = rag_service.generate_response(query, k=k)
        
        return JsonResponse({
            'success': True,
            'response': result['response'],
            'sources': result['sources'],
            'query': query
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON format. Please send valid JSON.'
        }, status=400)
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error: {str(e)}'
        }, status=500)