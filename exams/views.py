import random as _random

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Exam, Question
from .serializers import ExamSerializer, ExamDetailSerializer, QuestionSerializer


class ExamViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/exams/         → lista de provas
    GET /api/exams/{id}/    → detalhe da prova
    GET /api/exams/{id}/questions/ → questões da prova
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Exam.objects.all().order_by('-year', 'name')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ExamDetailSerializer
        return ExamSerializer

    @action(detail=True, methods=['get'], url_path='questions')
    def questions(self, request, pk=None):
        exam = get_object_or_404(Exam, pk=pk)
        qs = (
            exam.questions
            .prefetch_related('alternatives', 'questionattachment_set__attachment')
            .order_by('number')
        )
        serializer = QuestionSerializer(qs, many=True)
        return Response(serializer.data)


class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/questions/{id}/    → questão individual
    GET /api/questions/random/  → questões aleatórias (subject, exam_type, count)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = QuestionSerializer

    def get_queryset(self):
        return Question.objects.prefetch_related(
            'alternatives',
            'questionattachment_set__attachment',
        ).all()

    @action(detail=False, methods=['get'], url_path='random')
    def random(self, request):
        subject = request.query_params.get('subject')
        exam_type = request.query_params.get('exam_type')
        count = int(request.query_params.get('count', 10))

        qs = self.get_queryset()
        if subject:
            qs = qs.filter(subject=subject)
        if exam_type:
            qs = qs.filter(exam__type=exam_type)

        ids = list(qs.values_list('id', flat=True))
        if not ids:
            return Response([], status=status.HTTP_200_OK)

        sampled = _random.sample(ids, min(count, len(ids)))
        questions = qs.filter(id__in=sampled)
        serializer = self.get_serializer(questions, many=True)
        return Response(serializer.data)
