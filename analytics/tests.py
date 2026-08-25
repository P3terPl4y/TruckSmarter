from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from vehicles.models import Vehicle, Brand
from analytics.models import VehicleView
from analytics.decorators import track_vehicle_view

User = get_user_model()

class VehicleViewTest(TestCase):
    def setUp(self):
        cache.clear()  # ✅ Limpiar cache entre pruebas
        
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='test', password='test')
        
        # Crear una marca
        self.brand = Brand.objects.create(name='Test Brand')
        
        # Crear un vehículo con todos los campos obligatorios
        self.vehicle = Vehicle.objects.create(
            brand=self.brand,
            model='Test Model',
            year=2023,
            price=10000,
            mileage=5000,
            transmission='Manual',      # Ajusta según tus opciones
            fuel_type='Gasoline',       # Ajusta según tus opciones
            status='available',         # Ajusta según tus opciones
            description='Test description',
            is_active=True,
        )

    def test_view_increment(self):
        request = self.factory.get('/vehicles/1/')
        request.user = self.user
        
        # Simular sesión
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()

        @track_vehicle_view
        def dummy_view(request, pk):
            pass

        dummy_view(request, pk=self.vehicle.id)

        # Verificar que se creó un registro y el contador subió a 1
        self.assertEqual(VehicleView.objects.count(), 1)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.view_count, 1)

    def test_no_duplicate_view(self):
        request = self.factory.get('/vehicles/1/')
        request.user = self.user
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()

        @track_vehicle_view
        def dummy_view(request, pk):
            pass

        # Primera visita
        dummy_view(request, pk=self.vehicle.id)
        self.assertEqual(VehicleView.objects.count(), 1)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.view_count, 1)

        # Segunda visita (no debe incrementar)
        dummy_view(request, pk=self.vehicle.id)
        self.assertEqual(VehicleView.objects.count(), 1)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.view_count, 1)
