import random
from django.core.management.base import BaseCommand
from django.db import models
from marketPrice.models import Crop as PriceCrop, HarvestPrice
from decimal import Decimal

class Command(BaseCommand):
    help = 'Generate mock harvest price data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--crops',
            nargs='+',
            type=str,
            help='Specific crop names to mock (default: all)'
        )
        parser.add_argument(
            '--years',
            nargs='+',
            type=str,
            default=['2022', '2023', '2024', '2025', '2026'],
            help='Years to generate data for (format: 2022)'
        )

    def handle(self, *args, **options):
        years = options['years']
        crop_names = options['crops'] if options['crops'] else None

        # Define realistic base prices (in Kyat per Ton)
        # All prices are based on Yangon wholesale market data
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
            
            # FIXED: Betel Leaves - Now using realistic Yangon wholesale price
            # 10,000 Ks/Viss × 612.4 = 6,124,000 Ks/Ton
            'Betel Leaves': {'base': 6124000, 'volatility': 0.20, 'trend': 0.05},
            
            # Default for unknown crops
            'default': {'base': 5000000, 'volatility': 0.15, 'trend': 0.05},
        }

        # Get crops from marketPrice.Crop (not farms.Crop)
        if crop_names:
            crops = PriceCrop.objects.filter(name__in=crop_names)
        else:
            crops = PriceCrop.objects.all()

        if not crops.exists():
            self.stdout.write(self.style.ERROR('No crops found in marketPrice database!'))
            self.stdout.write('Please add crops to marketPrice.Crop first.')
            return

        self.stdout.write(f'Generating mock prices for {crops.count()} crops...')
        self.stdout.write(f'Years: {", ".join(years)}\n')
        
        created_count = 0
        
        for crop in crops:
            # Try to find a matching profile
            profile = None
            for key, value in CROP_PRICE_PROFILES.items():
                if key.lower() in crop.name.lower() or crop.name.lower() in key.lower():
                    profile = value
                    break
            
            if not profile:
                # Default profile for unknown crops
                profile = CROP_PRICE_PROFILES['default']
                self.stdout.write(f'  ⚠️ Using default profile for {crop.name}')
            
            base_price = profile['base']
            volatility = profile['volatility']
            trend = profile['trend']

            # Delete existing data for these years
            deleted = HarvestPrice.objects.filter(crop=crop, year__in=years).delete()
            if deleted[0] > 0:
                self.stdout.write(f'  🗑️ Removed {deleted[0]} existing records for {crop.name}')

            # Generate prices with realistic variation
            for i, year in enumerate(sorted(years)):
                # Add trend: prices generally go up or down over years
                trend_factor = 1 + (trend * i)
                
                # Add random variation
                random_factor = 1 + random.uniform(-volatility, volatility)
                
                # Add seasonal variation (peak in certain months)
                seasonal_factor = 1 + (0.15 * random.choice([-0.8, -0.3, 0.3, 0.8]))
                
                price = base_price * trend_factor * random_factor * seasonal_factor
                
                # Round to nearest 1000
                price = round(price / 1000) * 1000
                
                # Ensure price stays within realistic range
                if price < base_price * 0.3:
                    price = base_price * 0.3
                if price > base_price * 2.5:
                    price = base_price * 2.5
                
                # Create the harvest price
                HarvestPrice.objects.create(
                    crop=crop,
                    year=year,
                    price=Decimal(str(int(price))),
                )
                created_count += 1
                
                # Calculate price per Viss for display
                price_per_viss = price / 612.4
                self.stdout.write(f'  ✓ {crop.name} - {year}: {int(price):,} Ks/Ton ({price_per_viss:,.0f} Ks/Viss)')

        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully created {created_count} mock price records!'))
        
        # Show summary statistics
        self.stdout.write('\n📊 Summary of generated prices:')
        for crop in crops:
            prices = HarvestPrice.objects.filter(crop=crop).order_by('year')
            if prices.exists():
                # Convert Decimal to float for calculations
                first_price = float(prices.first().price)
                last_price = float(prices.last().price)
                avg_price = prices.aggregate(models.Avg('price'))['price__avg']
                if avg_price:
                    avg_price = float(avg_price)
                
                self.stdout.write(f'  {crop.name}:')
                self.stdout.write(f'    First: {first_price:,.0f} Ks/Ton ({first_price/612.4:,.0f} Ks/Viss)')
                self.stdout.write(f'    Latest: {last_price:,.0f} Ks/Ton ({last_price/612.4:,.0f} Ks/Viss)')
                self.stdout.write(f'    Average: {avg_price:,.0f} Ks/Ton ({avg_price/612.4:,.0f} Ks/Viss)')
        
        self.stdout.write('\n📋 Now you can view the Crop Catalog and Harvest Advisor pages!')