# sales/tests.py
from django.test import TestCase
from django.urls import reverse
from users.models import User
from vehicles.models import Vehicle, Brand

class PurchaseTest(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name='Toyota')
        self.seller = User.objects.create_user(username='seller', password='testpass', role='seller')
        self.buyer = User.objects.create_user(username='buyer', password='testpass', role='customer')
        self.vehicle = Vehicle.objects.create(
            brand=self.brand,
            model='Corolla',
            year=2020,
            price=20000,
            mileage=15000,
            transmission='automatic',
            fuel_type='gasoline',
            status='used',
            created_by=self.seller,
            is_active=True,
            sold=False
        )

    def test_purchase_success(self):
        self.client.login(username='buyer', password='testpass')
        response = self.client.post(reverse('sales:purchase', args=[self.vehicle.id]))
        self.assertEqual(response.status_code, 302)  # Redirección
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.sold)
        # Verificar que se creó la venta
        from sales.models import Sale
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.first()
        self.assertEqual(sale.buyer, self.buyer)
        self.assertEqual(sale.seller, self.seller)
        self.assertEqual(sale.amount, self.vehicle.price)
