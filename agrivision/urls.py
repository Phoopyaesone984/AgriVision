# agrivision/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from landing.views import set_language  # Import the set_language view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('landing.urls')),
    path('auth/', include('authentication.urls')),  
    path('i18n/', include('django.conf.urls.i18n')),
    path('set-language/', set_language, name='set_language'),  # Add this line
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)