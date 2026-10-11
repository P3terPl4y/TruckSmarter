"""Administrative forms live in users/vehicles and are shared by both panels."""

from users.forms import UserAdminCreationForm, UserAdminForm
from vehicles.forms import BrandForm

__all__ = ["UserAdminCreationForm", "UserAdminForm", "BrandForm"]
