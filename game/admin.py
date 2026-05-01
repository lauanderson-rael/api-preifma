from django.contrib import admin
from .models import (
    StudySession, Answer, SubjectProgress,
    Mission, UserMission, Achievement, UserAchievement
)


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'total_questions', 'correct_answers', 'xp_gained', 'created_at')
    list_filter = ('type', 'created_at')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'question', 'selected_letter', 'is_correct', 'response_time')
    list_filter = ('is_correct', 'created_at')


@admin.register(SubjectProgress)
class SubjectProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'questions_answered', 'correct_answers', 'accuracy_percentage')
    list_filter = ('subject',)


admin.site.register(Mission)
admin.site.register(UserMission)
admin.site.register(Achievement)
admin.site.register(UserAchievement)
