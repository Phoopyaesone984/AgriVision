import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from marketPrice.models import RegionalProduction
import os
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import regional crop production data from CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data/region_data.csv',  # Changed default to .csv
            help='Path to the CSV file (default: data/region_data.csv)'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'Reading file: {file_path}'))
        
        try:
            # --- CHANGE 1: Read CSV instead of Excel ---
            df = pd.read_csv(file_path)
            
            total_imported = 0
            
            # Determine the structure based on column names
            columns = df.columns.tolist()
            self.stdout.write(f'Columns found: {columns}')
            
            if 'region' in columns and 'crop_category' in columns:
                # New format with region, crop_category, year, etc.
                imported = self._import_region_data_format1(df)
                total_imported += imported
            elif 'region' in columns and 'crop' in columns:
                # Alternative format
                imported = self._import_region_data_format2(df)
                total_imported += imported
            else:
                self.stdout.write(self.style.WARNING(f'  Unknown format. Columns: {columns}'))
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully imported {total_imported} records!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing data: {str(e)}'))
            raise

    def _import_region_data_format1(self, df):
        """Import data from the format with region, crop_category columns"""
        imported = 0
        
        # Clean column names
        df.columns = df.columns.str.strip().str.lower()
        
        # Map columns
        region_col = 'region'
        category_col = 'crop_category'
        year_col = 'year'
        
        # Find production columns
        sown_col = None
        harvested_col = None
        production_col = None
        
        for col in df.columns:
            if 'sown' in col or 'sown_acres' in col:
                sown_col = col
            elif 'harvested' in col or 'harvested_acres' in col:
                harvested_col = col
            elif 'production' in col or 'production_tons' in col:
                production_col = col
        
        # Process each row
        with transaction.atomic():
            for idx, row in df.iterrows():
                try:
                    region = row.get(region_col)
                    category = row.get(category_col)
                    year = str(row.get(year_col))
                    
                    if pd.isna(region) or pd.isna(category) or pd.isna(year):
                        continue
                    
                    # Get values
                    sown = row.get(sown_col) if sown_col else None
                    harvested = row.get(harvested_col) if harvested_col else None
                    production = row.get(production_col) if production_col else None
                    
                    # Skip if no data
                    if pd.isna(sown) and pd.isna(harvested) and pd.isna(production):
                        continue
                    
                    # Convert NaN values to 0 or None
                    sown_val = float(sown) if pd.notna(sown) else 0.0
                    harvested_val = float(harvested) if pd.notna(harvested) else 0.0
                    production_val = float(production) if pd.notna(production) else 0.0
                    
                    # Save to the RegionalProduction model
                    record, created = RegionalProduction.objects.get_or_create(
                        region=str(region).strip(),
                        crop_category=str(category).strip(),
                        year=str(year).strip(),
                        defaults={
                            'sown_acres': sown_val,
                            'harvested_acres': harvested_val,
                            'production_tons': production_val,
                            'measurement_type': None
                        }
                    )
                    
                    if created:
                        imported += 1
                        self.stdout.write(f'  ✅ Imported: {region} - {category} ({year})')
                    else:
                        self.stdout.write(f'  ⏭️ Skipped (already exists): {region} - {category} ({year})')
                    
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠️ Error processing row {idx}: {e}'))
                    continue
        
        return imported

    def _import_region_data_format2(self, df):
        """Import data from alternative format"""
        imported = 0
        
        # Clean column names
        df.columns = df.columns.str.strip().str.lower()
        
        with transaction.atomic():
            for idx, row in df.iterrows():
                try:
                    region = row.get('region')
                    crop_name = row.get('crop')
                    year = str(row.get('year'))
                    
                    if pd.isna(region) or pd.isna(crop_name) or pd.isna(year):
                        continue
                    
                    # Get production metrics
                    sown = row.get('sown_acres')
                    harvested = row.get('harvested_acres')
                    production = row.get('production_tons')
                    
                    # Convert NaN values to 0 or None
                    sown_val = float(sown) if pd.notna(sown) else 0.0
                    harvested_val = float(harvested) if pd.notna(harvested) else 0.0
                    production_val = float(production) if pd.notna(production) else 0.0
                    
                    # Save to the RegionalProduction model
                    record, created = RegionalProduction.objects.get_or_create(
                        region=str(region).strip(),
                        crop_category=str(crop_name).strip(),
                        year=str(year).strip(),
                        defaults={
                            'sown_acres': sown_val,
                            'harvested_acres': harvested_val,
                            'production_tons': production_val,
                            'measurement_type': None
                        }
                    )
                    
                    if created:
                        imported += 1
                        self.stdout.write(f'  ✅ Imported: {region} - {crop_name} ({year})')
                    else:
                        self.stdout.write(f'  ⏭️ Skipped (already exists): {region} - {crop_name} ({year})')
                    
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠️ Error processing row {idx}: {e}'))
                    continue
        
        return imported