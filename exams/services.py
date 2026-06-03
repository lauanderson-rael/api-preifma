import os
import json
import hashlib
import base64
from typing import Optional, Union
from django.core.files.base import ContentFile
from exams.models import Exam, Question, Alternative, Attachment, QuestionAttachment


def zip_package_has_images_folder(zip_path: str) -> bool:
    """Retorna True quando o ZIP contém uma pasta `images/` com pelo menos um arquivo."""
    try:
        import zipfile

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for name in zip_ref.namelist():
                normalized = name.replace("\\", "/").strip("/")
                if not normalized or normalized.endswith("/"):
                    continue
                parts = normalized.split("/")
                if "images" in parts[:-1]:
                    return True
            return False
    except Exception:
        return False

def save_exam_to_db(data: Union[dict, str], default_year: Optional[int] = None, base_path: Optional[str] = None) -> dict:
    """Salva uma prova no banco de dados a partir de JSON estruturado."""
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

    if not json_data:
        return {"error": "Formato inválido. O sistema agora aceita apenas JSON estruturado."}
    
    return _save_exam_from_json(json_data, default_year, base_path)


def _save_exam_from_json(data: dict, default_year: Optional[int] = None, base_path: Optional[str] = None) -> dict:
    questions_saved = 0
    errors = []

    # 1. Extrair Metadados da Prova
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

    # 2. Construir a Biblioteca Global de Anexos
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

    # 3. Processar Questões
    questions_list = data.get("questions", [])
    for q_data in questions_list:
        try:
            q_number = q_data.get("number", 0)
            subject = q_data.get("subject", "portugues").lower()
            if subject not in [s[0] for s in Question.SUBJECT_CHOICES]:
                subject = 'portugues'
            
            statement = q_data.get("text", "")
            correct_letter = q_data.get("correct_answer", "").upper()

            question, _ = Question.objects.update_or_create(
                exam=exam,
                number=q_number,
                defaults={'subject': subject, 'statement': statement}
            )

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


def _save_text_attachment(text_content: str, label: Optional[str] = None) -> Optional[Attachment]:
    """Salva texto limpo na biblioteca e retorna o Attachment."""
    text_content = text_content.strip() 
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
