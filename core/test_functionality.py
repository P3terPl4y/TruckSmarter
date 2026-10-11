from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from core.testing import MarketplaceTestCase
from .permissions import is_admin, is_seller, can_manage_vehicle


class PermissionFunctionalTests(MarketplaceTestCase):
    def test_anonymous_and_none_denied(self):
        for user in [None, AnonymousUser()]:
            self.assertFalse(is_admin(user))
            self.assertFalse(is_seller(user))
            self.assertFalse(can_manage_vehicle(user, self.vehicle))

    def test_inactive_users_denied_even_admin(self):
        self.admin.is_active = False
        self.assertFalse(is_admin(self.admin))
        self.assertFalse(is_seller(self.admin))
        self.assertFalse(can_manage_vehicle(self.admin, self.vehicle))

    def test_roles_and_ownership(self):
        self.assertTrue(is_admin(self.admin))
        self.assertTrue(is_admin(self.superuser))
        self.assertTrue(is_seller(self.owner))
        self.assertFalse(is_seller(self.buyer))
        self.assertTrue(can_manage_vehicle(self.owner, self.vehicle))
        self.assertFalse(can_manage_vehicle(self.other, self.vehicle))
        self.assertFalse(can_manage_vehicle(self.buyer, None))

    def test_anonymous_next_redirects_for_admin_and_owner(self):
        for url in [
            reverse("dashboard:home"),
            reverse("users:admin_list"),
            reverse("vehicles:delete", args=[self.vehicle.pk]),
        ]:
            self.assertRedirects(self.client.get(url), "/users/login/?next=" + url)
