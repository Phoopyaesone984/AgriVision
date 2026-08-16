import os
import json
import logging
import pickle
from typing import List, Dict, Any
from django.conf import settings
from dotenv import load_dotenv

# Import your models
from marketPrice.models import Crop, HarvestPrice, Profitability, RegionalProduction

logger = logging.getLogger(__name__)

# Use sentence_transformers directly for embeddings
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss
import requests

print("✓ Using simplified RAG service without LangChain")

class AgriRAGService:
    """Simplified RAG service without LangChain dependencies"""
    
    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            persist_directory = os.path.join(settings.BASE_DIR, 'faiss_db')
        
        self.persist_directory = persist_directory
        self.index = None
        self.documents = []
        self.metadata = []
        self.embeddings_model = None
        
        os.makedirs(self.persist_directory, exist_ok=True)
        
        self._initialize_embeddings()
        self._load_or_build()
    
    def _initialize_embeddings(self):
        """Initialize the embedding model"""
        try:
            print("🔧 Initializing embeddings with sentence_transformers...")
            self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✓ Embeddings initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing embeddings: {e}")
            raise
    
    def _load_or_build(self):
        """Load existing FAISS index or prepare to build"""
        index_path = os.path.join(self.persist_directory, "index.faiss")
        docs_path = os.path.join(self.persist_directory, "documents.pkl")
        
        if os.path.exists(index_path) and os.path.exists(docs_path):
            try:
                self.index = faiss.read_index(index_path)
                with open(docs_path, 'rb') as f:
                    self.documents, self.metadata = pickle.load(f)
                print(f"✓ Loaded {len(self.documents)} documents from {self.persist_directory}")
                return
            except Exception as e:
                print(f"⚠ Could not load existing index: {e}")
        
        print("ℹ No existing index found. Will build new one.")
        self.index = None
        self.documents = []
        self.metadata = []
    
    def _create_documents(self):
        """Create documents from database"""
        documents = []
        metadata = []
        
        print("📊 Creating documents from database...")
        
        # ============================================================
        # 1. CROP DATA
        # ============================================================
        crops = Crop.objects.all()
        print(f"  Found {crops.count()} crops")
        
        for crop in crops:
            prices = crop.harvest_prices.order_by('-year')[:5]
            price_lines = []
            for price in prices:
                price_lines.append(f"Year {price.year}: {price.price:,} Ks/Ton")
            
            profit = crop.profitability
            profit_text = ""
            if profit:
                if hasattr(profit, 'average_profit') and profit.average_profit:
                    profit_text = f"Average Profit: {profit.average_profit:,} Ks/acre"
                    if hasattr(profit, 'profit_margin') and profit.profit_margin:
                        profit_text += f", Margin: {profit.profit_margin}%"
                    if hasattr(profit, 'yield_tons_per_acre') and profit.yield_tons_per_acre:
                        profit_text += f", Yield: {profit.yield_tons_per_acre} tons/acre"
            
            content = f"""
Crop: {crop.name}
Category: {crop.category or 'N/A'}

Prices:
{chr(10).join(price_lines) if price_lines else 'No price data available'}

{profit_text}
"""
            documents.append(content)
            metadata.append({
                'crop_id': crop.id,
                'crop_name': crop.name,
                'category': crop.category or 'N/A',
                'document_type': 'crop_data'
            })
        
        # ============================================================
        # 2. PROFITABILITY-BASED PLANTING RECOMMENDATIONS
        # ============================================================
        print("  Adding planting recommendations...")
        
        profit_crops = Profitability.objects.select_related('crop').order_by('-profit_per_acre')[:20]
        
        if profit_crops:
            content = "🌾 TOP PROFITABLE CROPS TO PLANT:\n\n"
            for i, item in enumerate(profit_crops, 1):
                if item.profit_per_acre and item.profit_per_acre > 0:
                    content += f"{i}. {item.crop.name}: {int(item.profit_per_acre):,} Ks/acre\n"
            documents.append(content)
            metadata.append({
                'document_type': 'planting_recommendations',
                'crop_name': 'All Crops'
            })
        
        # ============================================================
        # 3. FARMING ADVICE
        # ============================================================
        print("  Adding farming advice...")
        
        crop_advice = [
            {
                'crop': 'Rice',
                'planting': 'Plant during monsoon season (June-July). Use 50-60 kg seeds/acre.',
                'soil': 'Clay or clay-loam soil, pH 5.5-6.5.',
                'watering': 'Keep field flooded with 2-5cm water. Drain 2 weeks before harvest.',
                'fertilizer': 'Apply NPK 16-16-8 at 50 kg/acre. Add urea 30 kg/acre during tillering.'
            },
            {
                'crop': 'Bean',
                'planting': 'Plant May-June. Use 30-40 kg seeds/acre.',
                'soil': 'Well-drained loam, pH 6.0-7.0.',
                'watering': 'Water every 7-10 days. Reduce after pods form.',
                'fertilizer': 'Apply DAP 18-46-0 at 100 kg/acre. Nitrogen not needed.'
            },
            {
                'crop': 'Onion',
                'planting': 'Plant November-December. Use sets or seedlings.',
                'soil': 'Sandy loam with good drainage, pH 6.0-7.0.',
                'watering': 'Water every 5-7 days. Stop 2 weeks before harvest.',
                'fertilizer': 'Apply NPK 12-24-12 at 40 kg/acre. Top dress urea 20 kg/acre after 1 month.'
            },
            {
                'crop': 'Garlic',
                'planting': 'Plant October-November. Use disease-free cloves.',
                'soil': 'Well-drained sandy loam, pH 6.0-7.5.',
                'watering': 'Water every 7-10 days. Reduce near maturity.',
                'fertilizer': 'Apply NPK 10-20-20 at 30 kg/acre. Top dress urea 15 kg/acre after 45 days.'
            },
            {
                'crop': 'Potato',
                'planting': 'Plant October-November. Use certified disease-free tubers.',
                'soil': 'Well-drained fertile loam, pH 5.5-6.5.',
                'watering': 'Water every 7-10 days. Consistent moisture critical.',
                'fertilizer': 'Apply NPK 15-15-15 at 50 kg/acre. Top dress urea 25 kg/acre at tuber initiation.'
            },
            {
                'crop': 'Tomato',
                'planting': 'Plant October-November. Use stakes or trellises.',
                'soil': 'Well-drained fertile soil, pH 6.0-7.0.',
                'watering': 'Water every 3-5 days. Consistent moisture prevents cracking.',
                'fertilizer': 'Apply NPK 12-24-12 at 50 kg/acre. Top dress K and Ca during fruiting.'
            },
            {
                'crop': 'Chilli',
                'planting': 'Plant September-October. Spacing: 30x45cm.',
                'soil': 'Well-drained loam, pH 6.0-7.0.',
                'watering': 'Water every 3-4 days. Avoid waterlogging.',
                'fertilizer': 'Apply NPK 16-16-16 at 40 kg/acre. Top dress urea 20 kg/acre every 30 days.'
            },
            {
                'crop': 'Maize',
                'planting': 'Plant May-June. Use 20-25 kg seeds/acre.',
                'soil': 'Well-drained fertile soil, pH 5.5-7.0.',
                'watering': 'Water every 7-10 days. Critical during tasseling.',
                'fertilizer': 'Apply NPK 15-15-15 at 60 kg/acre. Top dress urea 40 kg/acre at knee-high.'
            },
            {
                'crop': 'Groundnut',
                'planting': 'Plant May-June. Use 40-50 kg seeds/acre.',
                'soil': 'Well-drained sandy loam, pH 6.0-7.0.',
                'watering': 'Water every 10-15 days. Drought tolerant.',
                'fertilizer': 'Apply DAP 18-46-0 at 100 kg/acre. Calcium important for pods.'
            },
            {
                'crop': 'Sugarcane',
                'planting': 'Plant March-April or November-December. Use 3-5 tons seed cane/acre.',
                'soil': 'Well-drained fertile soil, pH 6.0-7.5.',
                'watering': 'Water every 10-15 days. Needs plenty of water.',
                'fertilizer': 'Apply NPK 14-14-14 at 80 kg/acre. Top dress N every 60 days.'
            },
            {
                'crop': 'Mango',
                'planting': 'Plant during rainy season. Use grafted seedlings. Spacing: 10x10m.',
                'soil': 'Well-drained loam, pH 5.5-7.0.',
                'watering': 'Water during dry season. Reduce after fruit set.',
                'fertilizer': 'Apply NPK 15-15-15 at 30 kg/acre. Add organic compost annually.'
            },
            {
                'crop': 'Wheat',
                'planting': 'Plant November-December. Use 60-80 kg seeds/acre.',
                'soil': 'Well-drained loam, pH 6.0-7.5.',
                'watering': 'Water every 7-10 days. Critical during tillering.',
                'fertilizer': 'Apply NPK 12-24-12 at 50 kg/acre. Top dress urea 30 kg/acre during tillering.'
            },
            {
                'crop': 'Cotton',
                'planting': 'Plant May-June. Use 20-25 kg seeds/acre.',
                'soil': 'Well-drained sandy loam, pH 6.0-7.5.',
                'watering': 'Water every 10-15 days. Tolerates moderate drought.',
                'fertilizer': 'Apply NPK 15-15-15 at 60 kg/acre. Top dress with nitrogen during boll formation.'
            },
            {
                'crop': 'Coffee',
                'planting': 'Plant during rainy season. Use shade trees. Spacing: 2x2m.',
                'soil': 'Rich, well-drained soil, pH 5.0-6.0. High organic matter.',
                'watering': 'Water during dry season. Consistent moisture for flowering.',
                'fertilizer': 'Apply NPK 12-12-17 at 40 kg/acre. Add organic compost regularly.'
            },
            {
                'crop': 'Tea',
                'planting': 'Plant during rainy season. Use rooted cuttings. Spacing: 1x1m.',
                'soil': 'Well-drained acidic soil, pH 4.5-5.5.',
                'watering': 'Regular watering during dry season.',
                'fertilizer': 'Apply NPK 15-15-15 at 30 kg/acre. Add organic compost annually.'
            }
        ]
        
        for advice in crop_advice:
            content = f"""
CROP: {advice['crop']}

PLANTING: {advice['planting']}
SOIL: {advice['soil']}
WATERING: {advice['watering']}
FERTILIZER: {advice['fertilizer']}
"""
            documents.append(content)
            metadata.append({
                'document_type': 'farming_advice',
                'crop_name': advice['crop']
            })
        
        # ============================================================
        # 4. FERTILIZER ADVICE
        # ============================================================
        print("  Adding fertilizer advice...")
        
        fertilizer_advice = [
            {
                'type': 'Compost',
                'description': 'Organic compost improves soil structure, adds nutrients, increases water retention.',
                'application': 'Apply 2-5 tons per acre. Work into top 15-20cm of soil.'
            },
            {
                'type': 'Urea (46-0-0)',
                'description': 'High nitrogen fertilizer for leafy growth. Best for rice, maize, and leafy vegetables.',
                'application': 'Apply 30-50 kg per acre in split doses during growing season.'
            },
            {
                'type': 'DAP (18-46-0)',
                'description': 'High phosphorus fertilizer for root development. Excellent for pulses, beans, and root crops.',
                'application': 'Apply 50-100 kg per acre at planting.'
            },
            {
                'type': 'NPK 15-15-15',
                'description': 'Balanced fertilizer for general use. Good for vegetables, cash crops, and field crops.',
                'application': 'Apply 40-60 kg per acre at planting and during early growth.'
            }
        ]
        
        for advice in fertilizer_advice:
            content = f"""
FERTILIZER: {advice['type']}
Description: {advice['description']}
Application: {advice['application']}
"""
            documents.append(content)
            metadata.append({
                'document_type': 'fertilizer_advice',
                'fertilizer_name': advice['type']
            })
        
        # ============================================================
        # 5. MARKET TRENDS
        # ============================================================
        print("  Adding market trends...")
        
        trend_content = "CURRENT MARKET TRENDS IN MYANMAR:\n\n"
        crops_with_prices = Crop.objects.filter(harvest_prices__isnull=False).distinct()
        
        for crop in crops_with_prices[:15]:
            prices = crop.harvest_prices.order_by('year')
            if prices.count() >= 2:
                price_list = list(prices)
                first_price = float(price_list[0].price)
                last_price = float(price_list[-1].price)
                if first_price > 0:
                    change = ((last_price - first_price) / first_price) * 100
                    trend = "UP" if change > 0 else "DOWN"
                    trend_content += f"{crop.name}: {trend} {abs(change):.1f}% (Current: {last_price:,.0f} Ks/Ton)\n"
        
        if len(trend_content) < 100:
            trend_content += "Limited price trend data available. Prices are generally stable."
        
        documents.append(trend_content)
        metadata.append({
            'document_type': 'market_trends',
            'crop_name': 'All Crops'
        })
        
        # ============================================================
        # 6. REGIONAL DATA & BEST MARKETS
        # ============================================================
        print("  Adding regional market data...")

        regional_data = RegionalProduction.objects.all()

        if regional_data.exists():
            print(f"  Found {regional_data.count()} regional records")
            
            region_dict = {}
            for item in regional_data:
                region = item.region
                if region not in region_dict:
                    region_dict[region] = {}
                
                crop = item.crop_category
                if crop not in region_dict[region]:
                    region_dict[region][crop] = 0
                if item.production_tons:
                    region_dict[region][crop] += float(item.production_tons)
            
            content = "📍 BEST MARKETS TO SELL CROPS IN MYANMAR:\n\n"
            content += "Based on regional production data, here are the key markets and what they produce:\n\n"
            
            for region in sorted(region_dict.keys()):
                crops_in_region = region_dict[region]
                total_prod = sum(crops_in_region.values())
                
                content += f"=== {region} REGION ===\n"
                content += f"Total Production: {int(total_prod):,} tons\n"
                content += "Major Crops Produced:\n"
                
                crops_sorted = sorted(crops_in_region.items(), key=lambda x: x[1], reverse=True)
                for crop_name, prod_value in crops_sorted[:7]:
                    if prod_value > 0:
                        content += f"  - {crop_name}: {int(prod_value):,} tons\n"
                content += "\n"
            
            content += "\n💡 RECOMMENDATIONS:\n"
            content += "• Yangon: Best for rice, beans, vegetables, and fruits - major export hub\n"
            content += "• Mandalay: Best for pulses, sesame, cotton, and groundnut - regional trading center\n"
            content += "• Bago: Best for rice, sugarcane, tapioca, and rubber - industrial hub\n"
            content += "• Ayeyawady: Best for rice, beans - major rice producer\n"
            content += "• Shan State: Best for corn, potato, tea, coffee - high-value crops\n"
            content += "• Magway: Best for sesame, groundnut, cotton, chillies - oilseed hub\n"
            content += "• Sagaing: Best for wheat, pulses, cotton - upper Myanmar market\n"
            
            documents.append(content)
            metadata.append({
                'document_type': 'market_locations',
                'crop_name': 'All Crops'
            })
            print("  ✅ Added regional market data")
        else:
            print("  ⚠ No regional data found in database!")
            content = """📍 BEST MARKETS TO SELL CROPS IN MYANMAR:

=== YANGON REGION ===
Total Production: High volume
Major Crops: Rice, Beans, Vegetables, Fruits
Market Access: Excellent - Major trading hub with export facilities

=== MANDALAY REGION ===
Total Production: Medium-high volume
Major Crops: Pulses, Sesame, Cotton, Groundnut
Market Access: Good - Regional trading center

=== SHAN STATE ===
Total Production: Medium volume
Major Crops: Corn, Potato, Tea, Coffee, Strawberry
Market Access: Good - Specialty crop hub

💡 RECOMMENDATION: 
- For rice: Sell in Yangon, Bago, or Ayeyawady
- For pulses/beans: Sell in Mandalay or Yangon
- For vegetables: Sell in Yangon or Nay Pyi Taw
- For coffee/tea: Sell in Shan State or Yangon
"""
            documents.append(content)
            metadata.append({
                'document_type': 'market_locations',
                'crop_name': 'All Crops'
            })
        
        # ============================================================
        # 7. WEATHER GUIDANCE
        # ============================================================
        print("  Adding weather guidance...")
        
        weather_content = """🌤️ WEATHER GUIDANCE FOR FARMERS IN MYANMAR:

1. MONSOON SEASON (June - October):
   - What to plant: Rice, paddy, maize, sugarcane
   - What to do: 
     - Ensure proper drainage to prevent waterlogging
     - Monitor for fungal diseases
     - Avoid applying pesticides during rain
     - Check flood risks in low-lying areas
   - Soil management: Heavy rain can leach nutrients. Apply fertilizer in split doses.

2. DRY SEASON (November - May):
   - What to plant: Pulses, beans, groundnut, sesame, cotton, wheat
   - What to do:
     - Focus on irrigation planning
     - Use drip irrigation for vegetables
     - Protect young plants from heat stress
     - Schedule harvesting during cooler hours (early morning)
   - Water management: Water early morning or late evening to reduce evaporation

3. EXTREME WEATHER CONDITIONS:
   - Strong Winds:
     * Protect young plants with windbreaks
     * Delay spraying pesticides
     * Support tall crops like maize and sugarcane
   - Heavy Rain:
     * Check and clear drainage systems
     * Protect soil from erosion with cover crops or mulch
     * Delay harvesting until fields dry
   - Heatwave (Above 40°C):
     * Increase irrigation frequency
     * Provide shade for sensitive crops
     * Protect workers from heat stress
   - Cold (Below 10°C):
     * Protect sensitive crops with mulch or row covers
     * Delay planting until temperatures rise

4. GENERAL WEATHER TIPS:
   - Always check the 7-day weather forecast before planning
   - Use weather-based irrigation scheduling
   - Monitor for pest outbreaks after rain
   - Plan fertilizer application around rainfall
   - Harvest during dry weather when possible
   - Keep records of weather and its impact on crops

5. RAINFALL REQUIREMENTS BY CROP:
   - Rice: 1,500-2,000 mm/season (flooded)
   - Maize: 400-600 mm/season
   - Beans: 300-500 mm/season
   - Vegetables: 400-600 mm/season
   - Sugarcane: 1,000-1,500 mm/season

6. WEATHER-BASED DECISIONS:
   - Planting: Plant at the start of rainy season for rain-fed crops
   - Fertilizing: Apply fertilizer before expected rain
   - Spraying: Spray when wind is low and no rain expected for 24 hours
   - Harvesting: Harvest during dry weather for better quality and storage
"""
        documents.append(weather_content)
        metadata.append({
            'document_type': 'weather_guidance',
            'crop_name': 'All Crops'
        })
        print("  ✅ Added weather guidance")
        
        # ============================================================
        # 8. GENERAL FARMING KNOWLEDGE - IMPROVED WITH KEYWORDS
        # ============================================================
        print("  Adding general farming knowledge...")

        general_knowledge = [
            {
                'topic': 'Crop Rotation',
                'keywords': 'crop rotation rotate crops soil fertility pest control sustainable farming',
                'content': """CROP ROTATION - COMPLETE GUIDE:

What is Crop Rotation?
Crop rotation is the practice of growing different crops in the same area in sequential seasons. This is one of the most important sustainable farming practices.

Benefits of Crop Rotation:
1. Prevents soil nutrient depletion - different crops use different nutrients
2. Breaks pest and disease cycles - pests that attack one crop won't survive when another crop is planted
3. Improves soil structure - different root systems improve soil health
4. Reduces weed pressure - different crops compete with different weeds
5. Increases overall yield by 10-30%
6. Reduces need for chemical fertilizers and pesticides

Recommended Rotations for Myanmar:
- 3-Year Cycle: Rice → Legumes (Pulses/Beans) → Oilseeds (Sesame/Groundnut)
- 2-Year Cycle: Maize → Pulses → Vegetables
- 3-Year Cycle: Cotton → Pulses → Fallow
- Vegetable Rotation: Leafy greens → Fruiting vegetables → Root vegetables

Rules for Effective Crop Rotation:
1. Rotate deep-rooted and shallow-rooted crops
2. Rotate heavy feeders (rice, maize) with light feeders (pulses)
3. Include legumes every 2-3 years (they fix nitrogen in soil)
4. Avoid planting same crop family in succession
5. Include a fallow period if possible

Example Rotation Schedule:
Year 1: Rice (heavy feeder, grass family)
Year 2: Beans/Pulses (nitrogen fixer, legume family)
Year 3: Sesame/Groundnut (oilseed, different family)
Year 4: Rice again (rotation completed)

Why Rotate Crops?
- Rice depletes nitrogen, beans add nitrogen back
- Pest populations crash when their host crop is removed
- Soil structure improves with diverse root systems
- Farmers can get better yields with less fertilizer"""
            },
            {
                'topic': 'Tomato Harvesting',
                'keywords': 'tomato harvest when to harvest tomatoes harvesting tomatoes tomato picking ripe tomatoes',
                'content': """TOMATO HARVESTING - COMPLETE GUIDE:

When to Harvest Tomatoes:
1. Color: Harvest when tomatoes are fully colored (red, orange, yellow, or pink depending on variety)
2. Firmness: Fruit should be firm but slightly give when gently squeezed
3. Stage: Harvest at "breaker stage" (when 10-30% color shows) for longer storage
4. Days: Most tomatoes are ready 70-85 days after transplanting
5. Size: Fruit should be full-sized for the variety

Harvesting Tips:
1. Pick every 3-4 days during peak season
2. Use clean, sharp shears or twist fruit off gently
3. Leave stem attached if possible (prevents disease)
4. Harvest in early morning when temperatures are cool
5. Handle gently to prevent bruising
6. Sort by size and ripeness immediately

Storage Tips:
1. Store at room temperature (18-22°C) for best flavor
2. Do NOT refrigerate green tomatoes (stops ripening)
3. Refrigerate only fully ripe tomatoes if needed
4. Store stem-side down to reduce moisture loss
5. Keep away from direct sunlight

Signs Tomatoes are Ready:
- Full color development
- Slight give when squeezed
- Easy to remove from vine
- Strong tomato smell
- Glossy, smooth skin

After Harvest:
1. Clean and sort immediately
2. Remove damaged or diseased fruit
3. Package carefully for market
4. Transport during cooler hours"""
            },
            {
                'topic': 'How to Start Organic Farming',
                'keywords': 'organic farming start organic farming organic agriculture natural farming chemical-free farming',
                'content': """HOW TO START ORGANIC FARMING - STEP BY STEP GUIDE:

What is Organic Farming?
Organic farming avoids synthetic pesticides, fertilizers, and GMOs. It uses natural methods to grow healthy crops and maintain soil health.

Step 1: Understand the Principles
1. Build healthy soil (healthy soil = healthy plants)
2. Use natural pest control methods
3. Practice crop rotation
4. Maintain biodiversity
5. Use organic seeds and inputs

Step 2: Soil Preparation for Organic Farming
1. Test your soil (pH, nutrients, organic matter)
2. Add organic compost (2-5 tons per acre)
3. Use green manure (plant legumes and plow under)
4. Maintain soil organic matter above 2%
5. Avoid chemical fertilizers and pesticides

Step 3: Choose Organic Inputs
1. Organic fertilizers:
   - Compost (homemade or purchased)
   - Animal manure (aged 6+ months)
   - Green manure crops
   - Biofertilizers (Rhizobium, Azotobacter)
   - Bone meal, blood meal, fish emulsion
2. Natural pest control:
   - Neem oil spray (1:100 dilution with water)
   - Garlic-chilli solution (natural repellent)
   - Companion planting (marigolds, basil, mint)
   - Beneficial insects (ladybugs, parasitic wasps)
   - Yellow sticky traps
3. Organic seeds: Use certified organic seeds when possible

Step 4: Best Crops for Organic Farming in Myanmar
1. Coffee (high demand, good prices)
2. Tea (established organic markets)
3. Pulses (beans, chickpeas, mung beans)
4. Sesame (export opportunities)
5. Rice (growing organic market)
6. Vegetables (local demand)
7. Fruits (mango, banana, citrus)

Step 5: Certification (Optional but Recommended)
1. Apply for organic certification
2. Keep detailed records
3. Follow certification standards
4. Pay certification fees
5. Get inspected annually

Common Organic Practices:
1. Crop rotation (prevents pest buildup)
2. Mulching (reduces weeds, retains moisture)
3. Intercropping (growing multiple crops together)
4. Composting (recycles farm waste)
5. Biological pest control (uses natural predators)

Benefits of Organic Farming:
1. Better prices for organic produce (20-50% higher)
2. Healthier food (no chemical residues)
3. Better soil health long-term
4. Lower input costs over time
5. Sustainable and environmentally friendly
6. Export opportunities

Challenges of Organic Farming:
1. Requires more knowledge and skill
2. May have lower yields initially
3. More labor intensive
4. Higher risk of pest damage
5. Certification can be expensive

Tips for Success:
1. Start small (1-2 acres)
2. Learn from experienced organic farmers
3. Join farmer cooperatives
4. Find organic buyers before planting
5. Keep good records
6. Be patient (soil takes time to improve)"""
            },
            {
                'topic': 'What to Do When It Rains on Farm',
                'keywords': 'rain farming rain flooding wet weather rainy season farming what to do when it rains',
                'content': """WHAT TO DO WHEN IT RAINS ON YOUR FARM - COMPLETE GUIDE:

BEFORE RAIN:
1. Check weather forecast for expected rainfall amount
2. Clear all drainage channels to prevent waterlogging
3. Apply fertilizer before rain if needed (rain helps dissolve it)
4. Delay planting if heavy rain is expected
5. Move all equipment, tools, and harvested crops to covered storage
6. Secure tarps over vulnerable crops
7. Check roofs and storage areas for leaks

DURING RAIN:
1. Stop all outdoor field work
2. Monitor fields for flooding regularly
3. Keep drainage systems clear (remove blockages)
4. Protect stored crops from moisture
5. Stay indoors during lightning
6. Do not operate machinery on wet ground

AFTER RAIN:
1. Check fields for standing water
2. Assess any flood damage
3. Remove debris and blockages from drainage
4. Apply fungicide if humidity is high (prevents diseases)
5. Check for pest outbreaks (rain can bring pests)
6. Resume field work when conditions are suitable (usually 1-2 days after heavy rain)
7. Apply additional fertilizer if rain washed away nutrients
8. Check for soil erosion and take corrective measures

Crop-Specific Rain Advice:
- RICE: Check water levels, ensure proper drainage
- VEGETABLES: Check for flooding, protect seedlings
- PULSES: Watch for standing water (they don't like wet feet)
- FRUITS: Check for fruit drop (heavy rain can cause fruit drop)
- COFFEE/TEA: Check for soil erosion on slopes

SAFETY TIPS:
1. Avoid working outdoors during lightning
2. Do not operate machinery on wet, slippery ground
3. Wash hands thoroughly after working in wet fields
4. Check for leeches and other pests after working in water
5. Dry equipment thoroughly to prevent rust

RAIN AND IRRIGATION:
1. Reduce irrigation during and after rain
2. Check soil moisture before resuming irrigation
3. Adjust irrigation schedule based on rainfall
4. Use rain gauge to measure actual rainfall

Rainfall Requirements by Crop:
- Rice: 1,500-2,000 mm/season (flooded)
- Maize: 400-600 mm/season
- Beans: 300-500 mm/season
- Vegetables: 400-600 mm/season
- Sugarcane: 1,000-1,500 mm/season"""
            },
            {
                'topic': 'Soil Health Management',
                'keywords': 'soil health soil management soil fertility improve soil soil testing',
                'content': """SOIL HEALTH MANAGEMENT - COMPLETE GUIDE:

HOW TO IMPROVE SOIL HEALTH:
1. Add organic compost annually (2-5 tons/acre)
2. Practice crop rotation
3. Use cover crops during off-season
4. Reduce tillage to preserve soil structure
5. Maintain soil pH between 5.5 and 7.0
6. Apply lime if soil is too acidic
7. Apply sulfur if soil is too alkaline

SIGNS OF HEALTHY SOIL:
- Dark color (rich in organic matter)
- Good structure (crumbly)
- Earthworms present
- Good drainage
- Sweet smell
- Moderate pH (5.5-7.0)

SOIL FERTILITY MANAGEMENT:
- Test soil every 1-2 years
- Apply fertilizer based on soil test results
- Use organic matter to improve nutrient retention
- Avoid over-fertilization (can damage crops and environment)
- Balance nitrogen, phosphorus, and potassium applications"""
            }
        ]

        for knowledge in general_knowledge:
            content = f"""
KNOWLEDGE TOPIC: {knowledge['topic']}

Keywords: {knowledge['keywords']}

{knowledge['content']}
"""
            documents.append(content)
            metadata.append({
                'document_type': 'general_knowledge',
                'topic': knowledge['topic']
            })

        print(f"  ✅ Added general farming knowledge")

        print(f"  Created {len(documents)} documents")
        return documents, metadata

    def build_vector_store(self, force_rebuild: bool = False):
        """Build the vector store using FAISS"""
        if self.index is not None and not force_rebuild:
            print("ℹ Vector store already exists. Use force_rebuild=True to rebuild.")
            return

        print("🔄 Building vector store from database...")

        documents, metadata = self._create_documents()

        if not documents:
            print("⚠ No documents created!")
            return

        self.documents = documents
        self.metadata = metadata

        print(f"  Generating embeddings for {len(documents)} documents...")
        embeddings = self.embeddings_model.encode(documents, normalize_embeddings=True)

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings.astype(np.float32))

        faiss.write_index(self.index, os.path.join(self.persist_directory, "index.faiss"))
        with open(os.path.join(self.persist_directory, "documents.pkl"), 'wb') as f:
            pickle.dump((documents, metadata), f)

        print(f"✅ Vector store saved to {self.persist_directory}")

    def get_relevant_documents(self, query: str, k: int = 5) -> List[Dict]:
        """Retrieve relevant documents for a query"""
        if self.index is None or not self.documents:
            print("⚠ Vector store not initialized! Build it first.")
            return []

        try:
            query_embedding = self.embeddings_model.encode([query], normalize_embeddings=True)

            distances, indices = self.index.search(query_embedding.astype(np.float32), k)

            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.documents):
                    results.append({
                        'content': self.documents[idx],
                        'metadata': self.metadata[idx],
                        'score': float(distances[0][i])
                    })

            return results

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

    def get_relevant_context(self, query: str, k: int = 5) -> List[str]:
        """Get relevant context strings"""
        results = self.get_relevant_documents(query, k)
        return [r['content'] for r in results]

    def generate_response(self, query: str, k: int = 5) -> dict:
        """Generate response using Groq API directly"""
        load_dotenv()

        groq_api_key = os.getenv('GROQ_API_KEY')
        if not groq_api_key:
            return {
                'response': "Error: GROQ_API_KEY not found. Please set it in your .env file.",
                'context': [],
                'sources': []
            }

        results = self.get_relevant_documents(query, k=k)

        if not results:
            return {
                'response': "I don't have any information about that in my database yet.",
                'context': [],
                'sources': []
            }

        context_text = "\n\n".join([r['content'] for r in results])

        prompt = f"""You are AgriVision AI, an agricultural market intelligence assistant for Myanmar.

You have access to the following information:
1. Crop prices and profitability
2. Farming advice for specific crops
3. Fertilizer recommendations
4. Market trends
5. Regional market data (where to sell)
6. Weather guidance (rain, heat, wind, cold)
7. General farming knowledge (soil, irrigation, pests, harvesting, crop rotation, organic farming)
8. Plant growth stages and harvesting guides

IMPORTANT INSTRUCTIONS:
1. If the user asks about a general topic (crop rotation, organic farming, harvesting, soil health, etc.), use the general knowledge documents
2. If the user asks about a specific crop, use both crop-specific and general knowledge
3. If the user asks about weather (rain, heat, cold, wind), use the weather guidance
4. If you don't find relevant information, say "I don't have enough information about that in my database."

Answer the user's question based ONLY on the context below.

Context:
{context_text}

User Question: {query}

Answer:"""

        try:
            headers = {
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a helpful agricultural market intelligence assistant for Myanmar farmers. Provide practical, actionable advice based on the context provided."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 600
            }

            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data['choices'][0]['message']['content']
            else:
                ai_response = f"Error from Groq API: {response.status_code}"

            sources = []
            seen = set()
            for r in results:
                crop_name = r['metadata'].get('crop_name', 'Unknown')
                if crop_name not in seen:
                    seen.add(crop_name)
                    sources.append({
                        'crop': crop_name,
                        'category': r['metadata'].get('category', 'N/A')
                    })

            return {
                'response': ai_response,
                'context': [r['content'] for r in results],
                'sources': sources[:5]
            }

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                'response': f"Error: {str(e)}",
                'context': [],
                'sources': []
            }