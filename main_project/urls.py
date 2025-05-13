from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('forecast.api.urls')),  # Forecast API endpoints - first
    path('api/', include('main_app.api.urls')),  # Main API endpoints
    path('', include('forecast.urls')),  # Forecast web views - first
    path('', include('main_app.urls')),  # Main app URLs
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
