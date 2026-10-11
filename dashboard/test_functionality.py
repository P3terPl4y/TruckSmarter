from django.contrib.auth import get_user_model
from django.urls import reverse
from core.testing import MarketplaceTestCase
from vehicles.models import Brand, Vehicle

User = get_user_model()


class DashboardFunctionalTests(MarketplaceTestCase):
    def test_all_dashboard_pages_permissions(self):
        for name, args in [
            ("home", []),
            ("user_list", []),
            ("user_create", []),
            ("user_update", [self.buyer.pk]),
            ("user_delete", [self.other.pk]),
            ("brand_list", []),
            ("brand_create", []),
            ("brand_update", [self.brand.pk]),
            ("brand_delete", [self.brand.pk]),
            ("offer_list", []),
        ]:
            with self.subTest(name=name):
                self.client.logout()
                url = reverse("dashboard:" + name, args=args)
                self.assertEqual(self.client.get(url).status_code, 302)
                self.client.force_login(self.owner)
                self.assertEqual(self.client.get(url).status_code, 403)
                self.client.force_login(self.admin)
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_create_user_requires_secure_password(self):
        self.client.force_login(self.admin)
        data = {
            "username": "managed",
            "email": "managed@example.com",
            "role": "seller",
            "is_active": True,
        }
        self.assertEqual(
            self.client.post(reverse("dashboard:user_create"), data).status_code, 200
        )
        self.assertFalse(User.objects.filter(username="managed").exists())
        data.update(password1="SecureManaged123!", password2="SecureManaged123!")
        self.assertEqual(
            self.client.post(reverse("dashboard:user_create"), data).status_code, 302
        )
        user = User.objects.get(username="managed")
        self.assertTrue(user.check_password("SecureManaged123!"))
        self.assertTrue(hasattr(user, "profile"))

    def test_business_admin_cannot_escalate_native_privileges(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("dashboard:user_update", args=[self.buyer.pk]),
            {
                "username": self.buyer.username,
                "email": self.buyer.email,
                "role": "seller",
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.buyer.refresh_from_db()
        self.assertFalse(self.buyer.is_superuser)
        self.assertFalse(self.buyer.is_staff)
        self.assertEqual(
            self.client.get(
                reverse("dashboard:user_update", args=[self.superuser.pk])
            ).status_code,
            404,
        )

    def test_superuser_can_manage_native_privileges(self):
        self.client.force_login(self.superuser)
        response = self.client.post(
            reverse("dashboard:user_update", args=[self.buyer.pk]),
            {
                "username": self.buyer.username,
                "email": self.buyer.email,
                "role": "admin",
                "is_active": True,
                "is_staff": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.buyer.refresh_from_db()
        self.assertTrue(self.buyer.is_staff)

    def test_cannot_delete_own_account(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(
                reverse("dashboard:user_delete", args=[self.admin.pk])
            ).status_code,
            403,
        )
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_brand_deletion_preserves_vehicles_and_history(self):
        sale = self.offer()
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("dashboard:brand_delete", args=[self.brand.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Brand.objects.filter(pk=self.brand.pk).exists())
        self.assertTrue(Vehicle.objects.filter(pk=self.vehicle.pk).exists())
        sale.refresh_from_db()

    def test_user_deletion_preserves_history(self):
        self.offer()
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(
                reverse("dashboard:user_delete", args=[self.buyer.pk])
            ).status_code,
            302,
        )
        self.assertTrue(User.objects.filter(pk=self.buyer.pk).exists())

    def test_unlinked_user_and_brand_can_be_deleted(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(
                reverse("dashboard:user_delete", args=[self.other.pk])
            ).status_code,
            302,
        )
        self.assertFalse(User.objects.filter(pk=self.other.pk).exists())
        brand = Brand.objects.create(name="Unused")
        self.assertEqual(
            self.client.post(
                reverse("dashboard:brand_delete", args=[brand.pk])
            ).status_code,
            302,
        )
        self.assertFalse(Brand.objects.filter(pk=brand.pk).exists())

    def test_brand_crud_and_duplicate_validation(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post(
                reverse("dashboard:brand_create"), {"name": "Honda"}
            ).status_code,
            302,
        )
        brand = Brand.objects.get(name="Honda")
        self.assertEqual(
            self.client.post(
                reverse("dashboard:brand_create"), {"name": "Honda"}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.post(
                reverse("dashboard:brand_update", args=[brand.pk]), {"name": "Mazda"}
            ).status_code,
            302,
        )
        brand.refresh_from_db()
        self.assertEqual(brand.name, "Mazda")

    def test_offer_list_has_working_post_actions(self):
        sale = self.offer()
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:offer_list"))
        self.assertContains(response, reverse("sales:accept_offer", args=[sale.pk]))
        self.assertContains(response, reverse("sales:reject_offer", args=[sale.pk]))
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, 'method="post"')

    def test_lists_paginated(self):
        Brand.objects.bulk_create([Brand(name=f"Brand {i}") for i in range(30)])
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:brand_list"))
        self.assertEqual(len(response.context["brands"]), 25)
        self.assertContains(response, "page=2")
