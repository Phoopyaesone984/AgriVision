from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from landing.views import set_language
from marketPrice import views  # Add this import

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('landing.urls')),
    path('community/', include('community.urls')),
    path('stock/', include('stock.urls')),
    path('farms/', include('farms.urls')),
    path('crops/', include('crops.urls')), 
    path('weather/', include('weather.urls')), 
    path('auth/', include('authentication.urls')),
    path('market/', include('marketPrice.urls')), 
    path('i18n/', include('django.conf.urls.i18n')),
    path('set-language/', set_language, name='set_language'),
    
    # Direct chat API route (so frontend works without changing URL)
    path('api/chat/', views.chat_api, name='chat_api_direct'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)