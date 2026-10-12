from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from core.views import catalog_image

urlpatterns = [
    path("media/<path:image_path>", catalog_image, name="catalog_image"),
    path("admin/", admin.site.urls),
    path("", include("vehicles.urls")),
    path("users/", include("users.urls")),
    path("sales/", include("sales.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("analytics/", include("analytics.urls")),
]

# Servir archivos estáticos y multimedia en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
