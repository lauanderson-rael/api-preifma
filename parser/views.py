import traceback
from django.shortcuts import render
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

from .services import run_pipeline, save_exam_to_db


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
    # Chave: prioridade → override do form → settings
    api_key = request.POST.get("api_key_override", "").strip() or settings.GEMINI_API_KEY

    if not api_key:
        return JsonResponse(
            {"error": "GEMINI_API_KEY não configurada. Cole sua chave no campo indicado."},
            status=500,
        )

    exam_file = request.FILES.get("exam_pdf")
    if not exam_file:
        return JsonResponse({"error": "Envie o arquivo da prova (campo exam_pdf)."}, status=400)

    answer_key_file = request.FILES.get("answer_key_pdf")

    try:
        exam_bytes = exam_file.read()
        answer_key_bytes = answer_key_file.read() if answer_key_file else None

        html_result = run_pipeline(exam_bytes, answer_key_bytes, api_key=api_key)
        return JsonResponse({"html": html_result})

    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_to_db_view(request: HttpRequest):
    """
    Recebe o HTML estruturado via POST e salva no banco de dados.
    """
    import json
    try:
        data = json.loads(request.body)
        html_content = data.get("html", "")
        year = data.get("ano") # Pode vir nulo
        
        if not html_content:
            return JsonResponse({"error": "Nenhum HTML recebido."}, status=400)

        result = save_exam_to_db(html_content, default_year=int(year) if year else None)
        
        if "error" in result:
            return JsonResponse(result, status=400)
            
        return JsonResponse(result)

    except Exception as exc:
        traceback.print_exc()
        return JsonResponse({"error": str(exc)}, status=500)
