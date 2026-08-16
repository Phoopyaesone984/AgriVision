# crops/management/commands/setup_regional_data.py

import csv
import random
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.db import transaction
from marketPrice.models import RegionalProduction
import os

class Command(BaseCommand):
    help = 'Import regional data from CSV and generate 2026 mock data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data/region_data.csv',
            help='Path to the CSV file (default: data/region_data.csv)'
        )
        parser.add_argument(
            '--skip-import',
            action='store_true',
            help='Skip CSV import (if data already imported)'
        )
        parser.add_argument(
            '--skip-generate',
            action='store_true',
            help='Skip generating 2026 mock data'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration even if data exists'
        )

    def safe_decimal(self, value):
        """Safely convert any value to Decimal, return Decimal('0') if invalid"""
        if value is None:
            return Decimal('0')
        
        # If it's already a Decimal, return it
        if isinstance(value, Decimal):
            return value
        
        # Convert to string and clean
        str_value = str(value).strip()
        
        # Handle empty or null-like values
        if str_value in ('', 'None', 'NULL', 'null', 'Null', 'N/A', 'n/a', 'nan', 'NaN'):
            return Decimal('0')
        
        # Remove commas, spaces, currency symbols
        clean_value = str_value.replace(',', '').replace(' ', '').replace('$', '').replace('Ks', '')
        
        # If empty after cleaning
        if not clean_value:
            return Decimal('0')
        
        try:
            return Decimal(clean_value)
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0')

    def handle(self, *args, **options):
        file_path = options['file']
        skip_import = options['skip_import']
        skip_generate = options['skip_generate']
        force = options['force']

        self.stdout.write("=" * 70)
        self.stdout.write("REGIONAL DATA SETUP")
        self.stdout.write("=" * 70)

        # =========================================================
        # STEP 1: Import CSV Data
        # =========================================================
        if not skip_import:
            self.stdout.write("\n📂 STEP 1: Importing CSV Data")
            self.stdout.write("-" * 50)
            
            if not os.path.exists(file_path):
                self.stdout.write(self.style.ERROR(f'❌ File not found: {file_path}'))
                return
            
            imported_count = self.import_csv(file_path)
            self.stdout.write(self.style.SUCCESS(f'✅ Imported {imported_count} records from CSV'))
        else:
            self.stdout.write("\n⏭️ Skipping CSV import (--skip-import flag used)")

        # =========================================================
        # STEP 2: Generate 2026 Data
        # =========================================================
        if not skip_generate:
            existing_2026 = RegionalProduction.objects.filter(year='2026-27')
            
            if existing_2026.exists() and not force:
                self.stdout.write("\n📊 STEP 2: 2026 Data Already Exists")
                self.stdout.write("-" * 50)
                self.stdout.write(f"   📦 Found {existing_2026.count()} existing 2026-27 records")
                self.stdout.write("   ⏭️ Skipping generation (use --force to regenerate)")
            else:
                self.stdout.write("\n📊 STEP 2: Generating 2026 Mock Data")
                self.stdout.write("-" * 50)
                
                if force and existing_2026.exists():
                    deleted = existing_2026.delete()
                    self.stdout.write(f"   🗑️ Deleted {deleted[0]} existing 2026-27 records (--force)")
                
                created_count = self.generate_2026_data()
                self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} records for 2026-27'))
        else:
            self.stdout.write("\n⏭️ Skipping 2026 generation (--skip-generate flag used)")

        # =========================================================
        # STEP 3: Summary
        # =========================================================
        self.stdout.write("\n" + "=" * 70)
        total = RegionalProduction.objects.count()
        years = RegionalProduction.objects.values_list('year', flat=True).distinct().order_by('year')
        self.stdout.write(f"📦 TOTAL RECORDS: {total}")
        self.stdout.write(f"📅 YEARS: {', '.join(list(years))}")
        
        count_2026 = RegionalProduction.objects.filter(year='2026-27').count()
        self.stdout.write(f"📊 2026-27 RECORDS: {count_2026}")
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("\n✅ Setup complete!"))

    def import_csv(self, file_path):
        """Import data from CSV file with safe Decimal conversion"""
        imported = 0
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    region = row.get('region', '').strip()
                    crop = row.get('crop_category', '').strip()
                    year = row.get('year', '').strip()
                    
                    if not region or not crop or not year:
                        continue
                    
                    # Skip 2026-27 records from CSV (we generate them separately)
                    if year == '2026-27':
                        continue
                    
                    # SAFE CONVERSION - using the safe_decimal method
                    sown = self.safe_decimal(row.get('sown_acres', 0))
                    harvested = self.safe_decimal(row.get('harvested_acres', 0))
                    production = self.safe_decimal(row.get('production_tons', 0))
                    
                    measurement = row.get('measurement_type', '').strip() or 'Tons'
                    
                    # Create or update
                    obj, created = RegionalProduction.objects.update_or_create(
                        region=region,
                        crop_category=crop,
                        year=year,
                        defaults={
                            'sown_acres': sown,
                            'harvested_acres': harvested,
                            'production_tons': production,
                            'measurement_type': measurement,
                        }
                    )
                    imported += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'⚠️ Error in row: {e}'))
                    continue
        
        return imported

    def generate_2026_data(self):
        """Generate 2026 mock data based on historical trends"""
        created = 0
        
        # Get all unique region-crop combinations (excluding 2026-27)
        combos = RegionalProduction.objects.exclude(
            year='2026-27'
        ).values('region', 'crop_category').distinct()
        
        total_combos = combos.count()
        
        if total_combos == 0:
            self.stdout.write(self.style.WARNING('⚠️ No data found to base 2026 projections on'))
            return 0
        
        self.stdout.write(f'   📦 Found {total_combos} region-crop combinations')
        
        for combo in combos:
            region = combo['region']
            crop = combo['crop_category']
            
            try:
                # Get historical data (excluding 2026-27)
                historical = RegionalProduction.objects.filter(
                    region=region,
                    crop_category=crop
                ).exclude(year='2026-27').order_by('-year')
                
                if not historical.exists():
                    continue
                
                # Get the latest year's data
                latest = historical.first()
                
                # SAFE: Get base values using the safe_decimal method
                base_prod = float(self.safe_decimal(latest.production_tons)) if latest.production_tons else 1000
                base_sown = float(self.safe_decimal(latest.sown_acres)) if latest.sown_acres else 1000
                base_harvested = float(self.safe_decimal(latest.harvested_acres)) if latest.harvested_acres else 900
                
                # Ensure minimum values
                if base_prod < 100:
                    base_prod = 1000
                if base_sown < 100:
                    base_sown = 1000
                if base_harvested < 100:
                    base_harvested = 900
                
                # Calculate growth based on historical trend
                growth_factor = 1.05
                
                if historical.count() >= 2:
                    prev = historical[1]
                    try:
                        prev_prod = float(self.safe_decimal(prev.production_tons)) if prev.production_tons else 1
                        if prev_prod > 0 and base_prod > 0:
                            growth_factor = base_prod / prev_prod
                            growth_factor = max(0.7, min(1.3, growth_factor))
                    except (TypeError, ValueError):
                        growth_factor = 1.05
                
                # Add random variation
                variation = 1 + random.uniform(-0.08, 0.08)
                
                # Calculate 2026 values
                new_prod = round(base_prod * growth_factor * variation, 2)
                new_sown = round(base_sown * growth_factor * variation, 2)
                new_harvested = round(base_harvested * growth_factor * variation, 2)
                
                # Ensure minimum values
                new_prod = max(new_prod, base_prod * 0.85)
                new_sown = max(new_sown, base_sown * 0.85)
                new_harvested = max(new_harvested, base_harvested * 0.85)
                
                # Create 2026 record with safe Decimal conversion
                RegionalProduction.objects.create(
                    region=region,
                    crop_category=crop,
                    year='2026-27',
                    sown_acres=self.safe_decimal(str(new_sown)),
                    harvested_acres=self.safe_decimal(str(new_harvested)),
                    production_tons=self.safe_decimal(str(new_prod)),
                    measurement_type='Tons',
                )
                created += 1
                
                if created % 20 == 0:
                    self.stdout.write(f'      ✅ Created {created} records so far...')
                    
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️ Error: {region} - {crop}: {e}'))
                continue
        
        return created