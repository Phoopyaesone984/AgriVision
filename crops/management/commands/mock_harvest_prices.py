import random
from django.core.management.base import BaseCommand
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
            default=['2021-22', '2022-23', '2023-24', '2024-25'],
            help='Years to generate data for (format: 2021-22)'
        )

    def handle(self, *args, **options):
        years = options['years']
        crop_names = options['crops'] if options['crops'] else None

        # Define realistic base prices (in Kyat per Ton)
        CROP_PRICE_PROFILES = {
            'Wheat': {'base': 6000000, 'volatility': 0.15, 'trend': 0.08},
            'Rice': {'base': 3500000, 'volatility': 0.12, 'trend': 0.05},
            'Betel Leaves': {'base': 30000000, 'volatility': 0.20, 'trend': 0.10},
            'Chillies': {'base': 7000000, 'volatility': 0.25, 'trend': -0.05},
            'Garlic': {'base': 6000000, 'volatility': 0.18, 'trend': 0.07},
            'Coffee': {'base': 5500000, 'volatility': 0.15, 'trend': 0.12},
            'Maize': {'base': 2500000, 'volatility': 0.10, 'trend': 0.04},
            'Onion': {'base': 3000000, 'volatility': 0.22, 'trend': -0.03},
            'Potato': {'base': 2800000, 'volatility': 0.16, 'trend': 0.06},
            'Sugarcane': {'base': 1800000, 'volatility': 0.08, 'trend': 0.02},
            'Paddy': {'base': 3200000, 'volatility': 0.10, 'trend': 0.03},
            'Tobacco': {'base': 8000000, 'volatility': 0.20, 'trend': -0.08},
            'Cotton': {'base': 4500000, 'volatility': 0.14, 'trend': 0.05},
            'Groundnut': {'base': 3500000, 'volatility': 0.12, 'trend': 0.04},
            'Sesamum': {'base': 2800000, 'volatility': 0.18, 'trend': 0.06},
            'Tomato': {'base': 4000000, 'volatility': 0.20, 'trend': 0.05},
            'Tapioca': {'base': 2500000, 'volatility': 0.10, 'trend': 0.02},
            'Pulse': {'base': 3000000, 'volatility': 0.12, 'trend': 0.03},
            'Bean': {'base': 2800000, 'volatility': 0.12, 'trend': 0.03},
            'Tea': {'base': 4500000, 'volatility': 0.15, 'trend': 0.05},
            'Betel Nut': {'base': 8500000, 'volatility': 0.15, 'trend': 0.04},
            'Chillies (Dry)': {'base': 11000000, 'volatility': 0.15, 'trend': 0.02},
            'Garlic (Dry)': {'base': 10000000, 'volatility': 0.15, 'trend': 0.02},
            'Corn': {'base': 2800000, 'volatility': 0.12, 'trend': 0.04},
            'Soybean': {'base': 3800000, 'volatility': 0.12, 'trend': 0.06},
            'Fruit': {'base': 5000000, 'volatility': 0.20, 'trend': 0.05},
            'Vegetable': {'base': 4500000, 'volatility': 0.18, 'trend': 0.05},
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
                profile = {'base': 5000000, 'volatility': 0.15, 'trend': 0.05}
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
                
                # Round to nearest 100
                price = round(price / 100) * 100
                
                # Ensure price stays within realistic range
                if price < base_price * 0.3:
                    price = base_price * 0.3
                if price > base_price * 2.5:
                    price = base_price * 2.5
                
                # Create the harvest price (NO unit field!)
                HarvestPrice.objects.create(
                    crop=crop,
                    year=year,
                    price=Decimal(str(int(price))),
                )
                created_count += 1
                self.stdout.write(f'  ✓ {crop.name} - {year}: {int(price):,} Ks/Ton')

        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully created {created_count} mock price records!'))
        self.stdout.write('\n📊 Now you can view the Harvest Advisor page to see recommendations!')