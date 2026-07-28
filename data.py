import pandas as pd

# Load all files
prices = pd.read_csv('crop_prices_2019_2025.csv')
yields = pd.read_csv('table_3_04_average_yield_per_harvested_acre.csv')
daily = pd.read_csv('market_prices_yangon_july_2026.csv')

# Clean yield data - keep only 2020-2025 columns
yield_clean = yields[['sn_crop', '2020_2021', '2021_2022', '2022_2023', '2023_2024', '2024_2025']]

# Merge prices with yields on crop name
master = prices.merge(yield_clean, left_on='crop_name', right_on='sn_crop', how='left')

# Add daily prices
master = master.merge(daily[['Commodity', '24-07-2026']], 
                      left_on='crop_name', 
                      right_on='Commodity', 
                      how='left')

# Create profitability columns
master['profit_2024_25'] = master['price_2024_25'] * (master['2024_2025'] * 0.0205)  # Convert baskets to tons

# Save to Excel
master.to_excel('master_market_intelligence.xlsx', index=False)
print("Master file created!")