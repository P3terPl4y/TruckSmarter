from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class UpgradeMigrationTests(TransactionTestCase):
    def test_upgrade_preserves_history_and_reports_duplicate_emails(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        old_targets = [
            ("users", "0001_initial"),
            ("vehicles", "0001_initial"),
            ("sales", "0002_initial"),
        ]
        executor.migrate(old_targets)
        old = executor.loader.project_state(old_targets).apps
        User = old.get_model("users", "User")
        Brand = old.get_model("vehicles", "Brand")
        Vehicle = old.get_model("vehicles", "Vehicle")
        Sale = old.get_model("sales", "Sale")
        duplicate = None
        try:
            seller = User.objects.create(
                username="seller", email="Seller@example.com", password="!"
            )
            buyer = User.objects.create(
                username="buyer", email="buyer@example.com", password="!"
            )
            brand = Brand.objects.create(name="Toyota")
            vehicle = Vehicle.objects.create(
                brand=brand,
                created_by=seller,
                model="Corolla",
                year=2020,
                price=20000,
                mileage=0,
                transmission="manual",
                fuel_type="gasoline",
                status="used",
            )
            sale = Sale.objects.create(
                vehicle=vehicle,
                buyer=buyer,
                seller=seller,
                amount=20000,
                offered_price=15000,
                status="offer_pending",
            )
            duplicate = User.objects.create(
                username="duplicate", email="seller@example.com", password="!"
            )
            with self.assertRaisesMessage(RuntimeError, "emails duplicados"):
                MigrationExecutor(connection).migrate(latest)
            duplicate.delete()
            duplicate = None
            MigrationExecutor(connection).migrate(latest)
            from sales.models import Sale as CurrentSale

            self.assertEqual(CurrentSale.objects.get(pk=sale.pk).offered_price, 15000)
            self.assertEqual(CurrentSale.objects.get(pk=sale.pk).vehicle_id, vehicle.pk)
        finally:
            if duplicate is not None:
                duplicate.delete()
            MigrationExecutor(connection).migrate(latest)
