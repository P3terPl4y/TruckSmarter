from django.contrib.auth.mixins import UserPassesTestMixin

from .permissions import is_admin, is_seller


class SellerRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_seller(self.request.user)


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return is_admin(self.request.user)


class OwnerOrAdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        obj = self.get_object() if hasattr(self, "get_object") else None
        return is_admin(user) or bool(obj and getattr(obj, "created_by", None) == user)
