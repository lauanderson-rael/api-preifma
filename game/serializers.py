from rest_framework import serializers
from .models import (StudySession, Answer, SubjectProgress, Mission, UserMission,)
from exams.serializers import QuestionSerializer


#  Answer
class AnswerSerializer(serializers.ModelSerializer):
    """Serializer de leitura para uma resposta já salva."""
    question_id = serializers.IntegerField(source='question.id', read_only=True)
    selected_alternative_id = serializers.IntegerField(
        source='selected_alternative.id', allow_null=True, read_only=True
    )

    class Meta:
        model = Answer
        fields = [
            'id', 'question_id', 'selected_alternative_id',
            'correct_letter', 'is_correct', 'response_time', 'created_at',
        ]


class AnswerCreateSerializer(serializers.Serializer):
    """Payload para registrar uma nova resposta."""
    question_id = serializers.IntegerField()
    alternative_id = serializers.IntegerField()
    response_time = serializers.IntegerField(min_value=0)


# Session
class StudySessionSerializer(serializers.ModelSerializer):
    accuracy = serializers.SerializerMethodField()
    answers = AnswerSerializer(many=True, read_only=True)

    def get_accuracy(self, obj):
        return obj.accuracy_percentage

    class Meta:
        model = StudySession
        fields = [
            'id', 'type', 'total_questions', 'correct_answers',
            'accuracy', 'xp_gained', 'duration_seconds', 'finished', 'created_at',
            'answers',
        ]


class StudySessionListSerializer(serializers.ModelSerializer):
    """Versão leve para listagem (sem answers)."""
    accuracy = serializers.SerializerMethodField()

    def get_accuracy(self, obj):
        return obj.accuracy_percentage

    class Meta:
        model = StudySession
        fields = [
            'id', 'type', 'total_questions', 'correct_answers',
            'accuracy', 'xp_gained', 'duration_seconds', 'finished', 'created_at',
        ]


class SessionStartSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=['quick', 'simulated', 'practice'])
    question_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1)


class SessionFinishSerializer(serializers.Serializer):
    pass


#  Progress
class SubjectProgressSerializer(serializers.ModelSerializer):
    accuracy = serializers.SerializerMethodField()

    def get_accuracy(self, obj):
        return obj.accuracy_percentage

    class Meta:
        model = SubjectProgress
        fields = ['subject', 'questions_answered', 'correct_answers', 'accuracy']


#  Missions
class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = ['id', 'title', 'description', 'xp_reward', 'goal_type', 'goal_value', 'special_reward', 'special_reward_display']
    
    special_reward_display = serializers.CharField(source='get_special_reward_display', read_only=True)


class UserMissionSerializer(serializers.ModelSerializer):
    mission = MissionSerializer(read_only=True)
    completed = serializers.BooleanField(read_only=True)
    xp_claimed = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserMission
        fields = ['id', 'mission', 'progress', 'completed', 'xp_claimed', 'date']


class DashboardSerializer(serializers.Serializer):
    """Exibe os parâmetros na documentação do Dashboard."""
    level = serializers.IntegerField(read_only=True)
    xp = serializers.IntegerField(read_only=True)


class AnswerResponseSerializer(serializers.Serializer):
    is_correct = serializers.BooleanField(read_only=True)
    correct_letter = serializers.CharField(read_only=True)


class SessionFinishResponseSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(read_only=True)
