"""Fixtures with real business roles for functional tests."""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from vehicles.models import Brand, Vehicle


class MarketplaceTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        for name, role in (
            ("owner", "seller"),
            ("other", "seller"),
            ("buyer", "customer"),
            ("admin", "admin"),
        ):
            setattr(
                cls,
                name,
                User.objects.create_user(
                    username=name,
                    email=f"{name}@example.com",
                    password="SecurePass123!",
                    role=role,
                ),
            )
        cls.superuser = User.objects.create_superuser(
            username="root", email="root@example.com", password="SecurePass123!"
        )
        cls.brand = Brand.objects.create(name="Toyota")
        cls.vehicle = Vehicle.objects.create(
            brand=cls.brand,
            model="Corolla",
            year=2020,
            price=Decimal("20000.50"),
            mileage=1000,
            transmission="manual",
            fuel_type="gasoline",
            status="used",
            created_by=cls.owner,
        )

    def setUp(self):
        cache.clear()

    def vehicle_data(self, **overrides):
        data = dict(
            brand=self.brand.pk,
            model="Camry",
            year=2021,
            price="15000.25",
            mileage=2000,
            transmission="automatic",
            fuel_type="diesel",
            status="used",
            is_active=True,
        )
        data.update(overrides)
        return data

    def offer(self, buyer=None, **overrides):
        from sales.models import Sale

        data = dict(
            vehicle=self.vehicle,
            buyer=buyer or self.buyer,
            seller=self.owner,
            amount=self.vehicle.price,
            offered_price=Decimal("15000.00"),
            status="offer_pending",
        )
        data.update(overrides)
        return Sale.objects.create(**data)
