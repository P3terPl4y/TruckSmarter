from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from vehicles.models import Brand, Vehicle

from .models import Sale

User = get_user_model()


class SaleModelTest(TestCase):
    def setUp(self):
        self.brand = Brand.objects.create(name="Toyota")
        self.seller = User.objects.create_user(
            username="seller",
            email="seller@test.com",
            password="testpass123",
            role="seller",
        )
        self.buyer = User.objects.create_user(
            username="buyer",
            email="buyer@test.com",
            password="testpass123",
            role="customer",
        )
        self.vehicle = Vehicle.objects.create(
            brand=self.brand,
            model="Corolla",
            year=2020,
            price=20000.00,
            mileage=15000,
            transmission="automatic",
            fuel_type="gasoline",
            status="used",
            created_by=self.seller,
            is_active=True,
            sold=False,
        )

    def test_offer_creation(self):
        sale = Sale.objects.create(
            vehicle=self.vehicle,
            buyer=self.buyer,
            seller=self.seller,
            amount=self.vehicle.price,
            offered_price=Decimal("15000.00"),
            status="offer_pending",
            buyer_phone="123456789",
            buyer_email="buyer@test.com",
        )
        self.assertEqual(sale.offered_price, Decimal("15000.00"))
        self.assertEqual(sale.status, "offer_pending")


class MakeOfferViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.brand = Brand.objects.create(name="Toyota")
        self.seller = User.objects.create_user(
            username="seller",
            email="seller@test.com",
            password="testpass123",
            role="seller",
        )
        self.buyer = User.objects.create_user(
            username="buyer",
            email="buyer@test.com",
            password="testpass123",
            role="customer",
        )
        self.vehicle = Vehicle.objects.create(
            brand=self.brand,
            model="Corolla",
            year=2020,
            price=20000.00,
            mileage=15000,
            transmission="automatic",
            fuel_type="gasoline",
            status="used",
            created_by=self.seller,
            is_active=True,
            sold=False,
        )

    def test_make_offer_success(self):
        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse("sales:make_offer", args=[self.vehicle.id]),
            {"offered_price": "15000"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Sale.objects.filter(vehicle=self.vehicle, status="offer_pending").exists()
        )

    def test_make_offer_own_vehicle(self):
        self.client.force_login(self.seller)
        response = self.client.post(
            reverse("sales:make_offer", args=[self.vehicle.id]),
            {"offered_price": "15000"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Sale.objects.filter(vehicle=self.vehicle, status="offer_pending").exists()
        )

    def test_make_offer_unauthenticated(self):
        response = self.client.post(
            reverse("sales:make_offer", args=[self.vehicle.id]),
            {"offered_price": "15000"},
        )
        self.assertRedirects(
            response,
            f'/users/login/?next={reverse("sales:make_offer", args=[self.vehicle.id])}',
        )

    def test_make_offer_price_too_high(self):
        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse("sales:make_offer", args=[self.vehicle.id]),
            {"offered_price": "25000"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            Sale.objects.filter(vehicle=self.vehicle, status="offer_pending").exists()
        )
        # Verificar mensaje de error (opcional)

    def test_make_offer_duplicate_pending(self):
        Sale.objects.create(
            vehicle=self.vehicle,
            buyer=self.buyer,
            seller=self.seller,
            amount=self.vehicle.price,
            offered_price=Decimal("15000"),
            status="offer_pending",
        )
        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse("sales:make_offer", args=[self.vehicle.id]),
            {"offered_price": "14000"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Sale.objects.filter(vehicle=self.vehicle, status="offer_pending").count(), 1
        )


class OfferAcceptRejectTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.brand = Brand.objects.create(name="Toyota")
        self.admin = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="adminpass"
        )
        self.seller = User.objects.create_user(
            username="seller",
            email="seller@test.com",
            password="testpass123",
            role="seller",
        )
        self.buyer = User.objects.create_user(
            username="buyer",
            email="buyer@test.com",
            password="testpass123",
            role="customer",
        )
        self.vehicle = Vehicle.objects.create(
            brand=self.brand,
            model="Corolla",
            year=2020,
            price=20000.00,
            mileage=15000,
            transmission="automatic",
            fuel_type="gasoline",
            status="used",
            created_by=self.seller,
            is_active=True,
            sold=False,
        )
        self.sale = Sale.objects.create(
            vehicle=self.vehicle,
            buyer=self.buyer,
            seller=self.seller,
            amount=self.vehicle.price,
            offered_price=Decimal("15000"),
            status="offer_pending",
        )

    def test_accept_offer_admin(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("sales:accept_offer", args=[self.sale.id]))
        self.assertEqual(response.status_code, 302)
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, "offer_accepted")
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.sold)
        self.assertFalse(self.vehicle.is_active)

    def test_accept_offer_non_admin(self):
        self.client.force_login(self.seller)
        response = self.client.post(reverse("sales:accept_offer", args=[self.sale.id]))
        self.assertEqual(
            response.status_code, 302
        )  # Redirige a login? o 403? Depende de user_passes_test.

    def test_reject_offer_admin(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("sales:reject_offer", args=[self.sale.id]))
        self.assertEqual(response.status_code, 302)
        self.sale.refresh_from_db()
        self.assertEqual(self.sale.status, "offer_rejected")
        self.vehicle.refresh_from_db()
        self.assertFalse(self.vehicle.sold)
        self.assertTrue(self.vehicle.is_active)
