from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from parser.views import landing

from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django_rest_passwordreset.views import ResetPasswordRequestToken, ResetPasswordConfirm, ResetPasswordValidateToken
from drf_spectacular.utils import extend_schema_view, extend_schema

# Tradução customizada para erro de e-mail não encontrado
class CustomResetPasswordRequestToken(ResetPasswordRequestToken):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 400 and 'email' in response.data:
            if "We couldn't find an account associated with that email" in str(response.data['email']):
                response.data['email'] = ["Não encontramos uma conta associada a este e-mail. Verifique se digitou corretamente."]
        return response

admin.site.index_title = "Pré-IFMA"  

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/auth/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('api/', include('exams.urls')),
    path('api/', include('game.urls')),
    path('parser/', include('parser.urls')),
    path('', landing, name='landing'),
]


extend_schema_view(
    post=extend_schema(summary="Solicitar código de recuperação de senha", tags=["auth"])
)(ResetPasswordRequestToken)

extend_schema_view(
    post=extend_schema(summary="Confirmar nova senha usando o token", tags=["auth"])
)(ResetPasswordConfirm)

extend_schema_view(
    post=extend_schema(summary="Validar se o token recebido é válido", tags=["auth"])
)(ResetPasswordValidateToken)


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
