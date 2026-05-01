from django.db.models import Q, Sum
from .models import Question, Stage, UserProgress, AIUsage
from django.contrib.auth import get_user_model
import os
from google import genai

User = get_user_model()

def get_stage_questions(user, exam_type, stage_number):
    """
    Retorna as questões para uma determinada fase e tipo de prova.
    Se o usuário já completou pelo menos 1 ciclo (10 fases), entra no modo infinito (10 questões).
    Caso contrário, segue a distribuição linear das 10 fases.
    """
    progress, _ = UserProgress.objects.get_or_create(user=user, exam_type=exam_type)

    if progress.cycles_completed > 0:
        # Modo aprendizado contínuo (Infinito) após o 1º ciclo
        # Sempre 10 questões aleatórias do tipo de prova atual do usuário
        return Question.objects.filter(
            exam__type=exam_type
        ).order_by('?')[:10]
    
    # Modo Linear (Fases 1 a 10 do primeiro ciclo)
    try:
        # Garante que não passamos da fase 10 no modo linear
        effective_stage = min(stage_number, 10)
        stage = Stage.objects.get(exam_type=exam_type, stage_number=effective_stage)
    except Stage.DoesNotExist:
        return Question.objects.none()

    # Buscar questões de Português
    port_questions = Question.objects.filter(
        exam__type=exam_type,
        subject__icontains='Portugu'
    ).order_by('?')[:stage.portuguese_count]

    # Buscar questões de Matemática
    math_questions = Question.objects.filter(
        exam__type=exam_type,
        subject__icontains='Matem'
    ).order_by('?')[:stage.math_count]

    questions = list(port_questions) + list(math_questions)
    
    import random
    random.shuffle(questions)
    
    return questions

def complete_stage(user, exam_type, stage_number):
    """
    Atualiza o progresso do usuário ao completar uma fase.
    """
    progress, created = UserProgress.objects.get_or_create(
        user=user,
        exam_type=exam_type
    )

    if stage_number == progress.current_stage:
        # Se for o primeiro ciclo e terminou a fase 10
        if stage_number == 10 and progress.cycles_completed == 0:
            progress.cycles_completed += 1
            progress.current_stage = 11 # Entra no modo infinito
        else:
            progress.current_stage += 1
        
        if progress.current_stage > progress.max_stage:
            progress.max_stage = progress.current_stage
        
        progress.save()
    
    return progress

def explain_question_with_ai(user, question_id):
    """
    Usa o Gemini para explicar uma questão.
    """
    try:
        question = Question.objects.get(id=question_id)
        alternatives = question.alternatives.all()
        correct_alt = alternatives.filter(is_correct=True).first()
        
        # Preparar o contexto para a IA
        alt_text = "\n".join([f"{a.letter}) {a.text}" for a in alternatives])
        prompt = f"""
        Você é um professor tutor do IFMA. Explique de forma didática e curta a seguinte questão:
        
        Enunciado: {question.statement}
        
        Alternativas:
        {alt_text}
        
        A alternativa correta é a {correct_alt.letter if correct_alt else 'Desconhecida'}.
        
        Por que ela está correta e por que as outras estão incorretas?
        """
        
        # Chamar a API do Gemini
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return "Erro: GEMINI_API_KEY não configurada."
            
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        explanation = response.text
        
        # Registrar o uso
        AIUsage.objects.create(
            user=user,
            question=question,
            ai_response=explanation,
            tokens_used=0 # Gemini não retorna tokens da mesma forma que OpenAI facilmente aqui
        )
        
        return explanation
    except Exception as e:
        return f"Erro ao gerar explicação: {str(e)}"

def get_weekly_ranking():
    """
    Retorna os top 10 usuários baseados em XP.
    """
    return User.objects.all().order_by('-xp')[:10]
