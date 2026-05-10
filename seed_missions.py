import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from game.models import Mission

def seed_missions():
    missions = [
        # --- Nível Básico (Aquecimento) ---
        {'title': 'Primeiros Passos', 'description': 'Responda 5 questões hoje', 'xp_reward': 50, 'goal_type': 'answer_questions', 'goal_value': 5},
        {'title': 'Mestre da Precisão', 'description': 'Acerte 3 questões hoje', 'xp_reward': 100, 'goal_type': 'correct_answers', 'goal_value': 3},
        {'title': 'Iniciante Dedicado', 'description': 'Responda 8 questões', 'xp_reward': 80, 'goal_type': 'answer_questions', 'goal_value': 8},
        {'title': 'Lógica Afiada', 'description': 'Acerte 5 questões hoje', 'xp_reward': 120, 'goal_type': 'correct_answers', 'goal_value': 5},
        {'title': 'Foco Total', 'description': 'Responda 10 questões', 'xp_reward': 150, 'goal_type': 'answer_questions', 'goal_value': 10},

        # --- Nível Intermediário (Consistência) ---
        {'title': 'Explorador de Conteúdo', 'description': 'Responda 15 questões', 'xp_reward': 200, 'goal_type': 'answer_questions', 'goal_value': 15},
        {'title': 'Gênio da Matemática', 'description': 'Acerte 8 questões', 'xp_reward': 180, 'goal_type': 'correct_answers', 'goal_value': 8},
        {'title': 'Sábio do Português', 'description': 'Responda 12 questões', 'xp_reward': 140, 'goal_type': 'answer_questions', 'goal_value': 12},
        {'title': 'Sniper do IFMA', 'description': 'Acerte 10 questões', 'xp_reward': 250, 'goal_type': 'correct_answers', 'goal_value': 10},
        {'title': 'Rotina de Estudos', 'description': 'Responda 18 questões', 'xp_reward': 220, 'goal_type': 'answer_questions', 'goal_value': 18},
        {'title': 'Acerto de Contas', 'description': 'Acerte 12 questões', 'xp_reward': 260, 'goal_type': 'correct_answers', 'goal_value': 12},
        {'title': 'Leitura Dinâmica', 'description': 'Responda 14 questões de Português', 'xp_reward': 160, 'goal_type': 'answer_questions', 'goal_value': 14},
        {'title': 'Calculadora Humana', 'description': 'Acerte 9 questões de Matemática', 'xp_reward': 200, 'goal_type': 'correct_answers', 'goal_value': 9},

        # --- Nível Avançado (Maratona) ---
        {'title': 'Maratona de Estudos', 'description': 'Responda 25 questões hoje', 'xp_reward': 400, 'goal_type': 'answer_questions', 'goal_value': 25},
        {'title': 'Perfeccionista', 'description': 'Acerte 20 questões', 'xp_reward': 500, 'goal_type': 'correct_answers', 'goal_value': 20},
        {'title': 'Tanque de Conhecimento', 'description': 'Responda 30 questões', 'xp_reward': 450, 'goal_type': 'answer_questions', 'goal_value': 30},
        {'title': 'Elite do Seletivo', 'description': 'Acerte 15 questões', 'xp_reward': 350, 'goal_type': 'correct_answers', 'goal_value': 15},
        {'title': 'Resiliência', 'description': 'Responda 22 questões', 'xp_reward': 320, 'goal_type': 'answer_questions', 'goal_value': 22},

        # --- Recompensas Especiais (Bônus de IA) ---
        {'title': 'Curiosidade Ativada', 'description': 'Responda 10 questões para bônus de IA', 'xp_reward': 150, 'goal_type': 'answer_questions', 'goal_value': 10, 'special_reward': 'AI_LIMIT'},
        {'title': 'Investigador Digital', 'description': 'Acerte 7 questões para bônus de IA', 'xp_reward': 180, 'goal_type': 'correct_answers', 'goal_value': 7, 'special_reward': 'AI_LIMIT'},
        {'title': 'Buscador de Respostas', 'description': 'Responda 20 questões para bônus de IA', 'xp_reward': 300, 'goal_type': 'answer_questions', 'goal_value': 20, 'special_reward': 'AI_LIMIT'},
        
        # --- Missões Temáticas ---
        {'title': 'Desafio de Domingo', 'description': 'Responda 12 questões', 'xp_reward': 200, 'goal_type': 'answer_questions', 'goal_value': 12},
        {'title': 'Madrugada Estudantil', 'description': 'Acerte 6 questões', 'xp_reward': 150, 'goal_type': 'correct_answers', 'goal_value': 6},
        {'title': 'Reta Final', 'description': 'Responda 40 questões', 'xp_reward': 700, 'goal_type': 'answer_questions', 'goal_value': 40},
        {'title': 'Conhecimento é Poder', 'description': 'Acerte 25 questões', 'xp_reward': 600, 'goal_type': 'correct_answers', 'goal_value': 25},
    ]

    for m_data in missions:
        obj, created = Mission.objects.update_or_create(
            title=m_data['title'],
            defaults=m_data
        )
        if created:
            print(f"Missão criada: {obj.title}")
        else:
            print(f"Missão atualizada: {obj.title}")

if __name__ == '__main__':
    seed_missions()
