import base64
import io
import re
import hashlib
from typing import Optional

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
Transforme o conteúdo da prova em HTML estruturado.

1. Cabeçalho: <h1 class="exam-title">TÍTULO DA PROVA</h1>

2. Bloco de anexos GLOBAIS (antes das questões):
<section class="attachments-global">
  <div class="attachment-item" id="Texto-1">Texto 1: <span>conteúdo do texto...</span></div>
  <div class="attachment-item" id="Texto-2">Texto 2: título da imagem <img src="data:image/jpeg;base64,..." /></div>
  <div class="attachment-item" id="Trecho-1">Trecho 1 (para questões X-Y): <span>trecho do texto...</span></div>
</section>

3. Questões - cada uma com seu número, referência ao anexo e alternativas:
<article class="question-block" data-question-number="01" data-correct-alternative="C">
  <div class="question-meta">tipo: múltipla escolha, materia: Língua Portuguesa</div>
  <div class="question-number">01</div>
  <div class="question-context">
    <div class="attachment-ref" data-ref="Texto-1">Trecho correspondente: Texto 1</div>
  </div>
  <div class="question-statement">Enunciado da questão aqui.</div>
  <div class="question-alternatives">
    <ul>
      <li>A) alternativa A</li>
      <li>B) alternativa B</li>
      <li>C) alternativa C</li>
      <li>D) alternativa D</li>
    </ul>
  </div>
  <div class="correct-answer">Gabarito: <span>C</span></div>
</article>

=== REGRAS ===
- Detecte a matéria: "Língua Portuguesa" ou "Matemática"
- Use data-ref com o ID exato do attachment-item (ex: "Texto-1", "Trecho-1")
- Use <div class="visual-capture" data-page="P" data-bbox="[ymin, xmin, ymax, xmax]"></div> para imagens capturadas do PDF
- Se uma questão não tiver texto de apoio, omita a div.question-context
- Retorne APENAS o HTML, sem markdown, sem explicações.
"""


def transform_exam_to_html(pages: list[PageData], answer_key_text: Optional[str], api_key: str) -> str:
    client = genai.Client(api_key=api_key)
    full_text = "\n\n".join(f"--- PÁGINA {i + 1} ---\n{p.text}" for i, p in enumerate(pages))
    prompt_text = _PROMPT + f"\n\nGABARITO: {answer_key_text if answer_key_text else 'Não fornecido'}\n\nCONTEÚDO:\n{full_text}"
    parts = [prompt_text]
    for p in pages:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": p.image_b64}})
    response = client.models.generate_content(model="gemini-2.0-flash", contents=parts)
    return response.text or ""


def process_visual_captures(raw_html: str, pages: list[PageData]) -> str:
    _CAPTURE_RE = re.compile(
        r'<div\s+class=["\']visual-capture["\']\s+data-page=["\'](\d+)["\']\s+data-bbox=["\'][^\[]*\[([^\]]+)\]["\']?\s*(?:></div>|/>)',
        re.I
    )
    def replacer(m: re.Match) -> str:
        page_idx = int(m.group(1)) - 1
        coords = [float(v.strip()) for v in m.group(2).split(",")]
        ymin, xmin, ymax, xmax = (coords + [0, 0, 0, 0])[:4]
        if 0 <= page_idx < len(pages):
            b64 = crop_image_b64(pages[page_idx].image_b64, pages[page_idx].width, pages[page_idx].height,
                                  ymin, xmin, ymax, xmax)
            return f'<img src="data:image/jpeg;base64,{b64}" class="exam-capture-img" />'
        return ""
    return _CAPTURE_RE.sub(replacer, raw_html)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Funções de Suporte para Ingestão
# ─────────────────────────────────────────────────────────────────────────────

def _save_image_attachment(src: str) -> Optional[Attachment]:
    """Salva uma imagem base64 na biblioteca e retorna o Attachment."""
    if not src.startswith('data:image/'):
        return None
    format_part, imgstr = src.split(';base64,')
    ext = format_part.split('/')[-1]
    img_hash = hashlib.md5(imgstr.encode()).hexdigest()
    att, _ = Attachment.objects.get_or_create(
        hash=img_hash,
        type='image',
        defaults={'file': ContentFile(base64.b64decode(imgstr), name=f"img_{img_hash}.{ext}")}
    )
    return att


def _save_text_attachment(html_content: str) -> Optional[Attachment]:
    """Salva texto HTML limpo na biblioteca e retorna o Attachment."""
    text_content = html_content.strip()
    if not text_content:
        return None
    text_hash = hashlib.md5(text_content.encode()).hexdigest()
    att, _ = Attachment.objects.get_or_create(
        hash=text_hash,
        type='text',
        defaults={'content': text_content}
    )
    return att


def _process_attachment_item(item_div) -> Optional[Attachment]:
    """
    Processa um div.attachment-item do Modelo 02.
    Retorna EXATAMENTE um Attachment por div (proporção 1:1):
      - Se contém <img> → salva como type='image' (ignora o rótulo de texto).
      - Se é só texto    → salva como type='text'.
    """
    img_tag = item_div.find('img')

    if img_tag:
        # Anexo é uma imagem (gráfico, charge, tabela…)
        return _save_image_attachment(img_tag.get('src', ''))
    else:
        # Anexo é texto puro
        return _save_text_attachment(item_div.decode_contents().strip())


# ─────────────────────────────────────────────────────────────────────────────
# 3. Pipeline de Ingestão Principal (Modelo 02)
# ─────────────────────────────────────────────────────────────────────────────

def save_exam_to_db(html_content: str, default_year: Optional[int] = None) -> dict:
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
    # Mapeia: id do attachment-item → 1 Attachment no banco
    attachment_library: dict[str, Attachment] = {}

    global_section = soup.find('section', class_='attachments-global')
    if global_section:
        for item in global_section.find_all('div', class_='attachment-item'):
            item_id = item.get('id', '').strip()
            if not item_id:
                continue

            att = _process_attachment_item(item)
            if att:
                attachment_library[item_id] = att

    # ── C. Processar Questões ──────────────────────────────────────────────
    blocks = soup.find_all('article', class_='question-block')
    for block in blocks:
        try:
            # 1. Número e Matéria
            num_attr = block.get('data-question-number', '0')
            question_number = int(num_attr) if str(num_attr).isdigit() else 0

            meta_el = block.find('div', class_='question-meta')
            meta_text = meta_el.get_text().lower() if meta_el else ""
            subject = 'portugues'
            if any(k in meta_text for k in ['matem', 'math', 'raciocin']):
                subject = 'matematica'

            # 2. Criar ou Reutilizar Questão (idempotente por exam + number)
            question, created = Question.objects.get_or_create(
                exam=exam,
                number=question_number,
                defaults={'subject': subject, 'statement': ''}
            )

            # 3. Vincular Anexos via attachment-ref (1 ref = 1 Attachment)
            context_div = block.find('div', class_='question-context')
            order_counter = 1
            if context_div:
                for ref in context_div.find_all('div', class_='attachment-ref'):
                    ref_id = ref.get('data-ref', '').strip()
                    att = attachment_library.get(ref_id)
                    if att:
                        QuestionAttachment.objects.get_or_create(
                            question=question,
                            attachment=att,
                            defaults={'order': order_counter}
                        )
                        order_counter += 1

            # 4. Statement
            statement_el = block.find('div', class_='question-statement')
            statement_html = statement_el.decode_contents().strip() if statement_el else ""
            # Remove número no início do enunciado
            statement_html = re.sub(r'^\s*\d+[\s.)-]+\s*', '', statement_html, count=1)
            question.statement = statement_html
            question.save()

            # 5. Alternativas
            correct_letter = block.get('data-correct-alternative', '').upper()
            alt_list = block.find('div', class_='question-alternatives')
            if alt_list:
                for item in alt_list.find_all('li'):
                    text = item.get_text().strip()
                    if len(text) >= 2:
                        letter = text[0].upper()
                        if text[1:3] == ") ":
                            content = text[3:]
                        elif text[1] == ")":
                            content = text[2:]
                        else:
                            content = text
                        Alternative.objects.update_or_create(
                            question=question,
                            letter=letter,
                            defaults={'text': content, 'is_correct': (letter == correct_letter)}
                        )

            questions_saved += 1

        except Exception as e:
            errors.append(f"Questão {block.get('data-question-number', '?')}: {str(e)}")

    return {"saved": questions_saved, "errors": errors, "attachments_in_library": len(attachment_library)}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Pipeline Completo (PDF → HTML → DB)
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(exam_bytes: bytes, answer_key_bytes: Optional[bytes] = None, api_key: str = "") -> str:
    pages = process_pdf(exam_bytes)
    ak_text = "\n".join(p.text for p in process_pdf(answer_key_bytes)) if answer_key_bytes else None
    raw_html = transform_exam_to_html(pages, ak_text, api_key)
    return process_visual_captures(raw_html, pages)
