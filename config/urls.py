from django.contrib import admin
from django.urls import path, include
from .settings import DEBUG,MEDIA_URL, MEDIA_ROOT
from django.conf.urls.static import static
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('vehicles.urls')),
    path('users/', include('users.urls')),
    path('sales/', include('sales.urls')),
]
if DEBUG:
    urlpatterns += static(MEDIA_URL, document_root=MEDIA_ROOT)
