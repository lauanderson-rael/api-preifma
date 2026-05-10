from datetime import date
from django.conf import settings
from .models import UserAIDailyUsage
from exams.models import Question, QuestionExplanation
from parser.services import generate_question_explanation


def update_streak(user):
    # ... (mantém igual) ...
    today = date.today()
    lsd = user.last_study_date
    if lsd is None:
        user.streak = 1
    elif lsd == today:
        pass
    else:
        delta = (today - lsd).days
        if delta == 1:
            user.streak += 1
        else:
            user.streak = 1
    user.last_study_date = today
    user.save(update_fields=['streak', 'last_study_date'])
    return user.streak


def get_or_generate_explanation(user, question_id: int) -> dict:
    """
    Retorna a explicação de uma questão. 
    Lógica: Cache -> Cota Diária -> IA -> Salvar Cache -> Debitar Cota.
    """
    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        return {"error": "Questão não encontrada."}

    # 1. Checa Cota Diária PRIMEIRO
    today = date.today()
    usage, created = UserAIDailyUsage.objects.get_or_create(user=user, date=today)
    
    total_allowed = user.ai_daily_limit + usage.bonus_limit

    if usage.count >= total_allowed:
        return {
            "error": "Cota diária atingida.", 
            "limit": total_allowed,
            "usage": usage.count
        }

    # 2. Checa Cache
    if hasattr(question, 'explanation'):
        usage.count += 1
        usage.save()
        return {
            "content": question.explanation.content, 
            "cached": True,
            "remaining": total_allowed - usage.count
        }

    # 3. Chama IA
    api_key = settings.OPENROUTER_API_KEY or settings.GEMINI_API_KEY
    if not api_key:
        return {"error": "Serviço de IA não configurado no servidor."}

    alts = [{"letter": a.letter, "text": a.text} for a in question.alternatives.all()]
    correct = question.alternatives.filter(is_correct=True).first()
    correct_letter = correct.letter if correct else "?"

    # Coleta imagens dos anexos
    images_b64 = []
    import base64
    for att in question.attachments.all():
        if att.file:
            try:
                with att.file.open('rb') as f:
                    encoded = base64.b64encode(f.read()).decode('utf-8')
                    images_b64.append(encoded)
            except Exception:
                continue

    try:
        explanation_text = generate_question_explanation(
            question.statement, alts, correct_letter, api_key, images_b64
        )
        
        # 4. Salva no Banco (Cache)
        QuestionExplanation.objects.create(question=question, content=explanation_text)
        
        # 5. Debita Cota
        usage.count += 1
        usage.save()

        return {
            "content": explanation_text, 
            "cached": False, 
            "remaining": total_allowed - usage.count
        }
    except Exception as e:
        return {"error": f"Erro ao gerar explicação: {str(e)}"}


def xp_per_correct(session_type: str) -> int:
    """Retorna XP por acerto conforme tipo de sessão."""
    return 15 if session_type == 'simulated' else 10
