import random as _random
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Exam, Question
from .serializers import ExamSerializer, ExamDetailSerializer, QuestionSerializer


@extend_schema_view(
    list=extend_schema(summary="Listar provas"),
    retrieve=extend_schema(summary="Detalhes da prova"),
)
class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Exam.objects.all().order_by('-year', 'name')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ExamDetailSerializer
        return ExamSerializer
    
    def list(self, request, *args, **kwargs):
        """GET /api/exams/ — Lista todas as provas ordenadas por ano e nome."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """GET /api/exams/{id}/ — Detalhes de uma prova específica."""
        return super().retrieve(request, *args, **kwargs) 

    @extend_schema(summary="Questões da prova")
    @action(detail=True, methods=['get'], url_path='questions')
    def questions(self, request, pk=None):
        """GET /api/exams/{id}/questions/ — Retorna todas as questões de uma prova específica."""
        exam = get_object_or_404(Exam, pk=pk)
        qs = (
            exam.questions
            .prefetch_related('alternatives', 'questionattachment_set__attachment')
            .order_by('number')
        )
        serializer = QuestionSerializer(qs, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(summary="Listar questões"),
    retrieve=extend_schema(summary="Detalhes da questão"),
)
class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionSerializer

    def get_queryset(self):
        qs = Question.objects.prefetch_related(
            'alternatives',
            'questionattachment_set__attachment',
        ).all()
        
        subject = self.request.query_params.get('subject')
        exam_type = self.request.query_params.get('exam_type')
        
        if subject:
            qs = qs.filter(subject__in=subject.split(','))
        if exam_type:
            qs = qs.filter(exam__type__in=exam_type.split(','))
            
        return qs

    def list(self, request, *args, **kwargs):
        """GET /api/questions/ — Lista todas as questões com suporte a filtros (subject, exam_type)."""
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """GET /api/questions/{id}/ — Detalhes de uma questão específica (inclui alternativas)."""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary="Questões aleatórias")
    @action(detail=False, methods=['get'], url_path='random')
    def random(self, request):
        """GET /api/questions/random/ — Retorna questões aleatórias baseadas em filtros."""
        count = int(request.query_params.get('count', 10))
        qs = self.get_queryset()
        
        ids = list(qs.values_list('id', flat=True))
        if not ids:
            return Response([], status=status.HTTP_200_OK)

        sampled = _random.sample(ids, min(count, len(ids)))
        questions = self.get_queryset().filter(id__in=sampled)
        serializer = self.get_serializer(questions, many=True)
        return Response({
            "total": questions.count(),
            "results": serializer.data
        })

    @extend_schema(summary="Gerar simulado")
    @action(detail=False, methods=['get'], url_path='simulated')
    def simulated(self, request):
        """GET /api/questions/simulated/ — Gera um simulado balanceado (15 Port + 15 Mat)."""
        exam_type = request.query_params.get('exam_type', 'integrado')
        qs = self.get_queryset().filter(exam__type__in=exam_type.split(','))
        
        port_ids = list(qs.filter(subject='portugues').values_list('id', flat=True))
        mat_ids = list(qs.filter(subject='matematica').values_list('id', flat=True))
        
        sampled_port = _random.sample(port_ids, min(15, len(port_ids)))
        sampled_mat = _random.sample(mat_ids, min(15, len(mat_ids)))
        
        final_ids = sampled_port + sampled_mat
        _random.shuffle(final_ids) 
        
        questions = self.get_queryset().filter(id__in=final_ids)
        serializer = self.get_serializer(questions, many=True)
         
        # Sobrescreve o campo 'number' para ser sequencial (1 a 30) no simulado
        data = serializer.data
        for i, item in enumerate(data):
            item['number'] = i + 1

        return Response({
            "total": len(data),
            "results": data
        })
