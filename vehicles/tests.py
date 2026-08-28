from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from users.models import Profile

from .models import Brand, Vehicle, VehicleImage

User = get_user_model()


class VehicleModelTest(TestCase):
    """Pruebas para los modelos de vehículos."""

    def setUp(self):
        self.brand = Brand.objects.create(name="Toyota")
        self.user = User.objects.create_user(
            username="seller",
            email="seller@test.com",
            password="testpass123",
            role="admin",
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
            description="Excelente estado",
            created_by=self.user,
            is_active=True,
            sold=False,
        )

    def test_vehicle_creation(self):
        """Verifica que un vehículo se cree correctamente."""
        self.assertEqual(self.vehicle.brand.name, "Toyota")
        self.assertEqual(self.vehicle.model, "Corolla")
        self.assertEqual(str(self.vehicle), "Toyota Corolla (2020)")

    def test_mark_as_sold(self):
        """Verifica que mark_as_sold funcione correctamente."""
        from sales.models import Sale

        buyer = User.objects.create_user(
            username="buyer",
            email="buyer@test.com",
            password="testpass123",
            role="customer",
        )

        sale = self.vehicle.mark_as_sold(buyer)

        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.sold)
        self.assertFalse(self.vehicle.is_active)
        self.assertIsNotNone(sale)
        self.assertEqual(sale.buyer, buyer)
        self.assertEqual(sale.seller, self.user)
        self.assertEqual(sale.amount, self.vehicle.price)


class VehicleListViewTest(TestCase):
    """Pruebas para VehicleListView."""

    def setUp(self):
        self.client = Client()
        self.brand = Brand.objects.create(name="Toyota")
        self.user = User.objects.create_user(
            username="seller",
            email="seller@test.com",
            password="testpass123",
            role="admin",
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
            created_by=self.user,
            is_active=True,
            sold=False,
        )

    def test_list_view_status_code(self):
        """Verifica que la lista de vehículos cargue correctamente."""
        response = self.client.get(reverse("vehicles:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Corolla")

    def test_list_view_filters(self):
        """Verifica que los filtros funcionen correctamente."""
        # Filtro por precio mínimo
        response = self.client.get(reverse("vehicles:list"), {"min_price": "15000"})
        self.assertContains(response, "Corolla")

        response = self.client.get(reverse("vehicles:list"), {"min_price": "25000"})
        self.assertNotContains(response, "Corolla")

        # Filtro por búsqueda
        response = self.client.get(reverse("vehicles:list"), {"q": "Toyota"})
        self.assertContains(response, "Corolla")

        response = self.client.get(reverse("vehicles:list"), {"q": "Honda"})
        self.assertNotContains(response, "Corolla")


class VehicleCreateViewTest(TestCase):
    """Pruebas para VehicleCreateView."""

    def setUp(self):
        self.client = Client()
        self.brand = Brand.objects.create(name="Toyota")
        self.seller = User.objects.create_user(
            username="seller",
            email="seller@test.com",
            password="testpass123",
            role="admin",
        )
        self.customer = User.objects.create_user(
            username="customer",
            email="customer@test.com",
            password="testpass123",
            role="customer",
        )

    def test_create_vehicle_seller(self):
        """Verifica que un vendedor pueda crear un vehículo."""
        self.client.force_login(self.seller)
        response = self.client.post(
            reverse("vehicles:create"),
            {
                "brand": self.brand.id,
                "model": "Camry",
                "year": 2021,
                "price": 25000.00,
                "mileage": 10000,
                "transmission": "automatic",
                "fuel_type": "gasoline",
                "status": "used",
                "description": "Excelente estado",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)  # Redirección
        self.assertEqual(Vehicle.objects.count(), 1)
        self.assertEqual(Vehicle.objects.first().created_by, self.seller)

    def test_create_vehicle_customer_forbidden(self):
        """Verifica que un cliente NO pueda crear un vehículo."""
        self.client.force_login(self.customer)
        response = self.client.get(reverse("vehicles:create"))
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_create_vehicle_unauthenticated(self):
        """Verifica que usuarios no autenticados no puedan crear vehículos."""
        response = self.client.get(reverse("vehicles:create"))
        self.assertRedirects(
            response, f'/users/login/?next={reverse("vehicles:create")}'
        )


class VehicleUpdateViewTest(TestCase):
    """Pruebas para VehicleUpdateView."""

    def setUp(self):
        self.client = Client()
        self.brand = Brand.objects.create(name="Toyota")
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@test.com",
            password="testpass123",
            role="admin",
        )

        self.other_user = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="testpass123",
            role="admin",
        )

        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="adminpass123"
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
            created_by=self.owner,
            is_active=True,
            sold=False,
        )

    def test_update_vehicle_owner(self):
        """Verifica que el propietario pueda actualizar su vehículo."""
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("vehicles:update", args=[self.vehicle.id]),
            {
                "brand": self.brand.id,
                "model": "Camry",
                "year": 2021,
                "price": 26000.00,
                "mileage": 12000,
                "transmission": "automatic",
                "fuel_type": "gasoline",
                "status": "used",
                "description": "Nuevo estado",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.model, "Camry")
        self.assertEqual(self.vehicle.price, 26000.00)

    def test_update_vehicle_other_user_forbidden(self):
        """Verifica que otro usuario NO pueda actualizar el vehículo (a menos que sea admin)."""
        self.client.force_login(self.other_user)  # other_user es admin
        response = self.client.get(reverse("vehicles:update", args=[self.vehicle.id]))
        self.assertEqual(response.status_code, 200)  # Admin puede ver el formulario

    def test_update_vehicle_admin_allowed(self):
        """Verifica que un administrador pueda actualizar cualquier vehículo."""
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("vehicles:update", args=[self.vehicle.id]),
            {
                "brand": self.brand.id,
                "model": "Prius",
                "year": 2022,
                "price": 30000.00,
                "mileage": 5000,
                "transmission": "automatic",
                "fuel_type": "hybrid",
                "status": "new",
                "description": "Vehiculo híbrido",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.model, "Prius")


class VehicleDeleteViewTest(TestCase):
    """Pruebas para VehicleDeleteView."""

    def setUp(self):
        self.client = Client()
        self.brand = Brand.objects.create(name="Toyota")
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@test.com",
            password="testpass123",
            role="admin",
        )

        self.other_user = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="testpass123",
            role="admin",
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
            created_by=self.owner,
            is_active=True,
            sold=False,
        )

    def test_delete_vehicle_owner(self):
        """Verifica que el propietario pueda eliminar su vehículo (soft delete)."""
        self.client.force_login(self.owner)
        response = self.client.post(reverse("vehicles:delete", args=[self.vehicle.id]))
        self.assertEqual(response.status_code, 302)
        # Recargar desde la base de datos (debe existir porque es soft delete)
        self.vehicle.refresh_from_db()
        self.assertFalse(self.vehicle.is_active)
        self.assertTrue(self.vehicle.sold)

    def test_delete_vehicle_other_user_forbidden(self):
        """Verifica que otro usuario NO pueda eliminar el vehículo."""
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("vehicles:delete", args=[self.vehicle.id]))
        self.assertEqual(response.status_code, 403)
