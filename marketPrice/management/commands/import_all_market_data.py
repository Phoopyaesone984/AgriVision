import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import models
from marketPrice.models import Crop, HarvestPrice, Profitability, RegionalProduction

class Command(BaseCommand):
    help = 'Import all market data including crops, harvest prices, and profitability'

    def add_arguments(self, parser):
        parser.add_argument(
            '--crops',
            nargs='+',
            type=str,
            help='Specific crop names to import (default: all)'
        )
        parser.add_argument(
            '--years',
            nargs='+',
            type=str,
            default=['2022', '2023', '2024', '2025', '2026'],
            help='Years to generate data for (default: 2022-2026)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before importing'
        )

    def handle(self, *args, **options):
        years = options['years']
        crop_names = options['crops']
        clear_existing = options['clear']

        self.stdout.write(self.style.SUCCESS('🚀 Starting market data import...'))
        
        # ============================================================
        # COMPREHENSIVE CROP PRICE PROFILES
        # ============================================================
        CROP_PRICE_PROFILES = {
            # === FIELD CROPS ===
            'Wheat': {'base': 6000000, 'volatility': 0.15, 'trend': 0.08},
            'Rice': {'base': 3500000, 'volatility': 0.12, 'trend': 0.05},
            'Paddy': {'base': 3200000, 'volatility': 0.10, 'trend': 0.03},
            'Maize': {'base': 2500000, 'volatility': 0.10, 'trend': 0.04},
            'Corn': {'base': 2800000, 'volatility': 0.12, 'trend': 0.04},
            'Sugarcane': {'base': 1800000, 'volatility': 0.08, 'trend': 0.02},
            'Tapioca': {'base': 2500000, 'volatility': 0.10, 'trend': 0.02},
            'Cotton': {'base': 4500000, 'volatility': 0.14, 'trend': 0.05},
            'Paddy (Monsoon)': {'base': 3100000, 'volatility': 0.10, 'trend': 0.03},
            'Paddy (Summer)': {'base': 3300000, 'volatility': 0.10, 'trend': 0.03},
            
            # === VEGETABLES ===
            'Onion': {'base': 3000000, 'volatility': 0.22, 'trend': -0.03},
            'Potato': {'base': 2800000, 'volatility': 0.16, 'trend': 0.06},
            'Tomato': {'base': 4000000, 'volatility': 0.20, 'trend': 0.05},
            'Chillies': {'base': 7000000, 'volatility': 0.25, 'trend': -0.05},
            'Chillies (Dry)': {'base': 11000000, 'volatility': 0.15, 'trend': 0.02},
            'Chillies (Green)': {'base': 5000000, 'volatility': 0.20, 'trend': 0.05},
            'Garlic': {'base': 6000000, 'volatility': 0.18, 'trend': 0.07},
            'Garlic (Dry)': {'base': 10000000, 'volatility': 0.15, 'trend': 0.02},
            'Vegetable': {'base': 4500000, 'volatility': 0.18, 'trend': 0.05},
            'Cabbage': {'base': 2500000, 'volatility': 0.20, 'trend': 0.03},
            'Cauliflower': {'base': 2800000, 'volatility': 0.20, 'trend': 0.03},
            'Brinjal': {'base': 3000000, 'volatility': 0.18, 'trend': 0.04},
            'Okra': {'base': 3200000, 'volatility': 0.20, 'trend': 0.04},
            'Pumpkin': {'base': 2200000, 'volatility': 0.18, 'trend': 0.02},
            
            # === PULSES & OILSEEDS ===
            'Pulse': {'base': 3000000, 'volatility': 0.12, 'trend': 0.03},
            'Bean': {'base': 2800000, 'volatility': 0.12, 'trend': 0.03},
            'Soybean': {'base': 3800000, 'volatility': 0.12, 'trend': 0.06},
            'Groundnut': {'base': 3500000, 'volatility': 0.12, 'trend': 0.04},
            'Groundnut (Rain)': {'base': 3400000, 'volatility': 0.12, 'trend': 0.04},
            'Groundnut (Winter)': {'base': 3600000, 'volatility': 0.12, 'trend': 0.04},
            'Groundnut (a) Rain': {'base': 3400000, 'volatility': 0.12, 'trend': 0.04},
            'Groundnut (b) Winter': {'base': 3600000, 'volatility': 0.12, 'trend': 0.04},
            'Sesamum': {'base': 2800000, 'volatility': 0.18, 'trend': 0.06},
            'Sesamum (Early)': {'base': 2700000, 'volatility': 0.18, 'trend': 0.06},
            'Sesamum (Late)': {'base': 2900000, 'volatility': 0.18, 'trend': 0.06},
            'Sesamum (a) Early': {'base': 2700000, 'volatility': 0.18, 'trend': 0.06},
            'Sesamum (b) Late': {'base': 2900000, 'volatility': 0.18, 'trend': 0.06},
            'Gram': {'base': 3200000, 'volatility': 0.12, 'trend': 0.04},
            'Gram (Chick Pea)': {'base': 3200000, 'volatility': 0.12, 'trend': 0.04},
            'Matpe': {'base': 3000000, 'volatility': 0.12, 'trend': 0.04},
            'Matpe (Black Gram)': {'base': 3000000, 'volatility': 0.12, 'trend': 0.04},
            'Mustard': {'base': 2500000, 'volatility': 0.18, 'trend': 0.04},
            'Sunflower': {'base': 3000000, 'volatility': 0.18, 'trend': 0.05},
            
            # === PULSES - MYANMAR NAMES ===
            'Penauk (Krishna Mung)': {'base': 3500000, 'volatility': 0.12, 'trend': 0.05},
            'Penauk': {'base': 3500000, 'volatility': 0.12, 'trend': 0.05},
            'Pegyi (Lablab Bean)': {'base': 2800000, 'volatility': 0.12, 'trend': 0.04},
            'Pegyi': {'base': 2800000, 'volatility': 0.12, 'trend': 0.04},
            'Pebyugale (Duffin Bean)': {'base': 2600000, 'volatility': 0.12, 'trend': 0.03},
            'Pebyugale': {'base': 2600000, 'volatility': 0.12, 'trend': 0.03},
            'Peyazar (Lentil Bean)': {'base': 3000000, 'volatility': 0.12, 'trend': 0.04},
            'Peyazar': {'base': 3000000, 'volatility': 0.12, 'trend': 0.04},
            'Peyin (Rice Bean)': {'base': 2700000, 'volatility': 0.12, 'trend': 0.03},
            'Peyin': {'base': 2700000, 'volatility': 0.12, 'trend': 0.03},
            'Pedisein (Green Gram)': {'base': 3200000, 'volatility': 0.12, 'trend': 0.04},
            'Pedisein': {'base': 3200000, 'volatility': 0.12, 'trend': 0.04},
            'Pesingon (Pigeon Pea)': {'base': 3100000, 'volatility': 0.12, 'trend': 0.04},
            'Pesingon': {'base': 3100000, 'volatility': 0.12, 'trend': 0.04},
            'Pelun': {'base': 2800000, 'volatility': 0.12, 'trend': 0.03},
            'Sultani': {'base': 3300000, 'volatility': 0.12, 'trend': 0.05},
            'Sultapya': {'base': 3100000, 'volatility': 0.12, 'trend': 0.04},
            'Peboke (Soy Bean)': {'base': 3600000, 'volatility': 0.12, 'trend': 0.05},
            'Peboke': {'base': 3600000, 'volatility': 0.12, 'trend': 0.05},
            'Bocate (Cow Pea)': {'base': 2900000, 'volatility': 0.12, 'trend': 0.03},
            'Bocate': {'base': 2900000, 'volatility': 0.15, 'trend': 0.04},
            'Sadawpe (Garden Pea)': {'base': 3200000, 'volatility': 0.12, 'trend': 0.04},
            'Sadawpe': {'base': 3200000, 'volatility': 0.12, 'trend': 0.04},
            'Butter Bean': {'base': 2800000, 'volatility': 0.15, 'trend': 0.04},
            'Butter bean': {'base': 2800000, 'volatility': 0.15, 'trend': 0.04},
            'Pegya': {'base': 2800000, 'volatility': 0.12, 'trend': 0.04},
            'Pegya(Lima bean)': {'base': 2800000, 'volatility': 0.12, 'trend': 0.04},
            
            # === FRUITS ===
            'Mango': {'base': 5000000, 'volatility': 0.22, 'trend': 0.08},
            'Fruit': {'base': 5000000, 'volatility': 0.20, 'trend': 0.05},
            'Banana': {'base': 3500000, 'volatility': 0.18, 'trend': 0.04},
            'Orange': {'base': 4500000, 'volatility': 0.18, 'trend': 0.05},
            'Papaya': {'base': 2800000, 'volatility': 0.20, 'trend': 0.04},
            'Watermelon': {'base': 3000000, 'volatility': 0.25, 'trend': 0.03},
            'Dragon Fruit': {'base': 6000000, 'volatility': 0.20, 'trend': 0.10},
            'Jackfruit': {'base': 2500000, 'volatility': 0.18, 'trend': 0.03},
            'Strawberry': {'base': 8000000, 'volatility': 0.20, 'trend': 0.10},
            'Coconut': {'base': 4000000, 'volatility': 0.15, 'trend': 0.04},
            
            # === CASH CROPS ===
            'Coffee': {'base': 5500000, 'volatility': 0.15, 'trend': 0.12},
            'Tea': {'base': 4500000, 'volatility': 0.15, 'trend': 0.05},
            'Tea (Green)': {'base': 4000000, 'volatility': 0.15, 'trend': 0.05},
            'Tobacco': {'base': 8000000, 'volatility': 0.20, 'trend': -0.08},
            'Tobacco(dry)(Myanmar)': {'base': 7500000, 'volatility': 0.20, 'trend': -0.08},
            'Tobacco(dry)(Virginia)': {'base': 8000000, 'volatility': 0.20, 'trend': -0.08},
            'Rubber': {'base': 3500000, 'volatility': 0.15, 'trend': 0.03},
            'Jute': {'base': 2800000, 'volatility': 0.14, 'trend': 0.02},
            'Kenaf': {'base': 2800000, 'volatility': 0.14, 'trend': 0.03},
            
            # === COTTON VARIETIES ===
            'Cotton (Long Staple)': {'base': 4800000, 'volatility': 0.14, 'trend': 0.05},
            'Cotton (Mahlaing 5/6)': {'base': 4500000, 'volatility': 0.14, 'trend': 0.05},
            'Cotton (Wagyi)': {'base': 4200000, 'volatility': 0.14, 'trend': 0.05},
            'Cotton (a) Wagyi': {'base': 4200000, 'volatility': 0.14, 'trend': 0.05},
            'Cotton (b) Mahlaing 5/6': {'base': 4500000, 'volatility': 0.14, 'trend': 0.05},
            'Cotton (c) Long Staple': {'base': 4800000, 'volatility': 0.14, 'trend': 0.05},
            
            # === NUTS & SPECIALTY ===
            'Betel Nut': {'base': 8500000, 'volatility': 0.15, 'trend': 0.04},
            'Betel Leaves': {'base': 6124000, 'volatility': 0.20, 'trend': 0.05},
            
            # Default
            'default': {'base': 5000000, 'volatility': 0.15, 'trend': 0.05},
        }

        # ============================================================
        # YIELD PER ACRE (in tons) - ADD MISSING CROPS
        # ============================================================
        YIELD_PER_ACRE = {
            # Field crops
            'rice': 3.5, 'paddy': 3.5, 'wheat': 2.5, 'maize': 4.0, 
            'corn': 4.0, 'sugarcane': 50.0, 'tapioca': 25.0, 'cotton': 1.5,
            
            # Vegetables
            'onion': 12.0, 'potato': 15.0, 'tomato': 10.0, 'cabbage': 20.0,
            'cauliflower': 18.0, 'brinjal': 12.0, 'okra': 8.0, 'pumpkin': 15.0,
            'garlic': 5.0, 'chillies': 1.5, 'vegetable': 10.0,
            
            # Pulses & Oilseeds
            'pulse': 1.2, 'bean': 1.2, 'soybean': 1.5, 'groundnut': 0.8,
            'sesamum': 0.8, 'gram': 1.2, 'matpe': 1.0, 'penauk': 1.2,
            'pegyi': 1.2, 'pebyugale': 1.0, 'peyazar': 1.2, 'peyin': 1.0,
            'pedisein': 1.2, 'pesingon': 1.0, 'pelun': 1.0, 'sultani': 1.2,
            'sultapya': 1.2, 'peboke': 1.5, 'bocate': 1.0, 'sadawpe': 1.2,
            'mustard': 0.8, 'sunflower': 0.8, 'butter bean': 1.0, 'pegya': 1.0,
            
            # Fruits
            'mango': 8.0, 'banana': 15.0, 'orange': 10.0, 'papaya': 20.0,
            'watermelon': 25.0, 'dragon fruit': 5.0, 'jackfruit': 12.0,
            'fruit': 5.0, 'strawberry': 3.0, 'coconut': 2.0,
            
            # Cash crops
            'coffee': 0.8, 'tea': 0.8, 'tobacco': 2.0, 'rubber': 1.0,
            'jute': 2.0, 'kenaf': 2.0,
            
            # Others
            'betel': 1.2,
            
            'default': 1.5,
        }

        # ============================================================
        # PRODUCTION COST PER ACRE (in Kyat) - ADD MISSING CROPS
        # ============================================================
        PRODUCTION_COST = {
            'rice': 3500000, 'paddy': 3500000, 'wheat': 4000000,
            'maize': 4000000, 'corn': 4000000, 'sugarcane': 6000000,
            'tapioca': 3500000, 'cotton': 4500000,
            'onion': 5000000, 'potato': 5500000, 'tomato': 6000000,
            'cabbage': 4000000, 'cauliflower': 4000000, 'brinjal': 4500000,
            'okra': 4000000, 'pumpkin': 3500000, 'garlic': 8000000,
            'chillies': 7000000, 'vegetable': 5000000,
            'pulse': 2500000, 'bean': 2500000, 'soybean': 3000000,
            'groundnut': 3000000, 'sesamum': 2000000, 'gram': 2800000,
            'matpe': 2600000, 'penauk': 2800000, 'pegyi': 2600000,
            'pebyugale': 2500000, 'peyazar': 2700000, 'peyin': 2500000,
            'pedisein': 2800000, 'pesingon': 2700000, 'pelun': 2500000,
            'sultani': 2800000, 'sultapya': 2700000, 'peboke': 3000000,
            'bocate': 2600000, 'sadawpe': 2800000, 'mustard': 2200000,
            'sunflower': 2500000, 'butter bean': 2500000, 'pegya': 2500000,
            'mango': 5000000, 'banana': 4000000, 'orange': 4500000,
            'papaya': 3500000, 'watermelon': 4000000, 'dragon fruit': 6000000,
            'jackfruit': 3500000, 'fruit': 5000000, 'strawberry': 7000000,
            'coconut': 4000000,
            'coffee': 5000000, 'tea': 4000000, 'tobacco': 8000000,
            'rubber': 3500000, 'jute': 3000000, 'kenaf': 3000000,
            'betel': 6000000,
            'default': 4000000,
        }

        # ============================================================
        # COMPREHENSIVE REGIONAL PRODUCTION DATA - 15 States/Regions
        # ============================================================
        REGIONAL_DATA = {
            'Yangon': {
                'Rice': 250000, 'Paddy': 200000, 'Bean': 80000,
                'Onion': 50000, 'Potato': 40000, 'Tomato': 30000,
                'Vegetable': 60000, 'Fruit': 40000, 'Mango': 25000,
            },
            'Mandalay': {
                'Rice': 150000, 'Paddy': 120000, 'Bean': 60000,
                'Onion': 40000, 'Potato': 30000, 'Tomato': 25000,
                'Sesamum': 35000, 'Groundnut': 30000, 'Cotton': 20000,
                'Mango': 30000, 'Vegetable': 40000,
            },
            'Nay Pyi Taw': {
                'Rice': 100000, 'Paddy': 80000, 'Bean': 40000,
                'Onion': 30000, 'Potato': 25000, 'Vegetable': 35000,
                'Mango': 15000, 'Tomato': 20000,
            },
            'Bago': {
                'Rice': 200000, 'Paddy': 180000, 'Sugarcane': 50000,
                'Bean': 50000, 'Onion': 30000, 'Potato': 25000,
                'Tapioca': 30000, 'Rubber': 20000,
            },
            'Ayeyawady': {
                'Rice': 300000, 'Paddy': 280000, 'Bean': 60000,
                'Onion': 40000, 'Potato': 35000, 'Tomato': 20000,
                'Mango': 20000, 'Vegetable': 50000,
            },
            'Sagaing': {
                'Rice': 120000, 'Paddy': 100000, 'Wheat': 40000,
                'Bean': 40000, 'Sesamum': 30000, 'Groundnut': 25000,
                'Cotton': 30000, 'Onion': 25000,
            },
            'Magway': {
                'Rice': 80000, 'Paddy': 70000, 'Sesamum': 40000,
                'Groundnut': 35000, 'Cotton': 50000, 'Bean': 30000,
                'Chillies': 20000, 'Onion': 20000,
            },
            'Shan': {
                'Rice': 100000, 'Paddy': 80000, 'Corn': 40000,
                'Maize': 40000, 'Potato': 30000, 'Tomato': 25000,
                'Strawberry': 15000, 'Tea': 20000, 'Coffee': 15000,
                'Mango': 15000, 'Vegetable': 30000,
            },
            'Kachin': {
                'Rice': 60000, 'Paddy': 50000, 'Corn': 20000,
                'Maize': 20000, 'Vegetable': 20000, 'Fruit': 15000,
            },
            'Kayah': {
                'Rice': 40000, 'Paddy': 35000, 'Bean': 20000,
                'Corn': 15000, 'Vegetable': 15000,
            },
            'Kayin': {
                'Rice': 50000, 'Paddy': 45000, 'Bean': 25000,
                'Rubber': 30000, 'Vegetable': 20000,
            },
            'Mon': {
                'Rice': 60000, 'Paddy': 50000, 'Bean': 25000,
                'Rubber': 40000, 'Vegetable': 20000, 'Mango': 15000,
            },
            'Rakhine': {
                'Rice': 70000, 'Paddy': 60000, 'Bean': 25000,
                'Vegetable': 20000, 'Fruit': 15000,
            },
            'Tanintharyi': {
                'Rice': 50000, 'Paddy': 40000, 'Bean': 20000,
                'Rubber': 30000, 'Mango': 15000, 'Vegetable': 15000,
            },
            'Chin': {
                'Rice': 30000, 'Paddy': 25000, 'Corn': 15000,
                'Vegetable': 15000, 'Fruit': 10000,
            },
        }

        # Get or create crops
        if crop_names:
            crops_to_create = crop_names
        else:
            crops_to_create = list(CROP_PRICE_PROFILES.keys())
            if 'default' in crops_to_create:
                crops_to_create.remove('default')

        self.stdout.write(f'\n📋 Processing {len(crops_to_create)} crops...')

        if clear_existing:
            self.stdout.write('🗑️  Clearing existing data...')
            HarvestPrice.objects.all().delete()
            Profitability.objects.all().delete()
            RegionalProduction.objects.all().delete()
            self.stdout.write('✅ Data cleared')

        created_crops = 0
        created_prices = 0
        created_profitability = 0
        created_regional = 0
        updated_units = 0

        # ============================================================
        # IMPORT CROP PRICES & PROFITABILITY
        # ============================================================
        for crop_name in crops_to_create:
            # Get or create crop with unit set to "Ton"
            crop, is_new = Crop.objects.get_or_create(
                name=crop_name,
                defaults={'unit': 'Ton'}
            )
            if is_new:
                created_crops += 1
                self.stdout.write(f'  ✅ Created crop: {crop_name} (unit: Ton)')
            else:
                # Check if existing crop has no unit
                if not crop.unit or crop.unit == '':
                    crop.unit = 'Ton'
                    crop.save()
                    updated_units += 1
                    self.stdout.write(f'  🔧 Updated {crop_name}: unit set to Ton')

            # Get price profile
            profile = None
            for key, value in CROP_PRICE_PROFILES.items():
                if key.lower() in crop_name.lower() or crop_name.lower() in key.lower():
                    profile = value
                    break
            
            if not profile:
                profile = CROP_PRICE_PROFILES['default']
                self.stdout.write(f'  ⚠️ Using default profile for {crop_name}')

            base_price = profile['base']
            volatility = profile['volatility']
            trend = profile['trend']

            # Get yield for this crop
            yield_tons = Decimal('1.5')
            for key, value in YIELD_PER_ACRE.items():
                if key in crop_name.lower():
                    yield_tons = Decimal(str(value))
                    break

            # Get production cost for this crop
            prod_cost = Decimal('4000000')
            for key, value in PRODUCTION_COST.items():
                if key in crop_name.lower():
                    prod_cost = Decimal(str(value))
                    break

            # Generate prices for each year
            for i, year in enumerate(sorted(years)):
                trend_factor = 1 + (trend * i)
                random_factor = 1 + random.uniform(-volatility, volatility)
                seasonal_factor = 1 + (0.15 * random.choice([-0.8, -0.3, 0.3, 0.8]))
                
                price = base_price * trend_factor * random_factor * seasonal_factor
                price = round(price / 1000) * 1000
                
                if price < base_price * 0.3:
                    price = base_price * 0.3
                if price > base_price * 2.5:
                    price = base_price * 2.5

                # Create harvest price
                harvest_price, price_created = HarvestPrice.objects.get_or_create(
                    crop=crop,
                    year=year,
                    defaults={'price': Decimal(str(int(price)))}
                )
                if price_created:
                    created_prices += 1

                # Calculate profitability
                price_per_ton = Decimal(str(int(price)))
                revenue_per_acre = price_per_ton * yield_tons
                profit_per_acre = revenue_per_acre - prod_cost

                # Create profitability record
                profit, profit_created = Profitability.objects.get_or_create(
                    crop=crop,
                    year=year,
                    defaults={
                        'price_per_ton': price_per_ton,
                        'yield_tons_per_acre': yield_tons,
                        'profit_per_acre': profit_per_acre
                    }
                )
                if profit_created:
                    created_profitability += 1

            price_count = HarvestPrice.objects.filter(crop=crop).count()
            profit_count = Profitability.objects.filter(crop=crop).count()
            self.stdout.write(f'  📊 {crop_name}: {price_count} prices, {profit_count} profitability records')

        # ============================================================
        # IMPORT REGIONAL PRODUCTION DATA
        # ============================================================
        self.stdout.write('\n📍 Importing regional production data...')

        for region, crops in REGIONAL_DATA.items():
            for crop_name, production_tons in crops.items():
                # Find or create crop
                crop, _ = Crop.objects.get_or_create(
                    name=crop_name,
                    defaults={'unit': 'Ton'}
                )
                
                # Create regional production record for each year
                for year in sorted(years):
                    year_int = int(year)
                    # Add some variation for each year
                    variation = 1 + random.uniform(-0.1, 0.1)
                    prod_value = int(production_tons * variation)
                    
                    regional, created = RegionalProduction.objects.get_or_create(
                        region=region,
                        crop_category=crop_name,
                        year=year_int,
                        defaults={
                            'production_tons': prod_value,
                            'sown_acres': int(prod_value * 2),
                            'harvested_acres': int(prod_value * 1.8),
                            'measurement_type': 'tons'
                        }
                    )
                    if created:
                        created_regional += 1

        self.stdout.write(f'  ✅ Created {created_regional} regional production records')

        # ============================================================
        # SUMMARY
        # ============================================================
        self.stdout.write(self.style.SUCCESS('\n✅ Import complete!'))
        self.stdout.write(f'  📈 Created/Updated:')
        self.stdout.write(f'    - {created_crops} new crops')
        self.stdout.write(f'    - {updated_units} crops had unit fixed')
        self.stdout.write(f'    - {created_prices} price records')
        self.stdout.write(f'    - {created_profitability} profitability records')
        self.stdout.write(f'    - {created_regional} regional production records')
        self.stdout.write(f'  📊 Totals:')
        self.stdout.write(f'    - {Crop.objects.count()} total crops')
        self.stdout.write(f'    - {HarvestPrice.objects.count()} price records')
        self.stdout.write(f'    - {Profitability.objects.count()} profitability records')
        self.stdout.write(f'    - {RegionalProduction.objects.count()} regional records')
        
        # Show regional data summary
        regions = RegionalProduction.objects.values_list('region', flat=True).distinct()
        self.stdout.write(f'  📍 Regions: {", ".join(sorted(set(regions)))}')
        
        # Show crops with missing units (should be 0 now)
        missing_units = Crop.objects.filter(unit__isnull=True) | Crop.objects.filter(unit='')
        if missing_units.exists():
            self.stdout.write(self.style.WARNING(f'\n⚠️ Warning: {missing_units.count()} crops still have missing units:'))
            for crop in missing_units[:10]:
                self.stdout.write(f'    - {crop.name}')
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ All crops have units set!'))
        
        self.stdout.write('\n🚀 Visit /market/recommendations/ to see the recommendations!')
        self.stdout.write('\n💡 To rebuild the AI vector store, run:')
        self.stdout.write('   python manage.py shell')
        self.stdout.write('   >>> from marketPrice.services.rag_service import AgriRAGService')
        self.stdout.write('   >>> rag = AgriRAGService()')
        self.stdout.write('   >>> rag.build_vector_store(force_rebuild=True)')