import base64
import io
import re
import json
import requests
import fitz        
from typing import Optional, Union
from django.conf import settings  
from google import genai
from PIL import Image

# ─────────────────────────────────────────────────────────────────────────────
# 1. PDF Processing & Gemini Integration
# ─────────────────────────────────────────────────────────────────────────────

class PageData:
    def __init__(self, text: str, image_b64: str, width: int, height: int):
        self.text = text
        self.image_b64 = image_b64
        self.width = width
        self.height = height


def process_pdf(pdf_bytes: bytes, scale: float = 2.0) -> list[PageData]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[PageData] = []
    for page in doc:
        text = page.get_text("text")
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        pages.append(PageData(text=text, image_b64=image_b64, width=pix.width, height=pix.height))
    doc.close()
    return pages


def crop_image_b64(image_b64: str, img_w: int, img_h: int,
                   ymin: float, xmin: float, ymax: float, xmax: float,
                   pad_x: int = 34, pad_y: int = 20) -> str:
    img = Image.open(io.BytesIO(base64.b64decode(image_b64)))
    sx = int(xmin / 1000 * img_w)
    sy = int(ymin / 1000 * img_h)
    sw = int((xmax - xmin) / 1000 * img_w)
    sh = int((ymax - ymin) / 1000 * img_h)
    x = max(0, sx - pad_x)
    y = max(0, sy - pad_y)
    w = min(img_w - x, sw + pad_x * 2)
    h = min(img_h - y, sh + pad_y * 2)
    buf = io.BytesIO()
    img.crop((x, y, x + w, y + h)).save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


_PROMPT = """
Contexto: Você é um Especialista em Extração de Dados de Documentos Técnicos do IFMA. Sua missão é converter uma prova em um JSON para ingestão em banco de dados.

REGRAS CRÍTICAS DE EXTRAÇÃO:
1. METADADOS: O campo 'exam_title' DEVE seguir o formato: "SELETIVO TÉCNICO – [TIPO] [ANO]" (ex: SELETIVO TÉCNICO – SUBSEQUENTE 2024).
   - O campo 'type' deve ser "INTEGRADO", "SUBSEQUENTE" ou "CONCOMITANTE".
2. ANEXOS GLOBAIS (ZONA DE ALERTA):
   - Capture TODOS os textos de apoio, figuras, tabelas, quadros, gráficos, diagramas E TRECHOS DE CONTEXTO.
   - Os TEXTOS devem ser extraidos completamente sem cortes ou resumos! 
   - TRECHOS: Mesmo que um texto seja curto (ex: "Considere o trecho..."), se ele serve de base para responder questões, você DEVE extraí-lo como um anexo global.
   - LABEL: O campo 'label' deve ser idêntico ao que aparece na prova (ex: "Texto 1", "Figura 2", "Quadro 01", "Trecho para questões 03 a 05").
   - REGRAS DE LABEL: 
     - NÃO adicione descrições após o nome (ex: use "Texto 2", NÃO USE "Texto 2: Estatísticas...").
     - Se o texto indicar que é para questões específicas, inclua no label (ex: "Trecho para Questões 05 a 09").
   - SE FOR TEXTO PURO: Use type: "text" e coloque o conteúdo integral no campo 'content'.
   - SE FOR ELEMENTO VISUAL (Tabelas, Quadros, Gráficos, Mapas, Figuras de Matemática, Diagramas):
     - É EXPRESSAMENTE PROIBIDO converter tabelas ou quadros para texto ou markdown.
     - Você DEVE usar o formato de CAPTURA VISUAL: "CAPTURA:P[PÁGINA]:[ymin, xmin, ymax, xmax]" no campo 'image_data'.
     - Exemplo: "image_data": "CAPTURA:P1:[100, 200, 300, 400]" 
   - ATENÇÃO: Se uma questão tiver imagens essenciais para sua resolução, capture-as como anexo e vincule o ID na questão. NÃO IGNORE elementos visuais.
3. QUESTÕES:
   - 'number': Número da questão.
   - 'subject': Matéria detectada ("portugues" ou "matematica").
   - 'text': O enunciado completo e fiel.
   - 'local_attachments': Liste os IDs dos anexos globais (ex: ["Texto-1", "Figura-2"]) vinculados à questão.
   - 'alternatives': Extraia todas as opções (A a D) fielmente.
   - 'correct_answer': A letra correta (A, B, C ou D).
4. Deve-se extrair todas as 30 questões! 
ESQUEMA JSON ESPERADO: 
{
    "metadata": { "exam_title": "string", "year": 2024,"type": "INTEGRADO" }, 
    "global_attachments": [
        {
            "id": "Texto-1",
            "label": "Texto 1",
            "type": "text",
            "content": "Conteúdo integral..."
        },
        {
            "id": "Imagem-1",
            "label": "Figura 1",
            "type": "image",
            "image_data": "CAPTURA:P1:[ymin, xmin, ymax, xmax]"
        }
    ],
    "questions": [
        {
            "number": 1,
            "subject": "portugues",
            "text": "Enunciado...",
            "local_attachments": ["Texto-1"],
            "alternatives": [
                { "letter": "A", "text": "..." },
                { "letter": "B", "text": "..." }
            ],
            "correct_answer": "C"
        }
    ]
}

REQUISITO DE ARQUIVOS:
- No processamento final (pelo sistema), o campo 'image_data' será substituído por um campo 'path' apontando para 'images/ID.jpg'.
- Portanto, garanta que cada imagem essencial tenha um ID único e descritivo. 
Retorne APENAS o JSON puro, sem markdown (sem ```json), sem explicações adicionais.
"""


def _call_openrouter(prompt: str, pages: list[PageData], api_key: str) -> str:
    """Chamada para o OpenRouter (estilo OpenAI)"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000", # Opcional
        "X-OpenRouter-Title": "PRE-IFMA Parser"
    }
    
    content = [
        {"type": "text", "text": prompt}
    ]
    
    for p in pages:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{p.image_b64}"
            }
        })

    payload = {
        "model": getattr(settings, 'OPENROUTER_MODEL', 'google/gemini-2.0-flash-001'),
        "messages": [
            {"role": "system", "content": "Responda apenas com o JSON puro, sem blocos de código ou markdown."},
            {"role": "user", "content": content}
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        return json.dumps({"error": f"Erro no OpenRouter: {str(e)}"})


def transform_exam_to_json(pages: list[PageData], answer_key_text: Optional[str], api_key: str) -> dict:
    is_openrouter = api_key.startswith('sk-or-') or getattr(settings, 'OPENROUTER_API_KEY', '') == api_key
    
    full_text = "\n\n".join(f"--- PÁGINA {i + 1} ---\n{p.text}" for i, p in enumerate(pages))
    prompt_text = _PROMPT + f"\n\nGABARITO: {answer_key_text if answer_key_text else 'Não fornecido'}\n\nCONTEÚDO:\n{full_text}"
    
    if is_openrouter:
        raw_text = _call_openrouter(prompt_text, pages, api_key)
    else:
        # Gemini Direto
        client = genai.Client(api_key=api_key)
        parts = [prompt_text]
        for p in pages:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": p.image_b64}})
        
        response = client.models.generate_content(model="gemini-2.0-flash", contents=parts)
        raw_text = response.text or "{}"
    
    # Limpeza básica caso o modelo ignore a instrução de "sem markdown"
    clean_json = re.sub(r'```json\s*|\s*```', '', raw_text).strip()
    try:
        return json.loads(clean_json)
    except Exception:
        return {"error": "Falha ao decodificar JSON da IA", "raw": raw_text}


def process_visual_captures_in_json(data: dict, pages: list[PageData]) -> dict:
    """
    Percorre o JSON procurando por strings "CAPTURA:P[N]:[ymin, xmin, ymax, xmax]"
    e as substitui por data:image/jpeg;base64,...
    """
    _CAPTURE_RE = re.compile(r'CAPTURA:P(\d+):\[([^\]]+)\]', re.I)

    def process_item(item):
        if isinstance(item, str):
            match = _CAPTURE_RE.search(item)
            if match:
                page_idx = int(match.group(1)) - 1
                coords = [float(v.strip()) for v in match.group(2).split(",")]
                ymin, xmin, ymax, xmax = (coords + [0, 0, 0, 0])[:4]
                
                if 0 <= page_idx < len(pages):
                    b64 = crop_image_b64(pages[page_idx].image_b64, pages[page_idx].width, pages[page_idx].height,
                                          ymin, xmin, ymax, xmax)
                    return f'data:image/jpeg;base64,{b64}'
            return item
        elif isinstance(item, list):
            return [process_item(i) for i in item]
        elif isinstance(item, dict):
            return {k: process_item(v) for k, v in item.items()}
        return item

    return process_item(data)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Pipeline Completo (PDF → JSON)
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(exam_bytes: bytes, answer_key_bytes: Optional[bytes] = None, api_key: str = "") -> dict:
    pages = process_pdf(exam_bytes)
    ak_text = "\n".join(p.text for p in process_pdf(answer_key_bytes)) if answer_key_bytes else None
    
    # Agora retorna um DICT (JSON estruturado)
    exam_json = transform_exam_to_json(pages, ak_text, api_key)
    
    if "error" in exam_json:
        return exam_json

    return process_visual_captures_in_json(exam_json, pages)