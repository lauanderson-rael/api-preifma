from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from parser.views import landing

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

# admin.site.site_header = "Nome do Painel (Cabeçalho)"
# admin.site.site_title = "Nome do Site (Título da aba)"
admin.site.index_title = "Pré-IFMA" 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/', include('exams.urls')),
    path('api/', include('game.urls')),
    path('parser/', include('parser.urls')),
    path('', landing, name='landing'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
