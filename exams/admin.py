from django.contrib import admin
from .models import Attachment, Exam, Question, QuestionAttachment, Alternative


class QuestionAttachmentInline(admin.TabularInline):
    model = QuestionAttachment
    extra = 1


class AlternativeInline(admin.TabularInline):
    model = Alternative
    extra = 5


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', '__str__', 'hash')
    list_filter = ('type',)
    search_fields = ('content', 'hash')


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'year', 'type')
    list_filter = ('year', 'type')
    search_fields = ('name',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'number', 'subject', 'exam')
    list_filter = ('subject', 'exam')
    search_fields = ('statement',)
    inlines = [QuestionAttachmentInline, AlternativeInline]
