import traceback
from django.shortcuts import render
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings 
import json
import zipfile
import tempfile
import os

from .services import run_pipeline
from exams.services import save_exam_to_db


def index(request: HttpRequest):
    return render(request, "parser/index.html", {
        "has_api_key": bool(settings.GEMINI_API_KEY),
    })


@csrf_exempt
@require_http_methods(["POST"])
def process(request: HttpRequest):
    """
    Recebe:   exam_pdf (obrigatório), answer_key_pdf (opcional),
              api_key_override (opcional — quando a chave não está no servidor)
    Devolve:  JSON { "html": "..." } ou { "error": "..." }
    """
    # Chave: prioridade → override do form → OpenRouter → Gemini
    api_key = (request.POST.get("api_key_override", "").strip() or 
               settings.OPENROUTER_API_KEY or 
               settings.GEMINI_API_KEY)

    if not api_key:
        return JsonResponse(
            {"error": "Nenhuma chave de API configurada (Gemini ou OpenRouter)."},
            status=500,
        )

    exam_file = request.FILES.get("exam_pdf")
    if not exam_file:
        return JsonResponse({"error": "Envie o arquivo da prova (campo exam_pdf)."}, status=400)

    answer_key_file = request.FILES.get("answer_key_pdf")

    try:
        exam_bytes = exam_file.read()
        answer_key_bytes = answer_key_file.read() if answer_key_file else None

        exam_json = run_pipeline(exam_bytes, answer_key_bytes, api_key=api_key)
        return JsonResponse(exam_json)

    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_to_db_view(request: HttpRequest):
    """
    Recebe os dados estruturados da prova (JSON) via POST e salva no banco de dados.
    """
    try:
        data = json.loads(request.body)
        
        if not data:
            return JsonResponse({"error": "Nenhum conteúdo recebido para salvar."}, status=400)
        result = save_exam_to_db(data)
        
        if "error" in result:
            return JsonResponse(result, status=400)
            
        return JsonResponse(result)

    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def ingest_zip_view(request: HttpRequest):
    """
    Recebe um arquivo .zip (campo 'zip_file'), extrai e salva no banco.
    """
    zip_file = request.FILES.get("zip_file")
    if not zip_file:
        return JsonResponse({"error": "Envie o arquivo .zip (campo zip_file)."}, status=400)

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Salvar o upload em um arquivo temporário para o ZipFile ler
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
                return JsonResponse({"error": "Arquivo prova.json não encontrado dentro do ZIP."}, status=400)

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            result = save_exam_to_db(data, base_path=base_extract_path)
            
            if "error" in result:
                return JsonResponse(result, status=400)
                
            return JsonResponse(result)

    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({"error": str(exc)}, status=500)
