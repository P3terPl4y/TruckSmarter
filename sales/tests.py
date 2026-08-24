from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from vehicles.models import Vehicle, Brand
from users.models import Profile
from .models import Sale

User = get_user_model()

class SaleModelTest(TestCase):
    """Pruebas para el modelo Sale."""

    def setUp(self):
        self.brand = Brand.objects.create(name='Toyota')
        self.seller = User.objects.create_user(
            username='seller',
            email='seller@test.com',
            password='testpass123',
            role='seller'
        )
       
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            role='customer'
        )
       
        self.vehicle = Vehicle.objects.create(
            brand=self.brand,
            model='Corolla',
            year=2020,
            price=20000.00,
            mileage=15000,
            transmission='automatic',
            fuel_type='gasoline',
            status='used',
            created_by=self.seller,
            is_active=True,
            sold=False,
        )

    def test_sale_creation(self):
        """Verifica que se pueda crear una venta."""
        sale = Sale.objects.create(
            vehicle=self.vehicle,
            buyer=self.buyer,
            seller=self.seller,
            amount=self.vehicle.price,
            status='completed',
            buyer_phone='123456789',
            buyer_email='buyer@test.com'
        )
        self.assertEqual(sale.vehicle, self.vehicle)
        self.assertEqual(sale.buyer, self.buyer)
        self.assertEqual(sale.seller, self.seller)
        self.assertEqual(sale.amount, self.vehicle.price)
        self.assertEqual(str(sale), f"Venta de {self.vehicle} - {self.buyer.username}")


class PurchaseViewTest(TestCase):
    """Pruebas para la vista purchase_vehicle."""

    def setUp(self):
        self.client = Client()
        self.brand = Brand.objects.create(name='Toyota')
        self.seller = User.objects.create_user(
            username='seller',
            email='seller@test.com',
            password='testpass123',
            role='seller'
        )
       
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            role='customer'
        )
        
        self.vehicle = Vehicle.objects.create(
            brand=self.brand,
            model='Corolla',
            year=2020,
            price=20000.00,
            mileage=15000,
            transmission='automatic',
            fuel_type='gasoline',
            status='used',
            created_by=self.seller,
            is_active=True,
            sold=False,
        )

    def test_purchase_vehicle_success(self):
        """Verifica que la compra sea exitosa."""
        self.client.force_login(self.buyer)
        response = self.client.post(reverse('sales:purchase', args=[self.vehicle.id]))
        self.assertEqual(response.status_code, 302)  # Redirección
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.sold)
        self.assertFalse(self.vehicle.is_active)
        # Verificar que se creó la venta
        sale = Sale.objects.first()
        self.assertIsNotNone(sale)
        self.assertEqual(sale.buyer, self.buyer)
        self.assertEqual(sale.seller, self.seller)
        self.assertEqual(sale.amount, self.vehicle.price)

    def test_purchase_vehicle_own_vehicle(self):
        """Verifica que no se pueda comprar el propio vehículo."""
        self.client.force_login(self.seller)
        response = self.client.post(reverse('sales:purchase', args=[self.vehicle.id]))
        self.assertEqual(response.status_code, 302)  # Redirección
        self.assertFalse(self.vehicle.sold)  # No se vendió

    def test_purchase_vehicle_unauthenticated(self):
        """Verifica que usuarios no autenticados no puedan comprar."""
        response = self.client.post(reverse('sales:purchase', args=[self.vehicle.id]))
        self.assertRedirects(response, f'/users/login/?next={reverse("sales:purchase", args=[self.vehicle.id])}')

    def test_purchase_vehicle_already_sold(self):
        """Verifica que no se pueda comprar un vehículo ya vendido."""
        self.vehicle.sold = True
        self.vehicle.save()
        self.client.force_login(self.buyer)
        response = self.client.post(reverse('sales:purchase', args=[self.vehicle.id]))
        self.assertEqual(response.status_code, 404)  # No encontrado


class PurchaseHistoryTest(TestCase):
    """Pruebas para la vista purchase_history."""

    def setUp(self):
        self.client = Client()
        self.brand = Brand.objects.create(name='Toyota')
        self.seller = User.objects.create_user(
            username='seller',
            email='seller@test.com',
            password='testpass123',
            role='seller'
        )
        
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@test.com',
            password='testpass123',
            role='customer'
        )
        
        self.vehicle = Vehicle.objects.create(
            brand=self.brand,
            model='Corolla',
            year=2020,
            price=20000.00,
            mileage=15000,
            transmission='automatic',
            fuel_type='gasoline',
            status='used',
            created_by=self.seller,
            is_active=True,
            sold=False,
        )
        self.sale = Sale.objects.create(
            vehicle=self.vehicle,
            buyer=self.buyer,
            seller=self.seller,
            amount=self.vehicle.price,
            status='completed'
        )

    def test_purchase_history_authenticated(self):
        """Verifica que el historial de compras cargue correctamente."""
        self.client.force_login(self.buyer)
        response = self.client.get(reverse('sales:history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Corolla')

    def test_purchase_history_unauthenticated(self):
        """Verifica que usuarios no autenticados no puedan ver el historial."""
        response = self.client.get(reverse('sales:history'))
        self.assertRedirects(response, f'/users/login/?next={reverse("sales:history")}')
