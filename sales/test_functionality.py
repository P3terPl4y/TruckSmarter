from decimal import Decimal
from unittest.mock import patch
from django.core import mail
from django.test import Client
from django.urls import reverse
from core.testing import MarketplaceTestCase
from .models import Sale


class SalesFunctionalTests(MarketplaceTestCase):
    def test_reserve_get_does_not_mutate(self):
        self.client.force_login(self.buyer)
        self.assertEqual(
            self.client.get(
                reverse("sales:reserve", args=[self.vehicle.pk])
            ).status_code,
            405,
        )
        self.vehicle.refresh_from_db()
        self.assertFalse(self.vehicle.reserved)
        self.assertFalse(Sale.objects.exists())

    def test_reservation_cycle_and_ownership(self):
        self.client.force_login(self.buyer)
        self.assertEqual(
            self.client.post(
                reverse("sales:reserve", args=[self.vehicle.pk])
            ).status_code,
            302,
        )
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.reserved)
        self.assertEqual(self.vehicle.reserved_by, self.buyer)
        sale = Sale.objects.get()
        self.assertEqual(sale.get_status_display(), "Reservada")
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.post(
                reverse("sales:cancel_reservation", args=[self.vehicle.pk])
            ).status_code,
            404,
        )
        self.client.force_login(self.buyer)
        self.assertEqual(
            self.client.post(
                reverse("sales:cancel_reservation", args=[self.vehicle.pk])
            ).status_code,
            302,
        )
        self.vehicle.refresh_from_db()
        sale.refresh_from_db()
        self.assertFalse(self.vehicle.reserved)
        self.assertIsNone(self.vehicle.reserved_by)
        self.assertEqual(sale.status, "cancelled")

    def test_all_mutation_endpoints_require_post(self):
        sale = self.offer()
        self.client.force_login(self.admin)
        for name, pk in [
            ("make_offer", self.vehicle.pk),
            ("reserve", self.vehicle.pk),
            ("cancel_reservation", self.vehicle.pk),
            ("accept_offer", sale.pk),
            ("reject_offer", sale.pk),
        ]:
            with self.subTest(name=name):
                self.assertEqual(
                    self.client.get(reverse("sales:" + name, args=[pk])).status_code,
                    405,
                )
        sale.refresh_from_db()
        self.assertEqual(sale.status, "offer_pending")

    def test_malformed_prices_never_create_offer(self):
        self.client.force_login(self.buyer)
        for value in [
            "NaN",
            "sNaN",
            "Infinity",
            "-Infinity",
            "abc",
            "0",
            "-1",
            "1.001",
            "1e999999",
            "20000.50",
            "999999999999",
        ]:
            with self.subTest(value=value):
                response = self.client.post(
                    reverse("sales:make_offer", args=[self.vehicle.pk]),
                    {"offered_price": value},
                )
                self.assertEqual(response.status_code, 302)
                self.assertFalse(Sale.objects.exists())

    def test_comment_limit(self):
        self.client.force_login(self.buyer)
        self.client.post(
            reverse("sales:make_offer", args=[self.vehicle.pk]),
            {"offered_price": "100", "offer_comment": "x" * 651},
        )
        self.assertFalse(Sale.objects.exists())

    def test_multiple_buyers_can_offer_but_one_pending_per_buyer(self):
        for buyer in (self.buyer, self.other, self.buyer):
            self.client.force_login(buyer)
            self.assertEqual(
                self.client.post(
                    reverse("sales:make_offer", args=[self.vehicle.pk]),
                    {"offered_price": "10000"},
                ).status_code,
                302,
            )
        self.assertEqual(Sale.objects.count(), 2)

    def test_offer_after_cancelled_reservation_has_no_null_comparison(self):
        self.offer(status="cancelled", offered_price=None)
        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse("sales:make_offer", args=[self.vehicle.pk]),
            {"offered_price": "10000"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Sale.objects.filter(status="offer_pending").exists())

    def test_higher_repeat_offer_is_rejected(self):
        self.offer(status="offer_rejected", offered_price=Decimal("10000"))
        self.client.force_login(self.buyer)
        self.client.post(
            reverse("sales:make_offer", args=[self.vehicle.pk]),
            {"offered_price": "11000"},
        )
        self.assertFalse(Sale.objects.filter(status="offer_pending").exists())

    def test_reserved_vehicle_does_not_accept_new_offers(self):
        self.vehicle.reserved = True
        self.vehicle.reserved_by = self.other
        self.vehicle.save()
        self.client.force_login(self.buyer)
        self.assertEqual(
            self.client.post(
                reverse("sales:make_offer", args=[self.vehicle.pk]),
                {"offered_price": "100"},
            ).status_code,
            404,
        )
        self.assertFalse(Sale.objects.exists())

    def test_accept_closes_other_offers_and_reservation(self):
        selected = self.offer()
        alternative = self.offer(buyer=self.other)
        reservation = self.offer(status="reserved", offered_price=None)
        self.vehicle.reserved = True
        self.vehicle.reserved_by = self.buyer
        self.vehicle.save()
        self.client.force_login(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("sales:accept_offer", args=[selected.pk])
            )
        self.assertEqual(response.status_code, 302)
        selected.refresh_from_db()
        alternative.refresh_from_db()
        reservation.refresh_from_db()
        self.assertEqual(selected.status, "offer_accepted")
        self.assertEqual(alternative.status, "offer_rejected")
        self.assertEqual(reservation.status, "cancelled")
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.sold)
        self.assertIsNone(self.vehicle.reserved_by)
        self.assertTrue(mail.outbox)
        self.assertEqual(
            self.client.post(
                reverse("sales:accept_offer", args=[alternative.pk])
            ).status_code,
            404,
        )

    def test_reject_does_not_cancel_unrelated_reservation(self):
        sale = self.offer()
        self.vehicle.reserved = True
        self.vehicle.reserved_by = self.other
        self.vehicle.save()
        self.client.force_login(self.admin)
        self.client.post(reverse("sales:reject_offer", args=[sale.pk]))
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.reserved)
        self.assertEqual(self.vehicle.reserved_by, self.other)

    def test_admin_role_and_forbidden_seller(self):
        sale = self.offer()
        url = reverse("sales:accept_offer", args=[sale.pk])
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(url).status_code, 302)

    def test_history_is_private(self):
        self.offer()
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("sales:history")), "Corolla")
        self.client.force_login(self.buyer)
        self.assertContains(self.client.get(reverse("sales:history")), "Corolla")

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        sale = self.offer()
        self.assertEqual(
            client.post(reverse("sales:accept_offer", args=[sale.pk])).status_code, 403
        )

    def test_orphan_listing_cannot_be_reserved(self):
        self.vehicle.created_by = None
        self.vehicle.save()
        self.client.force_login(self.buyer)
        response = self.client.post(reverse("sales:reserve", args=[self.vehicle.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Sale.objects.exists())

    def test_withdraw_listing_closes_pending_transactions(self):
        sale = self.offer()
        reservation = self.offer(status="reserved", offered_price=None)
        self.vehicle.reserved = True
        self.vehicle.reserved_by = self.buyer
        self.vehicle.save()
        self.client.force_login(self.owner)
        self.client.post(reverse("vehicles:delete", args=[self.vehicle.pk]))
        sale.refresh_from_db()
        reservation.refresh_from_db()
        self.vehicle.refresh_from_db()
        self.assertEqual(sale.status, "cancelled")
        self.assertEqual(reservation.status, "cancelled")
        self.assertFalse(self.vehicle.reserved)
        self.assertIsNone(self.vehicle.reserved_by)

    def test_reservation_and_cancellation_deliver_notifications(self):
        self.client.force_login(self.buyer)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("sales:reserve", args=[self.vehicle.pk]))
        recipients = {address for message in mail.outbox for address in message.to}
        self.assertEqual(recipients, {self.buyer.email, self.superuser.email})
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("sales:cancel_reservation", args=[self.vehicle.pk])
            )
        self.assertEqual(len(mail.outbox), 2)
        self.assertTrue(
            all("cancelada" in message.subject.lower() for message in mail.outbox)
        )

    @patch("sales.services.send_mail", side_effect=OSError("SMTP down"))
    def test_smtp_failure_preserves_offer(self, send):
        self.client.force_login(self.buyer)
        with self.assertLogs("sales.services", level="ERROR"):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("sales:make_offer", args=[self.vehicle.pk]),
                    {"offered_price": "10000"},
                )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Sale.objects.filter(status="offer_pending").exists())
