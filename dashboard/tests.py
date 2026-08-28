from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from sales.models import Sale
from vehicles.models import Vehicle, Brand

User = get_user_model()

class DashboardTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username='admin', email='admin@test.com', password='adminpass')
        self.user = User.objects.create_user(username='user', email='user@test.com', password='userpass', role='customer')
        self.brand = Brand.objects.create(name='Toyota')
        self.vehicle = Vehicle.objects.create(
            brand=self.brand,
            model='Corolla',
            year=2020,
            price=20000,
            mileage=15000,
            transmission='automatic',
            fuel_type='gasoline',
            status='used',
            created_by=self.admin,
            is_active=True,
            sold=False,
        )
        self.sale = Sale.objects.create(
            vehicle=self.vehicle,
            buyer=self.user,
            seller=self.admin,
            amount=20000,
            offered_price=15000,
            status='offer_pending'
        )

    def test_dashboard_home_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_home_non_admin(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('dashboard:home'))
        self.assertEqual(response.status_code, 403)

    def test_offer_list_admin(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard:offer_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Toyota Corolla')
