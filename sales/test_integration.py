from django.test import Client
from django.urls import reverse
from core.testing import MarketplaceTestCase
from .models import Sale


class MarketplaceIntegrationTests(MarketplaceTestCase):
    def test_offer_to_acceptance_with_real_csrf_and_history(self):
        buyer = Client(enforce_csrf_checks=True)
        buyer.force_login(self.buyer)
        detail = reverse("vehicles:detail", args=[self.vehicle.pk])
        response = buyer.get(detail)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'max="20000.49"')
        token = buyer.cookies["csrftoken"].value
        response = buyer.post(
            reverse("sales:make_offer", args=[self.vehicle.pk]),
            {
                "offered_price": "15000.25",
                "offer_comment": "Entrega en La Habana",
                "csrfmiddlewaretoken": token,
            },
        )
        self.assertEqual(response.status_code, 302)
        sale = Sale.objects.get(status="offer_pending")
        admin = Client(enforce_csrf_checks=True)
        admin.force_login(self.admin)
        response = admin.get(reverse("dashboard:offer_list"))
        self.assertContains(response, "Entrega en La Habana")
        self.assertEqual(
            admin.post(
                reverse("sales:accept_offer", args=[sale.pk]),
                {"csrfmiddlewaretoken": admin.cookies["csrftoken"].value},
            ).status_code,
            302,
        )
        history = buyer.get(reverse("sales:history"))
        self.assertContains(history, "Oferta aceptada")
        self.assertContains(history, "15000,25")
        self.assertEqual(buyer.get(detail).status_code, 200)
        self.assertEqual(Client().get(detail).status_code, 404)
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.sold)

    def test_reservation_buttons_follow_state(self):
        self.client.force_login(self.buyer)
        detail = reverse("vehicles:detail", args=[self.vehicle.pk])
        self.assertContains(self.client.get(detail), "Reservar vehículo")
        self.client.post(reverse("sales:reserve", args=[self.vehicle.pk]))
        response = self.client.get(detail)
        self.assertContains(response, "Cancelar reserva")
        self.assertNotContains(response, "Hacer oferta")
        self.client.post(reverse("sales:cancel_reservation", args=[self.vehicle.pk]))
        self.assertContains(self.client.get(detail), "Reservar vehículo")
