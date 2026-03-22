from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    path('', include('apps.kiosk.urls', namespace='kiosk')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
