from django.db import transaction
from django.db.models import Sum, Q
from django.shortcuts import get_object_or_404
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from exams.models import Alternative, Question
from .models import (
    Answer, Mission, StudySession,
    SubjectProgress, UserMission, UserAIDailyUsage
)
from datetime import date
from .serializers import (
    AnswerCreateSerializer,
    AnswerSerializer,
    SessionFinishSerializer,
    SessionStartSerializer,
    StudySessionListSerializer,
    StudySessionSerializer,
    SubjectProgressSerializer,
    UserMissionSerializer,
    DashboardSerializer,
)
from .services import update_streak, xp_per_correct
from drf_spectacular.utils import extend_schema, extend_schema_view

# Sessions

class SessionStartView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SessionStartSerializer

    @extend_schema(summary="Iniciar nova sessão")
    def post(self, request): 
        """POST /api/sessions/start/ — cria uma nova sessão de estudo."""
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
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Detalhes da sessão")
    def get(self, request, pk):
        """GET /api/sessions/{id}/ — retorna detalhes e estatísticas de uma sessão específica."""
        session = get_object_or_404(
            StudySession.objects.prefetch_related('answers'),
            pk=pk,
            user=request.user,
        )
        return Response(StudySessionSerializer(session).data)


class SessionAnswerView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AnswerCreateSerializer

    @extend_schema(summary="Listar respostas da sessão")
    def get(self, request, pk):
        """GET /api/sessions/{id}/answers/ — Lista todas as respostas dadas nesta sessão."""
        session = get_object_or_404(StudySession, pk=pk, user=request.user)
        answers = session.answers.select_related('question', 'selected_alternative').all()
        return Response(AnswerSerializer(answers, many=True).data)

    @extend_schema(summary="Registrar resposta")
    def post(self, request, pk):
        """POST /api/sessions/{id}/answers/ — Registra a resposta do aluno para uma questão."""
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
    permission_classes = [IsAuthenticated]
    serializer_class = SessionFinishSerializer

    @extend_schema(summary="Finalizar sessão")
    def post(self, request, pk):
        """POST /api/sessions/{id}/finish/ — finaliza sessão, calcula XP e atualiza progresso."""
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
            })



@extend_schema(summary="Histórico de sessões", description="GET /api/sessions/history/ — histórico de sessões do usuário.")  
class SessionHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StudySessionListSerializer

    def get_queryset(self):
        return StudySession.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


# Progress
@extend_schema(summary="Progresso por matéria", description="GET /api/progress/subjects/ — progresso por matéria.")
class SubjectProgressView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SubjectProgressSerializer

    def get_queryset(self): 
        return SubjectProgress.objects.filter(user=self.request.user) 


# Missions
class DailyMissionsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Listar missões diárias")
    def get(self, request):
        """GET /api/missions/daily/ — missões do dia com progresso."""
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
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Reivindicar XP de missão")
    def post(self, request, pk):
        """POST /api/missions/{id}/claim/ — reivindica XP de missão completada (idempotente)."""
        user = request.user
        
        # Busca o registro da missão diária pelo ID (o frontend envia o ID do UserMission)
        um = get_object_or_404(UserMission, pk=pk, user=user)

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
        
        # Lógica de Recompensa Especial (Bônus de IA temporário)
        bonus_msg = ""
        if um.mission.special_reward == "AI_LIMIT":
            from .models import UserAIDailyUsage
            usage_today, _ = UserAIDailyUsage.objects.get_or_create(
                user=request.user, 
                date=um.date
            )
            usage_today.bonus_limit += 2
            usage_today.save()
            bonus_msg = " Seu limite de HOJE aumentou em +2!"

        request.user.save(update_fields=['xp'])
        um.xp_claimed = True
        um.save(update_fields=['xp_claimed'])
        
        return Response({
            'xp_gained': xp, 
            'new_total_xp': request.user.xp,
            'detail': f"Missão concluída!{bonus_msg}"
        })


# Dashboard
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DashboardSerializer

    @extend_schema(summary="Dashboard inicial")
    def get(self, request):
        """GET /api/dashboard/ — dados agregados para a tela inicial."""
        from datetime import date
        today = date.today()
        user = request.user

        # Garante que existam 5 missões aleatórias para hoje
        from datetime import date
        import random as _random_missions
        today = date.today()
        
        user_daily_missions = UserMission.objects.filter(user=user, date=today)
        
        if not user_daily_missions.exists():
            all_available_missions = list(Mission.objects.all())
            if all_available_missions:
                # Sorteia até 5 missões
                selected_missions = _random_missions.sample(
                    all_available_missions, 
                    min(5, len(all_available_missions))
                )
                for mission in selected_missions:
                    UserMission.objects.create(
                        user=user,
                        mission=mission,
                        date=today,
                        progress=0,
                        completed=False
                    )
        
        daily_missions = UserMission.objects.filter(
            user=user, date=today
        ).select_related('mission') 
       
        recent_sessions = StudySession.objects.filter(
            user=user, finished=True
        ).order_by('-created_at')[:3]

       
        subject_progress = SubjectProgress.objects.filter(user=user)
        # Informações de cota de IA
        today = date.today()
        ai_usage_obj, _ = UserAIDailyUsage.objects.get_or_create(user=user, date=today)

        return Response({
            'streak': user.streak,
            'xp': user.xp,
            'last_study_date': user.last_study_date,
            'daily_missions': UserMissionSerializer(daily_missions, many=True).data,
            'recent_sessions': StudySessionListSerializer(recent_sessions, many=True).data,
            'subject_progress': SubjectProgressSerializer(subject_progress, many=True).data,
            'ai_usage': {
                'used': ai_usage_obj.count,
                'limit': user.ai_daily_limit + ai_usage_obj.bonus_limit,
                'remaining': max(0, (user.ai_daily_limit + ai_usage_obj.bonus_limit) - ai_usage_obj.count)
            }
        })


class QuestionExplanationView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Explicação por IA")
    def get(self, request, question_id):
        """GET /api/game/questions/{question_id}/explain/ — obtém explicação detalhada via IA."""
        from .services import get_or_generate_explanation
        result = get_or_generate_explanation(request.user, question_id)
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)
