import pandas as pd
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AgriVision.settings')
django.setup()

from marketPrice.models import RegionalProduction

# Change this path if your file is somewhere else
file_path = 'data/region_data.csv'

print("🚀 Starting regional data import...")

try:
    # Read the CSV
    df = pd.read_csv(file_path)
    df.columns = df.columns.str.strip()
    
    imported_count = 0
    skipped_count = 0

    for index, row in df.iterrows():
        try:
            # Handle empty values (replace NaN with 0 or None)
            sown = float(row['sown_acres']) if pd.notna(row['sown_acres']) else 0.0
            harvested = float(row['harvested_acres']) if pd.notna(row['harvested_acres']) else 0.0
            production = float(row['production_tons']) if pd.notna(row['production_tons']) else 0.0
            measurement = str(row['measurement_type']).strip() if pd.notna(row['measurement_type']) else None
            if measurement == '':
                measurement = None

            # Create the record using get_or_create to avoid duplicates
            record, created = RegionalProduction.objects.get_or_create(
                region=str(row['region']).strip(),
                crop_category=str(row['crop_category']).strip(),
                year=str(row['year']).strip(),
                defaults={
                    'sown_acres': sown,
                    'harvested_acres': harvested,
                    'production_tons': production,
                    'measurement_type': measurement
                }
            )

            if created:
                imported_count += 1
            else:
                skipped_count += 1

        except Exception as e:
            print(f"⚠️ Error on row {index}: {e}")
            continue

    print(f"✅ Successfully imported {imported_count} new records.")
    print(f"⏭️ Skipped {skipped_count} duplicate records (already existed).")

except FileNotFoundError:
    print("❌ Error: Could not find 'data/region_data.csv'. Make sure the file is in the 'data' folder.")
except Exception as e:
    print(f"❌ Critical Error: {e}")