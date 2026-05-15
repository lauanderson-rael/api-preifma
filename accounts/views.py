from datetime import date

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from drf_spectacular.utils import extend_schema, extend_schema_view
from game.models import Answer
from .serializers import RegisterSerializer, UserSerializer, LoginSerializer
from game.services import get_or_create_daily_missions
from .level_utils import level_progress

User = get_user_model()

class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @extend_schema(summary="Registrar novo usuário")
    def post(self, request):
        """POST /api/auth/register/ — cria conta e retorna tokens JWT."""
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(summary="Login de usuário")
    def post(self, request):
        """POST /api/auth/login/ — autentica usuário, atualiza streak, retorna tokens."""
        from django.contrib.auth import authenticate
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)
        if not user:
            return Response(
                {'detail': 'E-mail ou senha inválidos.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        # Login bem sucedido

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })

@extend_schema(summary="Refresh token")
class CustomTokenRefreshView(TokenRefreshView):
    """POST /api/auth/refresh/ — Recebe um refresh token e retorna um novo access token."""
    pass


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(summary="Dados do usuário logado")
    def get(self, request):
        """GET /api/auth/me/ — dados básicos do usuário logado."""
        return Response(UserSerializer(request.user).data)


@extend_schema_view(
    get=extend_schema(summary="Exibir perfil completo"),
    patch=extend_schema(summary="Atualizar nome/username"),
)
class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get(self, request):
        """GET /api/users/profile/ — perfil completo"""
        return Response(UserSerializer(request.user).data)

    def patch(self, request, *args, **kwargs):
        """PATCH /api/users/profile/ — atualiza name, username"""
        allowed = {k: v for k, v in request.data.items() if k in ('name', 'username')}
        serializer = self.get_serializer(request.user, data=allowed, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class StatsView(APIView):
    permission_classes = [IsAuthenticated]
    @extend_schema(summary="Estatísticas de desempenho")
    def get(self, request):
        """GET /api/users/stats/ — xp, nível (curva progressiva), streak, acurácia."""
        user = request.user
        total_answered = Answer.objects.filter(user=user).count()
        total_correct = Answer.objects.filter(user=user, is_correct=True).count()
        accuracy = round(total_correct / total_answered * 100, 2) if total_answered else 0.0
        lp = level_progress(user.xp)

        return Response({
            'xp': user.xp,
            'level': lp['level'],
            'level_xp_cost': lp['level_xp_cost'],
            'xp_current_level': lp['xp_current_level'],
            'xp_to_next_level': lp['xp_to_next_level'],
            'progress_pct': lp['progress_pct'],
            'total_questions_answered': total_answered,
            'total_correct': total_correct,
            'accuracy': accuracy,
        })


@extend_schema(summary="Renovar token de acesso")
class CustomTokenRefreshView(TokenRefreshView):
    """POST /api/auth/refresh/ — Recebe um refresh token e retorna um novo access token."""
    pass
