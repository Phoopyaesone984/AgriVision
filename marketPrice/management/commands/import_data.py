# marketPrice/management/commands/import_data.py
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from marketPrice.models import Crop, HarvestPrice, DailyMarketPrice, YieldData, Profitability
import os

class Command(BaseCommand):
    help = 'Import all market data from CSV files'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting data import...'))
        
        # Check if data directory exists
        if not os.path.exists('data'):
            self.stdout.write(self.style.ERROR('❌ Data directory not found!'))
            return
        
        try:
            self.import_crops()
            self.import_prices()
            self.import_daily_prices()
            self.import_yields()
            self.calculate_profitability()
            self.stdout.write(self.style.SUCCESS('✅ All data imported successfully!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            import traceback
            traceback.print_exc()

    def import_crops(self):
        """Import crops from the price CSV"""
        self.stdout.write('📊 Importing crops...')
        
        df = pd.read_csv('data/crop_prices_2019_2025.csv')
        df.columns = df.columns.str.strip()
        
        imported = 0
        for idx, row in df.iterrows():
            crop_name = str(row['crop_name']).strip()
            unit = str(row['unit']).strip() if pd.notna(row['unit']) else 'Ton'
            
            crop, created = Crop.objects.get_or_create(
                name=crop_name,
                defaults={'unit': unit}
            )
            
            # Try to determine category from crop name
            if not crop.category:
                categories = {
                    'Paddy': 'Cereal',
                    'Wheat': 'Cereal',
                    'Maize': 'Cereal',
                    'Groundnut': 'Oilseed',
                    'Sesamum': 'Oilseed',
                    'Sunflower': 'Oilseed',
                    'Mustard': 'Oilseed',
                    'Cotton': 'Fiber',
                    'Jute': 'Fiber',
                    'Rubber': 'Industrial',
                    'Sugarcane': 'Cash Crop',
                    'Tobacco': 'Cash Crop',
                    'Betel': 'Cash Crop',
                    'Chillies': 'Spice',
                    'Onion': 'Vegetable',
                    'Garlic': 'Vegetable',
                    'Potato': 'Vegetable',
                    'Coffee': 'Beverage',
                    'Tea': 'Beverage',
                    'Coconut': 'Fruit',
                    'Tapioca': 'Root Crop',
                    'Gram': 'Pulse',
                    'Matpe': 'Pulse',
                    'Pedisein': 'Pulse',
                    'Bocate': 'Pulse',
                    'Peboke': 'Pulse',
                    'Pelun': 'Pulse',
                    'Pesingon': 'Pulse',
                    'Peyin': 'Pulse',
                    'Pebyugale': 'Pulse',
                    'Pegyi': 'Pulse',
                    'Sadawpe': 'Pulse',
                    'Peyazar': 'Pulse',
                    'Penauk': 'Pulse',
                    'Sultani': 'Pulse',
                    'Sultapya': 'Pulse',
                    'Butter Bean': 'Pulse',
                }
                
                for key, value in categories.items():
                    if key in crop_name:
                        crop.category = value
                        crop.save()
                        break
            
            if created:
                imported += 1
        
        self.stdout.write(self.style.SUCCESS(f'✅ Imported {imported} crops'))

    def import_prices(self):
        """Import harvest prices"""
        self.stdout.write('📊 Importing harvest prices...')
        
        df = pd.read_csv('data/crop_prices_2019_2025.csv')
        df.columns = df.columns.str.strip()
        
        imported = 0
        
        for idx, row in df.iterrows():
            try:
                crop_name = str(row['crop_name']).strip()
                crop = Crop.objects.get(name=crop_name)
                
                # Get price columns
                year_columns = [col for col in df.columns if col.startswith('price_')]
                
                for col in year_columns:
                    # Extract year from column name
                    year = col.replace('price_', '').replace('_', '-')
                    
                    # Check if value is not empty
                    if pd.notna(row[col]) and str(row[col]).strip():
                        try:
                            price_value = float(str(row[col]).strip().replace(',', ''))
                            if price_value > 0:
                                hp, created = HarvestPrice.objects.get_or_create(
                                    crop=crop,
                                    year=year,
                                    defaults={'price': Decimal(str(price_value))}
                                )
                                if created:
                                    imported += 1
                        except (ValueError, TypeError) as e:
                            self.stdout.write(f'  ⚠️ Skipping {crop_name} {year}: invalid price "{row[col]}"')
                            continue
                            
            except Crop.DoesNotExist:
                self.stdout.write(f'  ⚠️ Crop not found: {crop_name}')
                continue
            except Exception as e:
                self.stdout.write(f'  ⚠️ Error with row {idx}: {e}')
                continue
        
        self.stdout.write(self.style.SUCCESS(f'✅ Imported {imported} harvest prices'))

    def import_daily_prices(self):
        """Import daily market prices"""
        self.stdout.write('📊 Importing daily market prices...')
        
        try:
            df = pd.read_csv('data/market_prices_yangon_july_2026.csv')
            df.columns = df.columns.str.strip()
            
            imported = 0
            
            for idx, row in df.iterrows():
                try:
                    category = str(row['Category']).strip()
                    commodity = str(row['Commodity']).strip()
                    unit = str(row['Unit']).strip()
                    
                    # Get date columns
                    date_columns = [col for col in df.columns if '-' in col and '2026' in col]
                    
                    for date_str in date_columns:
                        if pd.notna(row[date_str]) and str(row[date_str]).strip():
                            try:
                                price_value = float(str(row[date_str]).strip().replace(',', ''))
                                if price_value > 0:
                                    # Parse date
                                    from datetime import datetime
                                    date_obj = datetime.strptime(date_str, '%d-%m-%Y').date()
                                    
                                    # Try to find matching crop
                                    crop = None
                                    crop_name = commodity.split('(')[0].strip()
                                    crop = Crop.objects.filter(name__icontains=crop_name).first()
                                    
                                    # Create daily price
                                    dp, created = DailyMarketPrice.objects.get_or_create(
                                        commodity=commodity,
                                        recorded_date=date_obj,
                                        defaults={
                                            'crop': crop,
                                            'category': category,
                                            'market': 'Yangon',
                                            'price': Decimal(str(price_value)),
                                            'unit': unit
                                        }
                                    )
                                    
                                    if created:
                                        imported += 1
                            except (ValueError, TypeError) as e:
                                self.stdout.write(f'  ⚠️ Skipping {commodity} {date_str}: invalid price')
                                continue
                                
                except Exception as e:
                    self.stdout.write(f'  ⚠️ Error with row {idx}: {e}')
                    continue
            
            self.stdout.write(self.style.SUCCESS(f'✅ Imported {imported} daily prices'))
            
        except FileNotFoundError:
            self.stdout.write(self.style.WARNING('⚠️ Daily prices file not found, skipping...'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Error importing daily prices: {e}'))

    def import_yields(self):
        """Import yield data"""
        self.stdout.write('📊 Importing yield data...')
        
        try:
            df = pd.read_csv('data/table_3_04_average_yield_per_harvested_acre.csv')
            df.columns = df.columns.str.strip()
            
            imported = 0
            
            for idx, row in df.iterrows():
                try:
                    crop_name = str(row['sn_crop']).strip()
                    
                    # Clean crop name
                    if '.' in crop_name:
                        crop_name = crop_name.split('.', 1)[1].strip()
                    
                    # Remove parentheses content if present
                    crop_name_clean = crop_name.split('(')[0].strip()
                    
                    # Find matching crop
                    crop = Crop.objects.filter(name__icontains=crop_name_clean).first()
                    
                    if not crop:
                        # Try exact match
                        crop = Crop.objects.filter(name=crop_name).first()
                    
                    if not crop:
                        self.stdout.write(f'  ⚠️ Crop not found: {crop_name}')
                        continue
                    
                    unit = str(row['unit']).strip() if pd.notna(row['unit']) else 'Ton'
                    
                    # Get year columns
                    year_columns = [col for col in df.columns if col not in ['sn_crop', 'unit']]
                    
                    for col in year_columns:
                        if pd.notna(row[col]) and str(row[col]).strip():
                            try:
                                yield_value = float(str(row[col]).strip().replace(',', ''))
                                if yield_value > 0:
                                    # Convert year format
                                    year = col.replace('_', '-')
                                    
                                    yd, created = YieldData.objects.get_or_create(
                                        crop=crop,
                                        year=year,
                                        defaults={
                                            'yield_value': Decimal(str(yield_value)),
                                            'unit': unit
                                        }
                                    )
                                    
                                    if created:
                                        imported += 1
                            except (ValueError, TypeError) as e:
                                self.stdout.write(f'  ⚠️ Skipping {crop_name} {col}: invalid yield value')
                                continue
                                
                except Exception as e:
                    self.stdout.write(f'  ⚠️ Error with row {idx}: {e}')
                    continue
            
            self.stdout.write(self.style.SUCCESS(f'✅ Imported {imported} yield records'))
            
        except FileNotFoundError:
            self.stdout.write(self.style.WARNING('⚠️ Yield data file not found, skipping...'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Error importing yield data: {e}'))

    def calculate_profitability(self):
        """Calculate profitability from harvest prices and yields"""
        self.stdout.write('📊 Calculating profitability...')
        
        try:
            # Get all crops with both harvest prices and yield data
            crops = Crop.objects.filter(
                harvest_prices__isnull=False,
                yields__isnull=False
            ).distinct()
            
            imported = 0
            
            for crop in crops:
                # Get all harvest prices and yields
                harvest_prices = crop.harvest_prices.all().order_by('year')
                
                for hp in harvest_prices:
                    # Find matching yield data for the same year
                    yield_data = crop.yields.filter(year=hp.year).first()
                    
                    if yield_data and hp.price and yield_data.yield_value:
                        try:
                            # Calculate profit per acre
                            price_per_ton = hp.price
                            yield_tons_per_acre = yield_data.yield_value
                            profit_per_acre = price_per_ton * yield_tons_per_acre
                            
                            # Create or update profitability record
                            profit, created = Profitability.objects.get_or_create(
                                crop=crop,
                                year=hp.year,
                                defaults={
                                    'price_per_ton': price_per_ton,
                                    'yield_tons_per_acre': yield_tons_per_acre,
                                    'profit_per_acre': profit_per_acre
                                }
                            )
                            
                            if created:
                                imported += 1
                        except Exception as e:
                            self.stdout.write(f'  ⚠️ Error calculating profit for {crop.name} {hp.year}: {e}')
            
            self.stdout.write(self.style.SUCCESS(f'✅ Calculated profitability for {imported} crops'))
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠️ Error calculating profitability: {e}'))
