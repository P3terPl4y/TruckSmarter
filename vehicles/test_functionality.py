from decimal import Decimal
from io import BytesIO
from PIL import Image
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from core.testing import MarketplaceTestCase
from .forms import VehicleForm
from .models import Vehicle


class VehicleFunctionalTests(MarketplaceTestCase):
    def test_real_seller_can_publish(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse("vehicles:create"), self.vehicle_data())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Vehicle.objects.filter(model="Camry", created_by=self.owner).exists()
        )

    def test_update_permission_matrix(self):
        url = reverse("vehicles:update", args=[self.vehicle.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        for user, status in (
            (self.owner, 200),
            (self.other, 403),
            (self.buyer, 403),
            (self.admin, 200),
            (self.superuser, 200),
        ):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(url).status_code, status)

    def test_owner_updates_without_changing_ownership(self):
        self.client.force_login(self.owner)
        data = self.vehicle_data()
        data["created_by"] = self.other.pk
        response = self.client.post(
            reverse("vehicles:update", args=[self.vehicle.pk]), data
        )
        self.assertEqual(response.status_code, 302)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.model, "Camry")
        self.assertEqual(self.vehicle.created_by, self.owner)

    def test_delete_permission_matrix(self):
        url = reverse("vehicles:delete", args=[self.vehicle.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        for user, status in (
            (self.owner, 200),
            (self.other, 403),
            (self.buyer, 403),
            (self.admin, 200),
            (self.superuser, 200),
        ):
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(url).status_code, status)

    def test_get_delete_is_read_only_and_post_withdraws_without_sale(self):
        self.client.force_login(self.owner)
        url = reverse("vehicles:delete", args=[self.vehicle.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.is_active)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.vehicle.refresh_from_db()
        self.assertFalse(self.vehicle.is_active)
        self.assertFalse(self.vehicle.sold)
        self.assertFalse(self.vehicle.sales.exists())

    def test_customer_cannot_publish_or_mutate(self):
        self.client.force_login(self.buyer)
        self.assertEqual(
            self.client.post(
                reverse("vehicles:create"), self.vehicle_data()
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("vehicles:update", args=[self.vehicle.pk]), self.vehicle_data()
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("vehicles:delete", args=[self.vehicle.pk])
            ).status_code,
            403,
        )

    def test_invalid_price_and_year(self):
        for field, value in [
            ("price", "0"),
            ("price", "-1"),
            ("price", "NaN"),
            ("price", "10.001"),
            ("year", 1800),
            ("year", 9999),
            ("mileage", -1),
        ]:
            data = self.vehicle_data()
            data[field] = value
            with self.subTest(field=field, value=value):
                self.assertFalse(VehicleForm(data).is_valid())

    def test_model_validation(self):
        self.vehicle.price = Decimal("0")
        self.vehicle.year = 1800
        with self.assertRaises(ValidationError):
            self.vehicle.full_clean()

    def test_decimal_price_filters(self):
        url = reverse("vehicles:list")
        self.assertNotContains(
            self.client.get(url, {"min_price": "20000.51"}), "Corolla"
        )
        self.assertNotContains(
            self.client.get(url, {"max_price": "20000.49"}), "Corolla"
        )
        self.assertContains(
            self.client.get(url, {"min_price": "20000.50", "max_price": "20000.50"}),
            "Corolla",
        )

    def test_invalid_filters_do_not_crash_or_broaden_results(self):
        for raw in ["NaN", "Infinity", "abc", "-1", "1e999999"]:
            with self.subTest(raw=raw):
                response = self.client.get(reverse("vehicles:list"), {"min_price": raw})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(list(response.context["vehicles"]), [])

    def test_combined_brand_search_filters(self):
        response = self.client.get(
            reverse("vehicles:list"), {"brand": "toy", "q": "cor", "max_price": "20001"}
        )
        self.assertEqual(list(response.context["vehicles"]), [self.vehicle])

    def test_pagination_preserves_filters(self):
        for i in range(13):
            Vehicle.objects.create(
                brand=self.brand,
                model=f"Corolla {i}",
                year=2020,
                price=10000,
                mileage=0,
                transmission="manual",
                fuel_type="diesel",
                created_by=self.owner,
            )
        response = self.client.get(
            reverse("vehicles:list"), {"q": "Corolla", "brand": "Toyota", "page": 1}
        )
        self.assertEqual(len(response.context["vehicles"]), 12)
        self.assertContains(response, "q=Corolla&amp;brand=Toyota&amp;page=2")
        self.assertEqual(
            self.client.get(reverse("vehicles:list"), {"page": 999}).status_code, 404
        )

    def test_inactive_visibility(self):
        self.vehicle.is_active = False
        self.vehicle.save()
        self.assertNotContains(self.client.get(reverse("vehicles:list")), "Corolla")
        url = reverse("vehicles:detail", args=[self.vehicle.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_sold_cannot_be_edited_or_relisted(self):
        self.vehicle.sold = True
        self.vehicle.is_active = False
        self.vehicle.save()
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(
                reverse("vehicles:update", args=[self.vehicle.pk]), self.vehicle_data()
            ).status_code,
            404,
        )

    def test_csrf_is_required_for_publish(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(
            client.post(reverse("vehicles:create"), self.vehicle_data()).status_code,
            403,
        )

    def test_invalid_and_valid_image_upload(self):
        fake = SimpleUploadedFile("bad.jpg", b"not an image", content_type="image/jpeg")
        self.assertFalse(
            VehicleForm(self.vehicle_data(), {"main_image": fake}).is_valid()
        )
        stream = BytesIO()
        Image.new("RGB", (2, 2)).save(stream, format="PNG")
        real = SimpleUploadedFile(
            "car.png", stream.getvalue(), content_type="image/png"
        )
        self.assertTrue(
            VehicleForm(self.vehicle_data(), {"main_image": real}).is_valid()
        )

    def test_repeat_purchase_and_self_purchase_rejected(self):
        with self.assertRaises(ValueError):
            self.vehicle.mark_as_sold(self.owner)
        self.vehicle.mark_as_sold(self.buyer)
        with self.assertRaises(ValueError):
            self.vehicle.mark_as_sold(self.other)
        self.assertEqual(self.vehicle.sales.filter(status="completed").count(), 1)

    def test_missing_vehicle_returns_404(self):
        self.assertEqual(
            self.client.get(reverse("vehicles:detail", args=[999999])).status_code, 404
        )

    def test_uploaded_main_image_saved(self):
        from django.test import override_settings
        from django.core.files.storage import default_storage

        self.client.force_login(self.owner)
        stream = BytesIO()
        Image.new("RGB", (2, 2)).save(stream, format="PNG")
        data = self.vehicle_data()
        data["main_image"] = SimpleUploadedFile(
            "upload.png", stream.getvalue(), content_type="image/png"
        )
        self.assertEqual(
            self.client.post(reverse("vehicles:create"), data).status_code, 302
        )
        vehicle = Vehicle.objects.get(model="Camry")
        self.assertTrue(default_storage.exists(vehicle.main_image.name))
        self.assertContains(
            self.client.get(reverse("vehicles:detail", args=[vehicle.pk])),
            vehicle.main_image.url,
        )

    def test_oversize_image_rejected(self):
        from django.test import override_settings

        stream = BytesIO()
        Image.new("RGB", (2, 2)).save(stream, format="PNG")
        real = SimpleUploadedFile(
            "large.png", stream.getvalue(), content_type="image/png"
        )
        with override_settings(MAX_IMAGE_UPLOAD_BYTES=10):
            form = VehicleForm(self.vehicle_data(), {"main_image": real})
            self.assertFalse(form.is_valid())
            self.assertIn("main_image", form.errors)

    def test_gallery_images_visible(self):
        from .models import VehicleImage

        VehicleImage.objects.create(vehicle=self.vehicle, image="vehicles/gallery.png")
        response = self.client.get(reverse("vehicles:detail", args=[self.vehicle.pk]))
        self.assertContains(response, "/media/vehicles/gallery.png")

    def test_existing_image_preserved_without_reupload(self):
        self.vehicle.main_image = "vehicles/legacy.png"
        self.vehicle.save()
        self.client.force_login(self.owner)
        self.assertEqual(
            self.client.post(
                reverse("vehicles:update", args=[self.vehicle.pk]), self.vehicle_data()
            ).status_code,
            302,
        )
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.main_image.name, "vehicles/legacy.png")

    def test_reserved_price_edit_rejected_and_sold_withdrawal_blocked(self):
        self.vehicle.reserved = True
        self.vehicle.reserved_by = self.buyer
        self.vehicle.save()
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("vehicles:update", args=[self.vehicle.pk]), self.vehicle_data()
        )
        self.assertEqual(response.status_code, 200)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.price, Decimal("20000.50"))
        self.vehicle.sold = True
        self.vehicle.is_active = False
        self.vehicle.save()
        self.assertEqual(
            self.client.post(
                reverse("vehicles:delete", args=[self.vehicle.pk])
            ).status_code,
            302,
        )
        self.vehicle.refresh_from_db()
        self.assertTrue(self.vehicle.sold)

    def test_catalog_queries_do_not_grow_per_vehicle(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as initial:
            self.assertEqual(self.client.get(reverse("vehicles:list")).status_code, 200)
        for i in range(10):
            Vehicle.objects.create(
                brand=self.brand,
                model=f"Additional {i}",
                year=2020,
                price=100,
                mileage=0,
                transmission="manual",
                fuel_type="diesel",
                created_by=self.owner,
            )
        with CaptureQueriesContext(connection) as expanded:
            self.assertEqual(self.client.get(reverse("vehicles:list")).status_code, 200)
        self.assertLessEqual(len(expanded), len(initial) + 1)

    def test_native_admin_uses_transactional_vehicle_editor(self):
        self.client.force_login(self.superuser)
        response = self.client.get(
            reverse("admin:vehicles_vehicle_change", args=[self.vehicle.pk])
        )
        self.assertRedirects(
            response, reverse("vehicles:update", args=[self.vehicle.pk])
        )
        response = self.client.get(
            reverse("admin:vehicles_vehicle_delete", args=[self.vehicle.pk])
        )
        self.assertRedirects(
            response, reverse("vehicles:delete", args=[self.vehicle.pk])
        )
        self.assertRedirects(
            self.client.get(reverse("admin:vehicles_vehicle_add")),
            reverse("vehicles:create"),
        )
