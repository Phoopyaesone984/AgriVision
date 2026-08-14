import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal
from marketPrice.models import Crop, HarvestPrice, DailyMarketPrice, YieldData, Profitability
import os
from datetime import datetime

class Command(BaseCommand):
    help = 'DIAGNOSTIC - Check what crops exist and what CSV contains'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 DIAGNOSTIC: Checking data...'))
        
        data_dir = os.path.join(os.getcwd(), 'data')
        
        if not os.path.exists(data_dir):
            self.stdout.write(self.style.ERROR(f'❌ Data directory not found at: {data_dir}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'📂 Data directory found at: {data_dir}'))
        
        # 1. Check existing crops in database
        self.stdout.write('\n📋 EXISTING CROPS IN DATABASE:')
        existing_crops = Crop.objects.all().order_by('name')
        self.stdout.write(f'  Total crops: {existing_crops.count()}')
        for crop in existing_crops:
            self.stdout.write(f'    - {crop.name}')
        
        # 2. Check crop_prices_2019_2025.csv
        self.stdout.write('\n📊 CROPS IN crop_prices_2019_2025.csv:')
        price_file = os.path.join(data_dir, 'crop_prices_2019_2025.csv')
        if os.path.exists(price_file):
            df_prices = pd.read_csv(price_file)
            df_prices.columns = df_prices.columns.str.strip()
            self.stdout.write(f'  Columns: {df_prices.columns.tolist()}')
            self.stdout.write(f'  Total rows: {len(df_prices)}')
            
            # Show first 5 rows
            self.stdout.write('  First 5 rows:')
            for idx in range(min(5, len(df_prices))):
                row = df_prices.iloc[idx]
                crop_name = str(row['crop_name']).strip()
                self.stdout.write(f'    - {crop_name}')
            
            # Check if these crops exist in database
            self.stdout.write('\n  🔍 Matching CSV crops to database:')
            for idx, row in df_prices.iterrows():
                crop_name = str(row['crop_name']).strip()
                if crop_name and crop_name != 'nan':
                    exists = Crop.objects.filter(name__icontains=crop_name).exists()
                    if exists:
                        self.stdout.write(f'    ✅ {crop_name} - EXISTS in database')
                    else:
                        self.stdout.write(f'    ❌ {crop_name} - NOT FOUND in database')
                        
                    # Also try to find by different name formats
                    crop_variants = [
                        crop_name,
                        crop_name.replace(' (', '('),
                        crop_name.split('(')[0].strip(),
                        crop_name.lower(),
                        crop_name.title()
                    ]
                    
                    found_variant = False
                    for variant in set(crop_variants):
                        if variant != crop_name:
                            if Crop.objects.filter(name__icontains=variant).exists():
                                self.stdout.write(f'      ℹ️  Found as: "{variant}"')
                                found_variant = True
                                break
                    
                    if not found_variant and not Crop.objects.filter(name__icontains=crop_name).exists():
                        self.stdout.write(f'      ℹ️  No matching crop found in database')
        
        # 3. Check yield data file
        self.stdout.write('\n📊 CROPS IN table_3_04_average_yield_per_harvested_acre.csv:')
        yield_file = os.path.join(data_dir, 'table_3_04_average_yield_per_harvested_acre.csv')
        if os.path.exists(yield_file):
            df_yields = pd.read_csv(yield_file)
            df_yields.columns = df_yields.columns.str.strip()
            self.stdout.write(f'  Columns: {df_yields.columns.tolist()}')
            self.stdout.write(f'  Total rows: {len(df_yields)}')
            
            # Show first 10 rows
            self.stdout.write('  First 10 rows:')
            for idx in range(min(10, len(df_yields))):
                row = df_yields.iloc[idx]
                crop_name = str(row['sn_crop']).strip()
                self.stdout.write(f'    - {crop_name}')
                
                # Check if exists in database
                crop_clean = crop_name.split('.', 1)[1].strip() if '.' in crop_name else crop_name
                crop_clean = crop_clean.split('(')[0].strip()
                exists = Crop.objects.filter(name__icontains=crop_clean).exists()
                if exists:
                    self.stdout.write(f'      ✅ Exists in database as: {crop_clean}')
                else:
                    self.stdout.write(f'      ❌ NOT found in database')
        
        # 4. Suggest crops to create
        self.stdout.write('\n💡 SUGGESTION: Run this to create missing crops:')
        self.stdout.write('  python manage.py create_missing_crops')
        
        # 5. Show current database stats
        self.stdout.write('\n📊 DATABASE STATISTICS:')
        self.stdout.write(f'  Crops: {Crop.objects.count()}')
        self.stdout.write(f'  Harvest Prices: {HarvestPrice.objects.count()}')
        self.stdout.write(f'  Yield Data: {YieldData.objects.count()}')
        self.stdout.write(f'  Daily Market Prices: {DailyMarketPrice.objects.count()}')
        self.stdout.write(f'  Profitability Records: {Profitability.objects.count()}')