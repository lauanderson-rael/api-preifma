import random
import base64
from datetime import date
from django.conf import settings
from .models import UserAIDailyUsage, Mission, UserMission
from exams.models import Question, QuestionExplanation
from parser.services import generate_question_explanation

def get_or_create_daily_missions(user):
    """Sorteia 3 missões para o dia de hoje."""  
    today = date.today() 
    existing = UserMission.objects.filter(user=user, date=today)  

    if existing.exists():
        return existing
    
    all_missions = list(Mission.objects.all())
    if len(all_missions) < 3:
        selected = all_missions 
    else:
        selected = random.sample(all_missions, 3)
        
    new_missions = []
    for m in selected:
        new_missions.append(
            UserMission.objects.create(user=user, mission=m, date=today)
        )
    return new_missions


def get_or_generate_explanation(user, question_id: int) -> dict:
    """ Retorna a explicação de uma questão."""
    try:
        question = Question.objects.get(id=question_id)
    except Question.DoesNotExist:
        return {"error": "Questão não encontrada."}

    # 1. Checa Cota Diária
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
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        return {"error": "Serviço de IA não configurado no servidor."}

    alts = [{"letter": a.letter, "text": a.text} for a in question.alternatives.all()]
    correct = question.alternatives.filter(is_correct=True).first()
    correct_letter = correct.letter if correct else "?"

    images_b64 = []
    for att in question.attachments.all(): 
        if att.file:
            try:
                with att.file.open('rb') as f:
                    encoded = base64.b64encode(f.read()).decode('utf-8')
                    images_b64.append(encoded)
            except Exception:
                continue

    try: 
        explanation_text = generate_question_explanation(question.statement, alts, correct_letter, api_key, images_b64)
        QuestionExplanation.objects.create(question=question, content=explanation_text)
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
