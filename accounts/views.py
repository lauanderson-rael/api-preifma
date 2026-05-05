from datetime import date

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from game.models import Answer, StudySession
from .serializers import RegisterSerializer, UserSerializer
from game.services import update_streak
from .level_utils import level_progress

User = get_user_model()


class RegisterView(APIView):
    """POST /api/auth/register/ — cria conta e retorna tokens JWT."""
    permission_classes = [AllowAny]

    def post(self, request):
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
    """
    POST /api/auth/login/ — autentica usuário, atualiza streak, retorna tokens.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)
        if not user:
            return Response(
                {'detail': 'E-mail ou senha inválidos.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Atualiza streak ao fazer login
        update_streak(user)

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class MeView(APIView):
    """GET /api/auth/me/ — dados básicos do usuário logado."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/users/profile/ → perfil completo
    PATCH /api/users/profile/ → atualiza name, username
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return self.request.user

    def partial_update(self, request, *args, **kwargs):
        # Só permite alterar name e username
        allowed = {k: v for k, v in request.data.items() if k in ('name', 'username')}
        serializer = self.get_serializer(request.user, data=allowed, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class StatsView(APIView):
    """GET /api/users/stats/ — xp, nível (curva progressiva), streak, acurácia."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
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
            'streak': user.streak,
            'last_study_date': user.last_study_date,
            'total_questions_answered': total_answered,
            'total_correct': total_correct,
            'accuracy': accuracy,
        })


class StreakView(APIView):
    """GET /api/streak/ — streak atual e data do último estudo."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'current_streak': request.user.streak,
            'last_study_date': request.user.last_study_date,
        })
