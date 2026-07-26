from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from ..models import MarketPrice, PriceAlert, MarketNews
from crops.models import Crop
import random

class MarketPriceService:
    """Service class for market price operations"""
    
    @staticmethod
    def get_current_prices():
        """Get the latest price for each crop in each market"""
        # Get all crops
        crops = Crop.objects.filter(is_active=True)
        result = []
        
        for crop in crops:
            # Get latest price for each market
            markets = MarketPrice.MARKET_CHOICES
            crop_prices = []
            
            for market_code, market_name in markets:
                latest_price = MarketPrice.objects.filter(
                    crop=crop,
                    market_name=market_code
                ).order_by('-recorded_date').first()
                
                if latest_price:
                    crop_prices.append({
                        'market': market_code,
                        'price': latest_price,
                        'trend': MarketPriceService.calculate_trend(crop.id, market_code)
                    })
            
            if crop_prices:
                result.append({
                    'crop': crop,
                    'prices': crop_prices
                })
        
        return result
    
    @staticmethod
    def calculate_trend(crop_id, market_name, days=30):
        """Calculate price trend over last X days"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        prices = MarketPrice.objects.filter(
            crop_id=crop_id,
            market_name=market_name,
            recorded_date__gte=start_date
        ).order_by('recorded_date')
        
        if prices.count() < 2:
            return {'direction': 'stable', 'change': 0}
        
        first_price = prices.first().price_per_tonne
        last_price = prices.last().price_per_tonne
        
        if first_price == 0:
            return {'direction': 'stable', 'change': 0}
        
        change_percent = ((last_price - first_price) / first_price) * 100
        
        if change_percent > 2:
            return {'direction': 'up', 'change': change_percent}
        elif change_percent < -2:
            return {'direction': 'down', 'change': abs(change_percent)}
        else:
            return {'direction': 'stable', 'change': 0}
    
    @staticmethod
    def get_price_history(crop_id, market_name, days=180):
        """Get price history for charts"""
        start_date = timezone.now().date() - timedelta(days=days)
        
        prices = MarketPrice.objects.filter(
            crop_id=crop_id,
            market_name=market_name,
            recorded_date__gte=start_date
        ).order_by('recorded_date')
        
        return prices
    
    @staticmethod
    def get_alerts_for_user(user):
        """Get all active alerts for a user"""
        return PriceAlert.objects.filter(user=user, is_active=True)
    
    @staticmethod
    def get_recent_news(limit=5):
        """Get recent market news"""
        return MarketNews.objects.all()[:limit]


class SampleDataLoader:
    """Load sample market price data"""
    
    @staticmethod
    def load_sample_prices():
        """Load 6 months of sample price data"""
        # Get all active crops
        crops = Crop.objects.filter(is_active=True)
        
        if not crops:
            print("No crops found. Please create crops first.")
            return 0
        
        # Define base prices for different crop types (MMK per tonne)
        base_prices = {
            'RICE': 850000,
            'CORN': 650000,
            'WHEAT': 700000,
            'SOYBEAN': 950000,
            'COTTON': 1200000,
            'VEGETABLE': 500000,
            'FRUIT': 800000,
            'OTHER': 600000,
        }
        
        markets = ['Yangon', 'Mandalay', 'Nay Pyi Taw', 'Mawlamyine']
        market_variations = {
            'Yangon': 1.0,
            'Mandalay': 0.95,
            'Nay Pyi Taw': 0.92,
            'Mawlamyine': 0.88,
        }
        
        # Generate 6 months of data
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=180)
        
        created_count = 0
        
        for crop in crops:
            # Get base price for crop type
            base_price = base_prices.get(crop.crop_type, 600000)
            
            for market in markets:
                market_base = base_price * market_variations.get(market, 1.0)
                
                # Generate price for each day
                current_date = start_date
                day_count = 0
                
                while current_date <= end_date:
                    # Add random variation (-15% to +15%)
                    variation = random.uniform(-0.15, 0.15)
                    
                    # Add seasonal trend (sine wave over 6 months)
                    seasonal = 0.1 * (day_count / 180) * 3.14159
                    price = market_base * (1 + variation + seasonal * 0.1)
                    
                    # Round to nearest 100
                    price = round(price / 100) * 100
                    
                    # Create price record
                    MarketPrice.objects.create(
                        crop=crop,
                        market_name=market,
                        price_per_tonne=price,
                        price_per_kg=price / 1000,
                        source='Sample',
                        recorded_date=current_date
                    )
                    
                    created_count += 1
                    current_date += timedelta(days=1)
                    day_count += 1
        
        return created_count
    
    @staticmethod
    def load_sample_news():
        """Load sample market news"""
        news_items = [
            {
                'title': 'Rice Prices Surge in Yangon Market',
                'content': 'Rice prices have increased by 5% this week due to high demand from export markets. Traders expect prices to remain high through the next month.',
                'source': 'Myanmar Agri News',
                'is_important': True
            },
            {
                'title': 'Corn Harvest Expected to Be Strong',
                'content': 'Farmers in the Mandalay region report a strong corn harvest this season. Prices may stabilize or decrease slightly in the coming weeks.',
                'source': 'Agricultural Daily',
                'is_important': False
            },
            {
                'title': 'Coffee Prices Reach New High',
                'content': 'Global coffee prices have reached a 3-year high. Myanmar coffee farmers are benefiting from increased demand for premium Arabica beans.',
                'source': 'Commodity News',
                'is_important': True
            },
            {
                'title': 'Government Announces Agricultural Subsidies',
                'content': 'The government has announced new subsidies for fertilizer and seeds to support farmers. Applications open next month.',
                'source': 'Government Gazette',
                'is_important': True
            },
            {
                'title': 'Weather Forecast Favors Crop Growing Season',
                'content': 'Favorable weather conditions are expected for all growing regions. Farmers are advised to monitor irrigation levels carefully.',
                'source': 'Weather Service',
                'is_important': False
            }
        ]
        
        created_count = 0
        for news in news_items:
            MarketNews.objects.get_or_create(
                title=news['title'],
                defaults=news
            )
            created_count += 1
        
        return created_count
    

class UnitConverter:
    """Convert prices between different units"""
    
    # Conversion factors (multiply to get price in that unit)
    CONVERSION_FACTORS = {
        'tonne': 1.0,      # Base unit
        'kg': 1000.0,      # 1 tonne = 1000 kg
        'viss': 613.5,     # 1 tonne ≈ 613.5 viss (1 viss = 1.63 kg)
        'pyi': 50.0,       # 1 tonne = 50 pyi (adjust as needed)
        'basket': 40.0,    # 1 tonne = 40 baskets (adjust as needed)
    }
    
    # Display names
    UNIT_NAMES = {
        'tonne': 'Tonne (1000 kg)',
        'kg': 'Kilogram (kg)',
        'viss': 'Viss (ပိဿာ)',
        'pyi': 'Pyi (ပြည်)',
        'basket': 'Basket (ဘူး)',
    }
    
    @staticmethod
    def convert_price(price_per_tonne, from_unit='tonne', to_unit='tonne'):
        """Convert price from one unit to another"""
        if from_unit == to_unit:
            return price_per_tonne
        
        # Convert to base (tonne) first
        if from_unit == 'tonne':
            base_price = price_per_tonne
        else:
            from_factor = UnitConverter.CONVERSION_FACTORS.get(from_unit, 1.0)
            base_price = price_per_tonne * from_factor
        
        # Convert from base to target
        to_factor = UnitConverter.CONVERSION_FACTORS.get(to_unit, 1.0)
        converted_price = base_price / to_factor
        
        return converted_price
    
    @staticmethod
    def get_unit_symbol(unit):
        """Get symbol for unit"""
        symbols = {
            'tonne': 't',
            'kg': 'kg',
            'viss': 'ပိဿာ',
            'pyi': 'ပြည်',
            'basket': 'ဘူး',
        }
        return symbols.get(unit, unit)
    
    @staticmethod
    def get_unit_label(unit):
        """Get display label for unit"""
        return UnitConverter.UNIT_NAMES.get(unit, unit)