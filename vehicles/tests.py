# vehicles/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Vehicle, Brand

User = get_user_model()

class VehicleModelTest(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name='Toyota')
        self.user = User.objects.create_user(username='test', password='test')

    def test_vehicle_creation(self):
        vehicle = Vehicle.objects.create(
            brand=self.brand,
            model='Corolla',
            year=2020,
            price=20000,
            mileage=15000,
            transmission='automatic',
            fuel_type='gasoline',
            status='used',
            created_by=self.user
        )
        self.assertEqual(str(vehicle), 'Toyota Corolla (2020)')
