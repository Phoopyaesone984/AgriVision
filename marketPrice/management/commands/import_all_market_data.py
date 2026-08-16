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
        
        # Define realistic base prices (in Kyat per Ton) - Yangon wholesale
        CROP_PRICE_PROFILES = {
            # Field Crops
            'Wheat': {'base': 6000000, 'volatility': 0.15, 'trend': 0.08},
            'Rice': {'base': 3500000, 'volatility': 0.12, 'trend': 0.05},
            'Paddy': {'base': 3200000, 'volatility': 0.10, 'trend': 0.03},
            'Maize': {'base': 2500000, 'volatility': 0.10, 'trend': 0.04},
            'Corn': {'base': 2800000, 'volatility': 0.12, 'trend': 0.04},
            'Sugarcane': {'base': 1800000, 'volatility': 0.08, 'trend': 0.02},
            'Tapioca': {'base': 2500000, 'volatility': 0.10, 'trend': 0.02},
            
            # Vegetables
            'Onion': {'base': 3000000, 'volatility': 0.22, 'trend': -0.03},
            'Potato': {'base': 2800000, 'volatility': 0.16, 'trend': 0.06},
            'Tomato': {'base': 4000000, 'volatility': 0.20, 'trend': 0.05},
            'Chillies': {'base': 7000000, 'volatility': 0.25, 'trend': -0.05},
            'Chillies (Dry)': {'base': 11000000, 'volatility': 0.15, 'trend': 0.02},
            'Garlic': {'base': 6000000, 'volatility': 0.18, 'trend': 0.07},
            'Garlic (Dry)': {'base': 10000000, 'volatility': 0.15, 'trend': 0.02},
            'Vegetable': {'base': 4500000, 'volatility': 0.18, 'trend': 0.05},
            
            # Pulses & Oilseeds
            'Pulse': {'base': 3000000, 'volatility': 0.12, 'trend': 0.03},
            'Bean': {'base': 2800000, 'volatility': 0.12, 'trend': 0.03},
            'Soybean': {'base': 3800000, 'volatility': 0.12, 'trend': 0.06},
            'Groundnut': {'base': 3500000, 'volatility': 0.12, 'trend': 0.04},
            'Sesamum': {'base': 2800000, 'volatility': 0.18, 'trend': 0.06},
            
            # Cash Crops
            'Coffee': {'base': 5500000, 'volatility': 0.15, 'trend': 0.12},
            'Tea': {'base': 4500000, 'volatility': 0.15, 'trend': 0.05},
            'Tobacco': {'base': 8000000, 'volatility': 0.20, 'trend': -0.08},
            'Cotton': {'base': 4500000, 'volatility': 0.14, 'trend': 0.05},
            
            # Fruits & Nuts
            'Fruit': {'base': 5000000, 'volatility': 0.20, 'trend': 0.05},
            'Betel Nut': {'base': 8500000, 'volatility': 0.15, 'trend': 0.04},
            
            # FIXED: Betel Leaves - Realistic Yangon wholesale price
            'Betel Leaves': {'base': 6124000, 'volatility': 0.20, 'trend': 0.05},
            
            # Default
            'default': {'base': 5000000, 'volatility': 0.15, 'trend': 0.05},
        }

        # Yield per acre by crop type (in tons)
        YIELD_PER_ACRE = {
            'rice': 3.5, 'paddy': 3.5, 'sugarcane': 50.0,
            'potato': 12.0, 'onion': 12.0, 'garlic': 5.0,
            'coffee': 0.8, 'tea': 0.8, 'betel': 1.2,
            'chillies': 1.5, 'groundnut': 0.8, 'sesamum': 0.8,
            'tobacco': 2.0, 'cotton': 1.5, 'fruit': 5.0,
            'vegetable': 10.0,
            'default': 1.5,
        }

        # Production cost per acre (in Kyat)
        PRODUCTION_COST = Decimal('4000000')  # 4 million Ks/acre

        # Get or create crops
        if crop_names:
            crops_to_create = crop_names
        else:
            crops_to_create = list(CROP_PRICE_PROFILES.keys())
            # Remove 'default' from the list
            if 'default' in crops_to_create:
                crops_to_create.remove('default')

        self.stdout.write(f'\n📋 Processing {len(crops_to_create)} crops...')

        if clear_existing:
            self.stdout.write('🗑️  Clearing existing data...')
            HarvestPrice.objects.all().delete()
            Profitability.objects.all().delete()
            self.stdout.write('✅ Data cleared')

        created_crops = 0
        created_prices = 0
        created_profitability = 0

        for crop_name in crops_to_create:
            # Get or create crop
            crop, is_new = Crop.objects.get_or_create(name=crop_name)
            if is_new:
                created_crops += 1
                self.stdout.write(f'  ✅ Created crop: {crop_name}')

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
            yield_tons = Decimal('1.5')  # Default
            for key, value in YIELD_PER_ACRE.items():
                if key in crop_name.lower():
                    yield_tons = Decimal(str(value))
                    break

            # Generate prices for each year
            for i, year in enumerate(sorted(years)):
                # Add trend and random variation
                trend_factor = 1 + (trend * i)
                random_factor = 1 + random.uniform(-volatility, volatility)
                seasonal_factor = 1 + (0.15 * random.choice([-0.8, -0.3, 0.3, 0.8]))
                
                price = base_price * trend_factor * random_factor * seasonal_factor
                price = round(price / 1000) * 1000  # Round to nearest 1000
                
                # Ensure price stays within realistic range
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
                profit_per_acre = revenue_per_acre - PRODUCTION_COST

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

            # Show progress
            price_count = HarvestPrice.objects.filter(crop=crop).count()
            profit_count = Profitability.objects.filter(crop=crop).count()
            self.stdout.write(f'  📊 {crop_name}: {price_count} prices, {profit_count} profitability records')

        # Summary
        self.stdout.write(self.style.SUCCESS('\n✅ Import complete!'))
        self.stdout.write(f'  📈 Created/Updated:')
        self.stdout.write(f'    - {created_crops} new crops')
        self.stdout.write(f'    - {created_prices} price records')
        self.stdout.write(f'    - {created_profitability} profitability records')
        self.stdout.write(f'  📊 Totals:')
        self.stdout.write(f'    - {Crop.objects.count()} total crops')
        self.stdout.write(f'    - {HarvestPrice.objects.count()} price records')
        self.stdout.write(f'    - {Profitability.objects.count()} profitability records')
        self.stdout.write('\n🚀 Visit /market/recommendations/ to see the recommendations!')