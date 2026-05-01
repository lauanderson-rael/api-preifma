from rest_framework import serializers
from exams.models import Question, Alternative, Attachment, QuestionAttachment


class AlternativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alternative
        fields = ['id', 'letter', 'text', 'is_correct']


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = ['id', 'type', 'content', 'file']


class QuestionSerializer(serializers.ModelSerializer):
    alternatives = AlternativeSerializer(many=True, read_only=True)
    attachments = serializers.SerializerMethodField()

    def get_attachments(self, obj):
        ordered = obj.questionattachment_set.select_related('attachment').order_by('order')
        return AttachmentSerializer([qa.attachment for qa in ordered], many=True).data

    class Meta:
        model = Question
        fields = ['id', 'number', 'subject', 'statement', 'alternatives', 'attachments']
