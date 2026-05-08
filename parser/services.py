import base64
import io
import re
import hashlib
import json
import os
from typing import Optional, Union

import fitz        
from google import genai
from PIL import Image
from bs4 import BeautifulSoup

from django.core.files.base import ContentFile
from exams.models import Exam, Question, Alternative, Attachment, QuestionAttachment

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
Contexto: Você é um Especialista em Processamento de Dados do IFMA.
Extraia os dados da prova e retorne APENAS um JSON estruturado seguindo EXATAMENTE este esquema:

{
    "metadata": {
        "exam_title": "TÍTULO COMPLETO DA PROVA",
        "year": 2024,
        "type": "INTEGRADO"
    },
    "global_attachments": [
        {
            "id": "Texto-1",
            "label": "Texto 1",
            "type": "text",
            "content": "Conteúdo integral do texto de apoio..."
        },
        {
            "id": "Imagem-1",
            "label": "Figura 1",
            "type": "image",
            "image_data": "CAPTURA:P[N]:[ymin, xmin, ymax, xmax]"
        }
    ],
    "questions": [
        {
            "number": 1,
            "subject": "portugues",
            "text": "Enunciado da questão...",
            "local_attachments": ["ID ou Label do anexo global correspondente"],
            "alternatives": [
                { "letter": "A", "text": "Texto da opção A" },
                { "letter": "B", "text": "Texto da opção B" }
            ],
            "correct_answer": "C"
        }
    ]
}

=== REGRAS DE CAPTURA VISUAL ===
Se houver uma imagem, gráfico ou texto complexo que precise de captura visual do PDF, use EXATAMENTE este formato no campo `image_data`:
"CAPTURA:P[PÁGINA]:[ymin, xmin, ymax, xmax]"
Exemplo: "CAPTURA:P1:[100, 200, 300, 400]"

=== REGRAS GERAIS ===
- Detecte a matéria: "portugues" ou "matematica".
- O campo `type` em metadata deve ser "INTEGRADO", "SUBSEQUENTE" ou "CONCOMITANTE".
- Retorne APENAS o JSON puro, sem markdown (sem ```json), sem explicações.
"""


def transform_exam_to_json(pages: list[PageData], answer_key_text: Optional[str], api_key: str) -> dict:
    client = genai.Client(api_key=api_key)
    full_text = "\n\n".join(f"--- PÁGINA {i + 1} ---\n{p.text}" for i, p in enumerate(pages))
    prompt_text = _PROMPT + f"\n\nGABARITO: {answer_key_text if answer_key_text else 'Não fornecido'}\n\nCONTEÚDO:\n{full_text}"
    
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
        # Fallback para string vazia ou erro
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
# 2. Funções de Suporte para Ingestão
# ─────────────────────────────────────────────────────────────────────────────

def _save_image_attachment(src: str, label: Optional[str] = None) -> Optional[Attachment]:
    """Salva uma imagem base64 na biblioteca e retorna o Attachment."""
    if not src.startswith('data:image/'):
        return None
    format_part, imgstr = src.split(';base64,')
    ext = format_part.split('/')[-1]
    img_hash = hashlib.md5(imgstr.encode()).hexdigest()
    att, _ = Attachment.objects.get_or_create(
        hash=img_hash,
        type='image',
        defaults={
            'file': ContentFile(base64.b64decode(imgstr), name=f"img_{img_hash}.{ext}"),
            'label': label
        }
    )
    return att


def _save_image_from_path(file_path: str, label: Optional[str] = None) -> Optional[Attachment]:
    """Lê uma imagem do disco, salva na biblioteca e retorna o Attachment."""
    if not os.path.exists(file_path):
        return None
        
    with open(file_path, 'rb') as f:
        img_data = f.read()
        
    img_hash = hashlib.md5(img_data).hexdigest()
    ext = os.path.splitext(file_path)[1].lower().replace('.', '')
    if not ext: ext = 'jpg'

    att, _ = Attachment.objects.get_or_create(
        hash=img_hash,
        type='image',
        defaults={
            'file': ContentFile(img_data, name=f"img_{img_hash}.{ext}"),
            'label': label
        }
    )
    return att


def _save_text_attachment(html_content: str, label: Optional[str] = None) -> Optional[Attachment]:
    """Salva texto HTML limpo na biblioteca e retorna o Attachment."""
    text_content = html_content.strip()
    if not text_content:
        return None
    text_hash = hashlib.md5(text_content.encode()).hexdigest()
    att, _ = Attachment.objects.get_or_create(
        hash=text_hash,
        type='text',
        defaults={
            'content': text_content,
            'label': label
        }
    )
    return att

def _process_attachment_item(item_div) -> Optional[Attachment]:
    """
    Processa um div.attachment-item do Modelo 02.
    Retorna EXATAMENTE um Attachment por div (proporção 1:1):
      - Se contém <img> → salva como type='image' (ignora o rótulo de texto).
      - Se é só texto    → salva como type='text'.
    Separa 'label' (antes do :) e 'content' (depois do :), limpando tags <span>.
    """
    raw_html = item_div.decode_contents().strip()
    label = None
    content = raw_html

    if ":" in raw_html:
        parts = raw_html.split(":", 1)
        label = parts[0].strip()
        content = parts[1].strip()
        
    # Limpa tags <span> e </span> do content
    content = content.replace("<span>", "").replace("</span>", "").strip()

    img_tag = item_div.find('img')

    if img_tag:
        # Anexo é uma imagem (gráfico, charge, tabela…)
        return _save_image_attachment(img_tag.get('src', ''), label=label)
    else:
        # Anexo é texto puro
        return _save_text_attachment(content, label=label)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Pipeline de Ingestão Principal (Modelo 02)
# ─────────────────────────────────────────────────────────────────────────────

def save_exam_to_db(data: Union[dict, str], default_year: Optional[int] = None, base_path: Optional[str] = None) -> dict:
    """
    Ingere uma prova no banco de dados. 
    Suporta o formato legado (HTML via BeautifulSoup) e o novo formato (JSON estruturado).
    """
    # Tenta detectar se é o novo formato JSON
    json_data = None
    if isinstance(data, dict):
        json_data = data
    elif isinstance(data, str) and data.strip().startswith('{'):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict) and ("questions" in parsed or "metadata" in parsed):
                json_data = parsed
        except json.JSONDecodeError:
            pass

    if json_data:
        return _save_exam_from_json(json_data, default_year, base_path)
    
    # Caso contrário, assume o formato HTML legado
    return _save_exam_from_html(str(data), default_year)


def _save_exam_from_json(data: dict, default_year: Optional[int] = None, base_path: Optional[str] = None) -> dict:
    questions_saved = 0
    errors = []

    # ── A. Extrair Metadados da Prova ──────────────────────────────────────
    metadata = data.get("metadata", {})
    exam_title = metadata.get("exam_title", "Sem Título")
    year = metadata.get("year") or default_year or 2025
    exam_type = metadata.get("type", "integrado").lower()

    valid_types = [t[0] for t in Exam.TYPE_CHOICES]
    if exam_type not in valid_types:
        exam_type = 'integrado'

    exam, _ = Exam.objects.get_or_create(
        year=year,
        type=exam_type,
        defaults={'name': exam_title}
    )

    # ── B. Construir a Biblioteca Global de Anexos ─────────────────────────
    # Mapeia tanto label quanto ID para garantir que as referências funcionem
    attachment_library: dict[str, Attachment] = {}
    global_attachments = data.get("global_attachments", [])
    for item in global_attachments:
        label = item.get("label", "").strip()
        item_id = item.get("id", "").strip()
        att_type = item.get("type")
        
        att = None
        if att_type == "image":
            image_data = item.get("image_data", "")
            relative_path = item.get("path", "")
            
            if image_data:
                att = _save_image_attachment(image_data, label=label)
            elif relative_path and base_path:
                full_path = os.path.join(base_path, relative_path)
                att = _save_image_from_path(full_path, label=label)
                
        elif att_type == "text":
            content = item.get("content", "")
            if content:
                att = _save_text_attachment(content, label=label)
        
        if att:
            if label: attachment_library[label] = att
            if item_id: attachment_library[item_id] = att

    # ── C. Processar Questões ──────────────────────────────────────────────
    questions_list = data.get("questions", [])
    for q_data in questions_list:
        try:
            q_number = q_data.get("number", 0)
            subject = q_data.get("subject", "portugues").lower()
            if subject not in [s[0] for s in Question.SUBJECT_CHOICES]:
                subject = 'portugues'
            
            statement = q_data.get("text", "")
            correct_letter = q_data.get("correct_answer", "").upper()

            # 1. Criar ou Reutilizar Questão
            question, _ = Question.objects.update_or_create(
                exam=exam,
                number=q_number,
                defaults={'subject': subject, 'statement': statement}
            )

            # 2. Vincular Anexos (Limpa antigos para garantir nova ordem)
            QuestionAttachment.objects.filter(question=question).delete()
            local_refs = q_data.get("local_attachments", [])
            for i, ref_key in enumerate(local_refs):
                att = attachment_library.get(ref_key.strip())
                if att:
                    QuestionAttachment.objects.create(
                        question=question,
                        attachment=att,
                        order=i + 1
                    )

            # 3. Alternativas
            alternatives = q_data.get("alternatives", [])
            for alt in alternatives:
                letter = alt.get("letter", "").upper()
                alt_text = alt.get("text", "")
                if letter and alt_text:
                    Alternative.objects.update_or_create(
                        question=question,
                        letter=letter,
                        defaults={'text': alt_text, 'is_correct': (letter == correct_letter)}
                    )
            questions_saved += 1
        except Exception as e:
            errors.append(f"Questão {q_data.get('number', '?')}: {str(e)}")

    return {"saved": questions_saved, "errors": errors, "attachments_in_library": len(attachment_library), "exam": exam.name}


def _save_exam_from_html(html_content: str, default_year: Optional[int] = None) -> dict:
    soup = BeautifulSoup(html_content, 'html.parser')
    questions_saved = 0
    errors = []

    # ── A. Extrair Título e Metadados da Prova ─────────────────────────────
    all_text = soup.get_text().lower()
    extracted_year = default_year or 2025
    year_match = re.search(r'(20\d{2})', all_text)
    if year_match:
        extracted_year = int(year_match.group(1))

    extracted_type = 'integrado'
    title_el = soup.find('h1', class_='exam-title')
    search_text = title_el.get_text().lower() if title_el else all_text
    if 'subsequente' in search_text:
        extracted_type = 'subsequente'
    elif 'concomitante' in search_text:
        extracted_type = 'concomitante'

    exam_name = f"SELETIVO TÉCNICO - {extracted_type.upper()} {extracted_year}"
    exam, _ = Exam.objects.get_or_create(
        year=extracted_year,
        type=extracted_type,
        defaults={'name': exam_name}
    )

    # ── B. Construir a Biblioteca Global de Anexos ─────────────────────────
    attachment_library: dict[str, Attachment] = {}
    global_section = soup.find('section', class_='attachments-global')
    if global_section:
        for item in global_section.find_all('div', class_='attachment-item'):
            item_id = item.get('id', '').strip()
            if not item_id: continue
            att = _process_attachment_item(item)
            if att: attachment_library[item_id] = att

    # ── C. Processar Questões ──────────────────────────────────────────────
    blocks = soup.find_all('article', class_='question-block')
    for block in blocks:
        try:
            num_attr = block.get('data-question-number', '0')
            question_number = int(num_attr) if str(num_attr).isdigit() else 0

            meta_el = block.find('div', class_='question-meta')
            meta_text = meta_el.get_text().lower() if meta_el else ""
            subject = 'portugues'
            if any(k in meta_text for k in ['matem', 'math', 'raciocin']):
                subject = 'matematica'

            question, _ = Question.objects.get_or_create(
                exam=exam,
                number=question_number,
                defaults={'subject': subject, 'statement': ''}
            )

            # Limpa vínculos antigos para garantir nova ordem
            QuestionAttachment.objects.filter(question=question).delete()
            context_div = block.find('div', class_='question-context')
            if context_div:
                for i, ref in enumerate(context_div.find_all('div', class_='attachment-ref')):
                    ref_id = ref.get('data-ref', '').strip()
                    att = attachment_library.get(ref_id)
                    if att:
                        QuestionAttachment.objects.create(
                            question=question,
                            attachment=att,
                            order=i + 1
                        )

            statement_el = block.find('div', class_='question-statement')
            statement_html = statement_el.decode_contents().strip() if statement_el else ""
            statement_html = re.sub(r'^\s*\d+[\s.)-]+\s*', '', statement_html, count=1)
            question.statement = statement_html
            question.save()

            correct_letter = block.get('data-correct-alternative', '').upper()
            alt_list = block.find('div', class_='question-alternatives')
            if alt_list:
                for item in alt_list.find_all('li'):
                    text = item.get_text().strip()
                    if len(text) >= 2:
                        letter = text[0].upper()
                        content = text[3:] if text[1:3] == ") " else (text[2:] if text[1] == ")" else text)
                        Alternative.objects.update_or_create(
                            question=question,
                            letter=letter,
                            defaults={'text': content, 'is_correct': (letter == correct_letter)}
                        )
            questions_saved += 1
        except Exception as e:
            errors.append(f"Questão {block.get('data-question-number', '?')}: {str(e)}")

    return {"saved": questions_saved, "errors": errors, "attachments_in_library": len(attachment_library), "exam": exam.name}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Pipeline Completo (PDF → HTML → DB)
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(exam_bytes: bytes, answer_key_bytes: Optional[bytes] = None, api_key: str = "") -> dict:
    pages = process_pdf(exam_bytes)
    ak_text = "\n".join(p.text for p in process_pdf(answer_key_bytes)) if answer_key_bytes else None
    
    # Agora retorna um DICT (JSON estruturado)
    exam_json = transform_exam_to_json(pages, ak_text, api_key)
    
    if "error" in exam_json:
        return exam_json

    return process_visual_captures_in_json(exam_json, pages)