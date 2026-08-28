from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.test import TestCase
from django.views.generic import View

from .mixins import (AdminRequiredMixin, OwnerOrAdminRequiredMixin,
                     SellerRequiredMixin)

User = get_user_model()


class MockView(View):
    """Vista mock para probar mixins."""

    def get_object(self):
        return None


class SellerRequiredMixinTest(TestCase):
    """Pruebas para SellerRequiredMixin."""

    def setUp(self):
        self.seller = User.objects.create_user(
            username="seller",
            email="seller@test.com",
            password="testpass123",
            role="seller",
        )
        self.customer = User.objects.create_user(
            username="customer",
            email="customer@test.com",
            password="testpass123",
            role="customer",
        )
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role="admin",
        )

    def test_seller_required_allowed(self):
        """Verifica que comerciantes y administradores pasen la prueba."""
        mixin = SellerRequiredMixin()
        request = HttpRequest()

        request.user = self.seller
        mixin.request = request
        self.assertTrue(mixin.test_func())

        request.user = self.admin
        mixin.request = request
        self.assertTrue(mixin.test_func())

    def test_seller_required_denied(self):
        """Verifica que clientes no pasen la prueba."""
        mixin = SellerRequiredMixin()
        request = HttpRequest()
        request.user = self.customer
        mixin.request = request
        self.assertFalse(mixin.test_func())

    def test_seller_required_unauthenticated(self):
        """Verifica que usuarios no autenticados no pasen la prueba."""
        mixin = SellerRequiredMixin()
        request = HttpRequest()
        request.user = None
        mixin.request = request
        self.assertFalse(mixin.test_func())


class AdminRequiredMixinTest(TestCase):
    """Pruebas para AdminRequiredMixin."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role="admin",
        )
        self.seller = User.objects.create_user(
            username="seller",
            email="seller@test.com",
            password="testpass123",
            role="seller",
        )

    def test_admin_required_allowed(self):
        """Verifica que los administradores pasen la prueba."""
        mixin = AdminRequiredMixin()
        request = HttpRequest()
        request.user = self.admin
        mixin.request = request
        self.assertTrue(mixin.test_func())

    def test_admin_required_denied(self):
        """Verifica que comerciantes NO pasen la prueba."""
        mixin = AdminRequiredMixin()
        request = HttpRequest()
        request.user = self.seller
        mixin.request = request
        self.assertFalse(mixin.test_func())


class OwnerOrAdminRequiredMixinTest(TestCase):
    """Pruebas para OwnerOrAdminRequiredMixin."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="testpass123",
            role="admin",
        )
        self.owner = User.objects.create_user(
            username="owner",
            email="owner@test.com",
            password="testpass123",
            role="seller",
        )
        self.other = User.objects.create_user(
            username="other",
            email="other@test.com",
            password="testpass123",
            role="seller",
        )

    class MockObject:
        def __init__(self, created_by):
            self.created_by = created_by

    def test_owner_allowed(self):
        """Verifica que el propietario tenga acceso."""
        obj = self.MockObject(self.owner)
        mixin = OwnerOrAdminRequiredMixin()
        request = HttpRequest()
        request.user = self.owner
        mixin.request = request
        mixin.get_object = lambda: obj
        self.assertTrue(mixin.test_func())

    def test_admin_allowed(self):
        """Verifica que el administrador tenga acceso."""
        obj = self.MockObject(self.owner)
        mixin = OwnerOrAdminRequiredMixin()
        request = HttpRequest()
        request.user = self.admin
        mixin.request = request
        mixin.get_object = lambda: obj
        self.assertTrue(mixin.test_func())

    def test_other_denied(self):
        """Verifica que otro usuario no tenga acceso."""
        obj = self.MockObject(self.owner)
        mixin = OwnerOrAdminRequiredMixin()
        request = HttpRequest()
        request.user = self.other
        mixin.request = request
        mixin.get_object = lambda: obj
        self.assertFalse(mixin.test_func())

    def test_no_object_denied(self):
        """Verifica que si no hay objeto, se deniegue el acceso."""
        mixin = OwnerOrAdminRequiredMixin()
        request = HttpRequest()
        request.user = self.owner
        mixin.request = request
        mixin.get_object = lambda: None
        self.assertFalse(mixin.test_func())
