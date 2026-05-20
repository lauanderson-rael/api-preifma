from rest_framework import serializers
from .models import Exam, Question, Alternative, Attachment


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ['id', 'type', 'label', 'content', 'file']


class AttachmentWithOrderSerializer(serializers.Serializer):
    """Includes the `order` field from the through-table."""
    id = serializers.IntegerField(source='attachment.id')
    type = serializers.CharField(source='attachment.type')
    label = serializers.CharField(source='attachment.label', allow_null=True)
    content = serializers.CharField(source='attachment.content', allow_null=True)
    file = serializers.ImageField(source='attachment.file', allow_null=True)
    order = serializers.IntegerField()


class AlternativePublicSerializer(serializers.ModelSerializer):
    """Alternativas públicas — NÃO expõe is_correct."""
    class Meta:
        model = Alternative
        fields = ['id', 'letter', 'text']


class AlternativePrivateSerializer(serializers.ModelSerializer):
    """Alternativas com gabarito — uso interno."""
    class Meta:
        model = Alternative
        fields = ['id', 'letter', 'text', 'is_correct']


class QuestionSerializer(serializers.ModelSerializer):
    alternatives = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    exam_name = serializers.SerializerMethodField()
    exam_id = serializers.IntegerField(source='exam.id', read_only=True)

    def get_exam_name(self, obj):
        if not obj.exam or not obj.exam.name:
            return None
        name = obj.exam.name.replace(" TÉCNICO", "").replace(" TECNICO", "").replace(" -", "")
        return name

    def get_alternatives(self, obj):
        return AlternativePublicSerializer(obj.alternatives.all(), many=True).data

    def get_attachments(self, obj):
        ordered_qs = (
            obj.questionattachment_set
            .select_related('attachment')
            .order_by('order')
        )
        result = []
        for qa in ordered_qs:
            att = qa.attachment
            result.append({
                'id': att.id,
                'type': att.type,
                'label': att.label,
                'content': att.content,
                'file': att.file.url if att.file else None,
                'order': qa.order,
            })
        return result

    class Meta:
        model = Question
        fields = [
            'id', 'number', 'subject', 'statement', 
            'exam_id', 'exam_name', 
            'attachments', 'alternatives'
        ]


class ExamSerializer(serializers.ModelSerializer):
    total_questions = serializers.SerializerMethodField()

    def get_total_questions(self, obj):
        return obj.questions.count()

    class Meta:
        model = Exam
        fields = ['id', 'name', 'year', 'type', 'total_questions']


class ExamDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()

    def get_total_questions(self, obj):
        return obj.questions.count()

    class Meta:
        model = Exam
        fields = ['id', 'name', 'year', 'type', 'total_questions', 'questions']
