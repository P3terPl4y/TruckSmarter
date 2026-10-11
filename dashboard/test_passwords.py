"""Password administration enforces the same account boundaries as editing."""

from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse, NoReverseMatch

from core.testing import MarketplaceTestCase

User = get_user_model()


class DashboardPasswordTests(MarketplaceTestCase):
    password = "ChangedSecurePass456!"

    def url(self, user=None):
        return reverse("dashboard:user_password", args=[(user or self.buyer).pk])

    def data(self, **overrides):
        return {
            "new_password1": self.password,
            "new_password2": self.password,
            **overrides,
        }

    def test_anonymous_and_non_admin_cannot_get_or_post(self):
        for actor in [None, self.owner, self.buyer]:
            self.client.logout()
            if actor:
                self.client.force_login(actor)
            expected = 302 if actor is None else 403
            with self.subTest(actor=actor):
                self.assertEqual(self.client.get(self.url()).status_code, expected)
                self.assertEqual(
                    self.client.post(self.url(), self.data()).status_code, expected
                )
        self.buyer.refresh_from_db()
        self.assertTrue(self.buyer.check_password("SecurePass123!"))

    def test_get_displays_confirmation_and_does_not_change_password(self):
        original = self.buyer.password
        self.client.force_login(self.admin)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="new_password1"')
        self.assertContains(response, 'name="new_password2"')
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertIn("no-store", response["Cache-Control"])
        self.buyer.refresh_from_db()
        self.assertEqual(self.buyer.password, original)

    def test_business_admin_changes_regular_password_without_affecting_role(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            self.url(), self.data(is_superuser=True, role="admin")
        )
        self.assertRedirects(response, reverse("dashboard:user_list"))
        self.buyer.refresh_from_db()
        self.assertTrue(self.buyer.check_password(self.password))
        self.assertFalse(self.buyer.check_password("SecurePass123!"))
        self.assertNotEqual(self.buyer.password, self.password)
        self.assertEqual(self.buyer.role, "customer")
        self.assertFalse(self.buyer.is_superuser)
        self.assertFalse(self.buyer.is_staff)
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)

    def test_mismatch_weak_and_missing_passwords_leave_hash_unchanged(self):
        self.client.force_login(self.admin)
        original = self.buyer.password
        for data in [
            self.data(new_password2="DifferentPass789!"),
            self.data(new_password1="12345678", new_password2="12345678"),
            {},
        ]:
            with self.subTest(data=data):
                response = self.client.post(self.url(), data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.buyer.refresh_from_db()
                self.assertEqual(self.buyer.password, original)
                self.assertNotContains(response, f'value="{self.password}"')

    def test_business_admin_cannot_change_staff_or_superuser(self):
        self.other.is_staff = True
        self.other.save(update_fields=["is_staff"])
        self.client.force_login(self.admin)
        for target in [self.other, self.superuser]:
            with self.subTest(target=target):
                self.assertEqual(self.client.get(self.url(target)).status_code, 404)
                self.assertEqual(
                    self.client.post(self.url(target), self.data()).status_code, 404
                )
                target.refresh_from_db()
                self.assertTrue(target.check_password("SecurePass123!"))

    def test_superuser_can_change_privileged_user(self):
        self.client.force_login(self.superuser)
        self.admin.is_staff = True
        self.admin.save(update_fields=["is_staff"])
        self.assertEqual(
            self.client.post(self.url(self.admin), self.data()).status_code, 302
        )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password(self.password))
        self.assertTrue(self.admin.is_staff)

    def test_changing_own_password_preserves_current_admin_session(self):
        self.client.force_login(self.superuser)
        old_key = self.client.session.session_key
        response = self.client.post(self.url(self.superuser), self.data())
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(self.client.session.session_key, old_key)
        self.assertEqual(self.client.get(reverse("dashboard:home")).status_code, 200)
        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.check_password(self.password))

    def test_password_change_invalidates_target_session_and_jwt(self):
        target_client = Client()
        target_client.force_login(self.buyer)
        token = target_client.post(reverse("users:api_token")).json()["access_token"]
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(self.url(), self.data()).status_code, 302)
        self.assertEqual(target_client.get(reverse("users:profile")).status_code, 302)
        self.assertEqual(
            Client()
            .get(reverse("users:api_me"), HTTP_AUTHORIZATION=f"Bearer {token}")
            .status_code,
            401,
        )

    def test_csrf_is_required_for_password_change(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(self.url(), self.data()).status_code, 403)
        self.buyer.refresh_from_db()
        self.assertTrue(self.buyer.check_password("SecurePass123!"))

    def test_password_links_visible_only_for_manageable_users(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:user_list"))
        self.assertContains(response, self.url(self.buyer))
        self.assertNotContains(response, self.url(self.superuser))
        response = self.client.get(
            reverse("dashboard:user_update", args=[self.buyer.pk])
        )
        self.assertContains(response, self.url(self.buyer))
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("dashboard:user_list"))
        self.assertContains(response, self.url(self.superuser))

    def test_missing_user_returns_404(self):
        self.client.force_login(self.admin)
        url = reverse("dashboard:user_password", args=[9999999])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, self.data()).status_code, 404)

    def test_users_pages_survive_old_worker_without_password_route(self):
        self.client.force_login(self.superuser)

        def old_reverse(name, *args, **kwargs):
            if name == "dashboard:user_password":
                raise NoReverseMatch("Old worker has not loaded the new route")
            return reverse(name, *args, **kwargs)

        with patch("django.urls.reverse", side_effect=old_reverse):
            for url in [
                reverse("dashboard:user_list"),
                reverse("dashboard:user_update", args=[self.buyer.pk]),
            ]:
                with self.subTest(url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertNotContains(response, self.url(self.buyer))
