from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django import forms
import json
import zipfile
import tempfile
import os
from parser.services import save_exam_to_db
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


class ZipUploadForm(forms.Form):
    zip_file = forms.FileField(label="Arquivo .ZIP da Prova")

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'year', 'type')
    list_filter = ('year', 'type')
    search_fields = ('name',)
    change_list_template = "admin/exams/exam/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-zip/', self.admin_site.admin_view(self.import_zip), name='exam_import_zip'),
        ]
        return custom_urls + urls

    def import_zip(self, request):
        if request.method == "POST":
            form = ZipUploadForm(request.POST, request.FILES)
            if form.is_valid():
                zip_file = request.FILES['zip_file']
                try:
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        # Salvar o upload
                        temp_zip_path = os.path.join(tmp_dir, 'upload.zip')
                        with open(temp_zip_path, 'wb+') as destination:
                            for chunk in zip_file.chunks():
                                destination.write(chunk)

                        # Extrair
                        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                            zip_ref.extractall(tmp_dir)

                        # Localizar prova.json
                        json_path = None
                        base_extract_path = tmp_dir
                        for root, dirs, files in os.walk(tmp_dir):
                            if 'prova.json' in files:
                                json_path = os.path.join(root, 'prova.json')
                                base_extract_path = root
                                break

                        if not json_path:
                            self.message_user(request, "Erro: Arquivo prova.json não encontrado dentro do ZIP.", level=messages.ERROR)
                            return HttpResponseRedirect("../")

                        with open(json_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        result = save_exam_to_db(data, base_path=base_extract_path)
                        
                        if "error" in result:
                            self.message_user(request, f"Erro no processamento: {result['error']}", level=messages.ERROR)
                        else:
                            msg = f"Sucesso! Prova '{result.get('exam')}' importada. {result.get('saved')} questões salvas."
                            if result.get('errors'):
                                msg += f" ({len(result['errors'])} erros menores)"
                            self.message_user(request, msg, level=messages.SUCCESS)
                        
                        return HttpResponseRedirect("../")

                except Exception as e:
                    self.message_user(request, f"Erro fatal: {str(e)}", level=messages.ERROR)
                    return HttpResponseRedirect("../")

        form = ZipUploadForm()
        payload = {"form": form, "opts": self.model._meta}
        return render(request, "admin/exams/exam/import_zip.html", payload)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'number', 'subject', 'exam')
    list_filter = ('subject', 'exam')
    search_fields = ('statement',)
    inlines = [QuestionAttachmentInline, AlternativeInline]
