from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.apps import apps
from farms.models import Farm, Activity, Harvest
from decimal import Decimal
from datetime import date, timedelta
import random

class Command(BaseCommand):
    help = 'Create test farm data for user khine'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Creating test farm data for user khine...')
        
        # Get existing user 'khine'
        try:
            user = User.objects.get(username='khine')
            self.stdout.write(self.style.SUCCESS(f'✅ Found user: {user.username} ({user.email})'))
        except User.DoesNotExist:
            self.stdout.write('❌ User khine not found, creating...')
            user = User.objects.create_user(
                username='khine',
                email='khin@gmail.com',
                password='password123',
                first_name='Khine',
                last_name='Farmer'
            )
            self.stdout.write(self.style.SUCCESS('✅ Created user: khine (password: password123)'))

        # Check if user already has a farm
        existing_farm = Farm.objects.filter(owner=user).first()
        if existing_farm:
            self.stdout.write(f'⚠️ User already has a farm: {existing_farm.name}')
            farm = existing_farm
            farm.name = "Green Valley Farm"
            farm.location = "Bago Region, Myanmar"
            farm.size_acres = 150.50
            farm.save()
            self.stdout.write(self.style.SUCCESS(f'✅ Updated farm: {farm.name}'))
        else:
            farm = Farm.objects.create(
                name="Green Valley Farm",
                owner=user,
                location='Bago Region, Myanmar',
                size_acres=150.50
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Created farm: {farm.name}'))

        # Add activities for the farm
        activities_data = [
            {
                'title': 'Prepare fields for planting',
                'description': 'Plow and prepare 25 acres for rice planting',
                'due_date': date.today() + timedelta(days=5),
                'priority': 'high'
            },
            {
                'title': 'Apply organic fertilizer',
                'description': 'Apply compost to the vegetable garden',
                'due_date': date.today() + timedelta(days=3),
                'priority': 'medium'
            },
            {
                'title': 'Irrigation maintenance',
                'description': 'Check and repair irrigation system in all fields',
                'due_date': date.today() + timedelta(days=7),
                'priority': 'high'
            },
            {
                'title': 'Pest control inspection',
                'description': 'Inspect all crops for pest infestation',
                'due_date': date.today() + timedelta(days=10),
                'priority': 'medium'
            },
            {
                'title': 'Harvest planning',
                'description': 'Plan harvest schedule for summer paddy',
                'due_date': date.today() + timedelta(days=14),
                'priority': 'low'
            }
        ]

        activity_count = 0
        for activity_data in activities_data:
            activity, created = Activity.objects.get_or_create(
                farm=farm,
                title=activity_data['title'],
                defaults={
                    'description': activity_data['description'],
                    'due_date': activity_data['due_date'],
                    'priority': activity_data['priority'],
                    'status': random.choice(['pending', 'in_progress'])
                }
            )
            if created:
                activity_count += 1
                self.stdout.write(f'  ✅ Created activity: {activity.title}')

        self.stdout.write(f'✅ Created {activity_count} activities')

        # Add harvest records with EXACT crop names from your database
        harvests_data = [
            {
                'crop_name': 'Paddy (Monsoon)',  # Exact match from your database
                'quantity': 45.5,
                'quality': 'Grade A',
                'date': date.today() - timedelta(days=15)
            },
            {
                'crop_name': 'Paddy (Summer)',  # This might not exist, we'll handle it
                'quantity': 38.2,
                'quality': 'Grade B',
                'date': date.today() - timedelta(days=25)
            },
            {
                'crop_name': 'Gram (Chick Pea)',  # Exact match from your database
                'quantity': 12.8,
                'quality': 'Grade A',
                'date': date.today() - timedelta(days=10)
            },
            {
                'crop_name': 'Maize',  # Exact match from your database
                'quantity': 22.5,
                'quality': 'Grade A',
                'date': date.today() - timedelta(days=20)
            }
        ]

        harvest_count = 0
        for harvest_data in harvests_data:
            # Try to get crop from crops app with exact match first
            try:
                Crop = apps.get_model('crops', 'Crop')
                # Try exact match
                crop = Crop.objects.filter(name__iexact=harvest_data['crop_name']).first()
                
                # If not found, try partial match
                if not crop:
                    crop = Crop.objects.filter(name__icontains=harvest_data['crop_name']).first()
                
                if not crop:
                    self.stdout.write(f'  ⚠️ Crop not found: {harvest_data["crop_name"]}')
                    self.stdout.write(f'     Available crops include: Paddy (Monsoon), Gram (Chick Pea), Maize, etc.')
                    continue
                    
            except Exception as e:
                self.stdout.write(f'  ⚠️ Error finding crop: {e}')
                continue
            
            # Create harvest record
            try:
                harvest, created = Harvest.objects.get_or_create(
                    crop=crop,
                    harvest_date=harvest_data['date'],
                    defaults={
                        'quantity_tonnes': harvest_data['quantity'],
                        'quality_grade': harvest_data['quality'],
                        'notes': f'Harvested {harvest_data["quantity"]} tonnes of {harvest_data["crop_name"]}'
                    }
                )
                if created:
                    harvest_count += 1
                    self.stdout.write(f'  ✅ Created harvest record: {harvest_data["crop_name"]}')
            except Exception as e:
                self.stdout.write(f'  ⚠️ Error creating harvest for {harvest_data["crop_name"]}: {e}')

        self.stdout.write(f'✅ Created {harvest_count} harvest records')

        # Summary
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('📊 FARM DATA SUMMARY')
        self.stdout.write('=' * 60)
        self.stdout.write(f'👤 User: {user.username} ({user.email})')
        self.stdout.write(f'🏠 Farm: {farm.name}')
        self.stdout.write(f'📍 Location: {farm.location}')
        self.stdout.write(f'📏 Size: {farm.size_acres} acres')
        self.stdout.write(f'📋 Activities: {Activity.objects.filter(farm=farm).count()}')
        self.stdout.write(f'🌾 Harvests: {Harvest.objects.count()}')
        
        self.stdout.write('\n📋 Your Activities:')
        for activity in Activity.objects.filter(farm=farm)[:5]:
            self.stdout.write(f'  - {activity.title} ({activity.status})')
        
        self.stdout.write('\n🌾 Harvest Records:')
        for harvest in Harvest.objects.all()[:5]:
            crop_name = harvest.crop.name if harvest.crop else "Unknown"
            self.stdout.write(f'  - {crop_name}: {harvest.quantity_tonnes} tonnes ({harvest.harvest_date})')
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✅ Test data creation complete!'))
        self.stdout.write('🔑 Login: khine / your-existing-password')
        self.stdout.write('🚀 Visit: http://localhost:8000/farms/dashboard/')
        self.stdout.write('📊 Visit: http://localhost:8000/market/')
        self.stdout.write('=' * 60)