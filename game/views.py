from django.db import transaction
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from exams.models import Alternative, Question
from .models import (
    Achievement, Answer, Mission, StudySession,
    SubjectProgress, UserAchievement, UserMission,
)
from .serializers import (
    AchievementSerializer,
    AnswerCreateSerializer,
    AnswerSerializer,
    SessionFinishSerializer,
    SessionStartSerializer,
    StudySessionListSerializer,
    StudySessionSerializer,
    SubjectProgressSerializer,
    UserAchievementSerializer,
    UserMissionSerializer,
)
from .services import update_streak, xp_per_correct

# Sessions

class SessionStartView(APIView):
    """POST /api/sessions/start/ — cria uma nova sessão."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SessionStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session = StudySession.objects.create(
            user=request.user,
            type=data['type'],
            total_questions=len(data['question_ids']),
        )
        return Response(StudySessionSerializer(session).data, status=status.HTTP_201_CREATED)


class SessionDetailView(APIView):
    """GET /api/sessions/{id}/ — detalhe da sessão."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        session = get_object_or_404(
            StudySession.objects.prefetch_related('answers'),
            pk=pk,
            user=request.user,
        )
        return Response(StudySessionSerializer(session).data)


class SessionAnswerView(APIView):
    """
    POST /api/sessions/{id}/answers/ — registra resposta
    GET  /api/sessions/{id}/answers/ — lista respostas
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        session = get_object_or_404(StudySession, pk=pk, user=request.user)
        answers = session.answers.select_related('question', 'selected_alternative').all()
        return Response(AnswerSerializer(answers, many=True).data)

    def post(self, request, pk):
        session = get_object_or_404(StudySession, pk=pk, user=request.user)
        if session.finished:
            return Response(
                {'detail': 'Esta sessão já foi finalizada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AnswerCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        question = get_object_or_404(Question, pk=data['question_id'])
        alternative = get_object_or_404(Alternative, pk=data['alternative_id'], question=question)

        # Snapshot do gabarito no momento da resposta
        correct_alt = question.alternatives.filter(is_correct=True).first()
        correct_letter = correct_alt.letter if correct_alt else ''
        is_correct = alternative.is_correct

        xp_partial = xp_per_correct(session.type) if is_correct else 0

        Answer.objects.create(
            user=request.user,
            session=session,
            question=question,
            selected_alternative=alternative,
            correct_letter=correct_letter,
            is_correct=is_correct,
            response_time=data['response_time'],
        )

        return Response({
            'is_correct': is_correct,
            'correct_letter': correct_letter,
            'xp_partial': xp_partial,
        }, status=status.HTTP_201_CREATED)


class SessionFinishView(APIView):
    """POST /api/sessions/{id}/finish/ — finaliza sessão e calcula resultado."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(StudySession, pk=pk, user=request.user)
        if session.finished:
            return Response(
                {'detail': 'Esta sessão já foi finalizada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = SessionFinishSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            answers = session.answers.all()
            
            if answers.filter(Q(correct_letter='') | Q(correct_letter__isnull=True)).exists():
                return Response(
                    {'detail': 'Inconsistência detectada: Algumas respostas estão sem o gabarito registrado.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            total_duration = answers.aggregate(Sum('response_time'))['response_time__sum'] or 0

            correct_count = answers.filter(is_correct=True).count()
            total = answers.count()

            xp_rate = xp_per_correct(session.type)
            xp_gained = correct_count * xp_rate
            accuracy = round((correct_count / total * 100), 2) if total else 0.0

            session.correct_answers = correct_count
            session.total_questions = total
            session.xp_gained = xp_gained
            session.duration_seconds = total_duration
            session.finished = True
            session.save()

            user = request.user
            user.xp += xp_gained
            user.save(update_fields=['xp'])
            new_streak = update_streak(user)

            for ans in answers.select_related('question'):
                subj = ans.question.subject
                sp, _ = SubjectProgress.objects.get_or_create(user=user, subject=subj)
                sp.questions_answered += 1
                if ans.is_correct:
                    sp.correct_answers += 1
                sp.save()

            # Missões do dia 
            from datetime import date
            today = date.today()
            daily_missions = UserMission.objects.filter(user=user, date=today)
            missions_updated = []
            for um in daily_missions:
                if um.completed:
                    continue
                if um.mission.goal_type == 'answer_questions':
                    um.progress = min(um.progress + total, um.mission.goal_value)
                elif um.mission.goal_type == 'correct_answers':
                    um.progress = min(um.progress + correct_count, um.mission.goal_value)
                if um.progress >= um.mission.goal_value:
                    um.completed = True
                um.save()
                missions_updated.append({
                    'id': um.mission.id,
                    'title': um.mission.title,
                    'progress': um.progress,
                    'completed': um.completed,
                })

            # ── Achievements (básico: Primeira Vitória) ──────────────────────
            achievements_unlocked = []
            already_unlocked_ids = UserAchievement.objects.filter(
                user=user
            ).values_list('achievement_id', flat=True)
            candidates = Achievement.objects.exclude(id__in=already_unlocked_ids)
            for achievement in candidates:
                unlock = False
                # Regras simples baseadas em title/goal_type podem ser expandidas
                if 'Primeira' in achievement.title and correct_count > 0:
                    unlock = True
                if unlock:
                    ua = UserAchievement.objects.create(user=user, achievement=achievement)
                    user.xp += achievement.xp_reward
                    user.save(update_fields=['xp'])
                    achievements_unlocked.append({
                        'id': achievement.id,
                        'title': achievement.title,
                        'icon': achievement.icon.url if achievement.icon else None,
                    })

        return Response({
            'session_id': session.id,
            'total_questions': total,
            'correct_answers': correct_count,
            'accuracy': accuracy,
            'duration_seconds': session.duration_seconds,
            'xp_gained': xp_gained,
            'new_total_xp': user.xp,
            'streak': new_streak,
            'missions_updated': missions_updated,
            'achievements_unlocked': achievements_unlocked,
        })


class SessionHistoryView(generics.ListAPIView):
    """GET /api/sessions/history/ — histórico de sessões do usuário."""
    permission_classes = [IsAuthenticated]
    serializer_class = StudySessionListSerializer

    def get_queryset(self):
        return StudySession.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


# Progress
class SubjectProgressView(generics.ListAPIView):
    """GET /api/progress/subjects/ — progresso por matéria."""
    permission_classes = [IsAuthenticated]
    serializer_class = SubjectProgressSerializer

    def get_queryset(self):
        return SubjectProgress.objects.filter(user=self.request.user)


# Missions
class DailyMissionsView(APIView):
    """GET /api/missions/daily/ — missões do dia com progresso."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from datetime import date
        today = date.today()
        user = request.user

        all_missions = Mission.objects.all()
        for mission in all_missions:
            UserMission.objects.get_or_create(
                user=user, mission=mission, date=today,
                defaults={'progress': 0, 'completed': False},
            )

        user_missions = (
            UserMission.objects.filter(user=user, date=today)
            .select_related('mission')
        )
        return Response(UserMissionSerializer(user_missions, many=True).data)


class MissionClaimView(APIView):
    """POST /api/missions/{id}/claim/ — reivindica XP de missão completada (idempotente)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        from datetime import date
        today = date.today()
        um = get_object_or_404(UserMission, mission_id=pk, user=request.user, date=today)

        if not um.completed:
            return Response(
                {'detail': 'Missão ainda não completada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if um.xp_claimed:
            return Response(
                {'detail': 'XP já foi reivindicado para esta missão hoje.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        xp = um.mission.xp_reward
        request.user.xp += xp
        request.user.save(update_fields=['xp'])
        um.xp_claimed = True
        um.save(update_fields=['xp_claimed'])
        return Response({'xp_gained': xp, 'new_total_xp': request.user.xp})


# Achievements
class AchievementListView(generics.ListAPIView):
    """GET /api/achievements/ — todas as conquistas do sistema."""
    permission_classes = [IsAuthenticated]
    serializer_class = AchievementSerializer
    queryset = Achievement.objects.all()


class UserAchievementListView(generics.ListAPIView):
    """GET /api/achievements/user/ — conquistas desbloqueadas pelo usuário."""
    permission_classes = [IsAuthenticated]
    serializer_class = UserAchievementSerializer

    def get_queryset(self):
        return UserAchievement.objects.filter(
            user=self.request.user
        ).select_related('achievement').order_by('-unlocked_at')


# Dashboard
class DashboardView(APIView):
    """GET /api/dashboard/ — dados agregados para a tela inicial."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from datetime import date
        today = date.today()
        user = request.user

       
        all_missions = Mission.objects.all()
        for mission in all_missions:
            UserMission.objects.get_or_create(
                user=user, mission=mission, date=today,
                defaults={'progress': 0, 'completed': False},
            )
        daily_missions = UserMission.objects.filter(
            user=user, date=today
        ).select_related('mission')

       
        recent_sessions = StudySession.objects.filter(
            user=user, finished=True
        ).order_by('-created_at')[:3]

       
        subject_progress = SubjectProgress.objects.filter(user=user)
        return Response({
            'streak': user.streak,
            'xp': user.xp,
            'last_study_date': user.last_study_date,
            'daily_missions': UserMissionSerializer(daily_missions, many=True).data,
            'recent_sessions': StudySessionListSerializer(recent_sessions, many=True).data,
            'subject_progress': SubjectProgressSerializer(subject_progress, many=True).data,
        })
