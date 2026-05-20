from django.contrib import admin
from .models import (StudySession, Answer, SubjectProgress,Mission, UserMission) 


@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'total_questions', 'correct_answers', 'xp_gained', 'created_at')
    list_filter = ('type', 'created_at')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'question', 'selected_alternative', 'correct_letter', 'is_correct', 'response_time')
    list_filter = ('is_correct', 'created_at')


@admin.register(SubjectProgress)
class SubjectProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'questions_answered', 'correct_answers', 'accuracy_percentage')
    list_filter = ('subject',)


@admin.register(Mission)
class MissionAdmin(admin.ModelAdmin):
    list_display = ('title', 'goal_type', 'goal_subject', 'goal_value', 'xp_reward', 'special_reward')
    list_filter = ('goal_type', 'goal_subject', 'special_reward')
    search_fields = ('title', 'description')


@admin.register(UserMission)
class UserMissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'mission', 'progress', 'completed', 'date')
    list_filter = ('completed', 'date')
    search_fields = ('user__username', 'mission__title')
