from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection, connections, transaction, IntegrityError
from django.http import Http404
from django.test import TransactionTestCase

from vehicles.models import Brand, Vehicle
from .models import Sale
from . import workflow


class SalesTransactionTests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user(
            username="seller", email="seller@example.com"
        )
        self.buyer = User.objects.create_user(
            username="buyer", email="buyer@example.com"
        )
        self.other = User.objects.create_user(
            username="other", email="other@example.com"
        )
        self.admin = User.objects.create_user(
            username="admin", email="admin@example.com", role="admin"
        )
        brand = Brand.objects.create(name="Toyota")
        self.vehicle = Vehicle.objects.create(
            brand=brand,
            model="Corolla",
            year=2020,
            price=20000,
            mileage=0,
            transmission="manual",
            fuel_type="diesel",
            created_by=self.seller,
        )

    @patch("sales.services.send_offer_notifications")
    def test_notification_only_after_commit(self, notify):
        with transaction.atomic():
            workflow.create_offer(self.vehicle.pk, self.buyer, Decimal("15000"))
            self.assertFalse(notify.called)
        notify.assert_called_once()

    @patch("sales.services.send_offer_notifications")
    def test_rollback_removes_offer_and_notification(self, notify):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                workflow.create_offer(self.vehicle.pk, self.buyer, Decimal("15000"))
                raise RuntimeError("Abort")
        self.assertFalse(Sale.objects.exists())
        notify.assert_not_called()

    @patch("sales.services.send_reservation_notifications")
    def test_reservation_rollback_restores_vehicle(self, notify):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                workflow.reserve(self.vehicle.pk, self.buyer)
                raise RuntimeError("Abort")
        self.vehicle.refresh_from_db()
        self.assertFalse(self.vehicle.reserved)
        self.assertFalse(Sale.objects.exists())
        notify.assert_not_called()

    @patch(
        "sales.services.send_offer_notifications", side_effect=RuntimeError("SMTP down")
    )
    def test_notification_failure_does_not_rollback_committed_offer(self, notify):
        with self.assertLogs("sales.workflow", level="ERROR"):
            workflow.create_offer(self.vehicle.pk, self.buyer, Decimal("15000"))
        self.assertEqual(Sale.objects.count(), 1)

    def test_database_prevents_duplicate_pending_offer(self):
        workflow.create_offer(self.vehicle.pk, self.buyer, Decimal("15000"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Sale.objects.create(
                vehicle=self.vehicle,
                buyer=self.buyer,
                seller=self.seller,
                amount=20000,
                offered_price=14000,
            )

    def test_database_prevents_invalid_amount(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Sale.objects.create(
                vehicle=self.vehicle, buyer=self.buyer, seller=self.seller, amount=-1
            )

    def run_race(self, operations):
        barrier = Barrier(len(operations))

        def worker(operation):
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                try:
                    operation()
                    return "ok"
                except Http404, ValueError:
                    return "rejected"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(operations)) as executor:
            return list(executor.map(worker, operations))

    @skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locking")
    @patch("sales.services.send_reservation_notifications")
    def test_concurrent_reservations_only_one_winner(self, notify):
        results = self.run_race(
            [
                lambda: workflow.reserve(self.vehicle.pk, self.buyer),
                lambda: workflow.reserve(self.vehicle.pk, self.other),
            ]
        )
        self.assertCountEqual(results, ["ok", "rejected"])
        self.assertEqual(Sale.objects.filter(status="reserved").count(), 1)
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.reserved)
        self.assertEqual(self.vehicle.reserved_by_id, Sale.objects.get().buyer_id)

    @skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locking")
    @patch("sales.services.send_offer_accepted_notification")
    @patch("sales.services.send_offer_rejected_notification")
    def test_concurrent_acceptance_only_one_sale(self, *mocks):
        first = Sale.objects.create(
            vehicle=self.vehicle,
            buyer=self.buyer,
            seller=self.seller,
            amount=20000,
            offered_price=15000,
        )
        second = Sale.objects.create(
            vehicle=self.vehicle,
            buyer=self.other,
            seller=self.seller,
            amount=20000,
            offered_price=14000,
        )
        results = self.run_race(
            [
                lambda: workflow.decide_offer(first.pk, self.admin, True),
                lambda: workflow.decide_offer(second.pk, self.admin, True),
            ]
        )
        self.assertCountEqual(results, ["ok", "rejected"])
        self.assertEqual(Sale.objects.filter(status="offer_accepted").count(), 1)
        self.assertEqual(Sale.objects.filter(status="offer_rejected").count(), 1)
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.sold)

    @skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locking")
    @patch("sales.services.send_offer_notifications")
    def test_concurrent_duplicate_offer_only_one_pending(self, notify):
        results = self.run_race(
            [
                lambda: workflow.create_offer(
                    self.vehicle.pk, self.buyer, Decimal("15000")
                ),
                lambda: workflow.create_offer(
                    self.vehicle.pk, self.buyer, Decimal("14000")
                ),
            ]
        )
        self.assertCountEqual(results, ["ok", "rejected"])
        self.assertEqual(Sale.objects.filter(status="offer_pending").count(), 1)

    @skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locking")
    @patch("sales.services.send_offer_notifications")
    def test_concurrent_purchase_and_offer_leaves_no_pending(self, notify):
        results = self.run_race(
            [
                lambda: workflow.complete_purchase(self.vehicle.pk, self.buyer),
                lambda: workflow.create_offer(
                    self.vehicle.pk, self.other, Decimal("14000")
                ),
            ]
        )
        self.assertIn("ok", results)
        self.assertEqual(Sale.objects.filter(status="completed").count(), 1)
        self.assertFalse(Sale.objects.filter(status="offer_pending").exists())
