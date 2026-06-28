from django.db import models
from accounts.models import User
from exams.models import Question, Alternative 

class StudySession(models.Model):
    SESSION_TYPES = [
        ('quick', 'Partida Rápida'),
        ('simulated', 'Simulado'),
        ('practice', 'Prática Livre'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Aluno")
    type = models.CharField(max_length=20, choices=SESSION_TYPES, verbose_name="Tipo de estudo")
    total_questions = models.PositiveIntegerField(default=0, verbose_name="Total de questões")
    correct_answers = models.PositiveIntegerField(default=0, verbose_name="Respostas corretas")
    xp_gained = models.PositiveIntegerField(default=0, verbose_name="XP ganho")
    duration_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Duração total da sessão em segundos",
        verbose_name="Duração da Sessão (s)"
    )
    finished = models.BooleanField(default=False, verbose_name="finalizada?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data de criação")

    @property
    def accuracy_percentage(self):
        """Percentual de acerto da sessão."""
        if self.total_questions == 0:
            return 0
        return round((self.correct_answers / self.total_questions) * 100, 2)

    def __str__(self):
        return f"Sessão {self.id} - {self.user.username}"
    
    class Meta:
        verbose_name = "Sessão de Estudo"
        verbose_name_plural = "Sessões de Estudo"


class Answer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Aluno")
    session = models.ForeignKey(StudySession, on_delete=models.CASCADE, related_name='answers', verbose_name="Sessão de estudo")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Questão")

    selected_alternative = models.ForeignKey(
        Alternative,
        on_delete=models.SET_NULL,
        null=True,
        related_name='answers',
        verbose_name="Alternativa escolhida",
    )

    correct_letter = models.CharField(
        max_length=2,
        default='',
        verbose_name="Letra correta",
        help_text="Letra correta no momento em que o aluno respondeu"
    )

    is_correct = models.BooleanField(verbose_name="Está correto?")
    response_time = models.PositiveIntegerField(help_text="Tempo em segundos", verbose_name="Tempo de Resposta (s)")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'session', 'question')
        verbose_name = "Resposta do Aluno"
        verbose_name_plural = "Respostas dos Alunos"


class SubjectProgress(models.Model):
    SUBJECT_CHOICES = [
        ('portugues', 'Português'),
        ('matematica', 'Matemática'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Aluno")
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, verbose_name="Matéria")
    questions_answered = models.PositiveIntegerField(default=0, verbose_name="Questões respondidas")
    correct_answers = models.PositiveIntegerField(default=0, verbose_name="Respostas corretas")

    @property
    def accuracy_percentage(self):
        if self.questions_answered == 0:
            return 0
        return round((self.correct_answers / self.questions_answered) * 100, 2)

    def __str__(self):
        return f"{self.user.username} - {self.subject}: {self.accuracy_percentage}%"

    class Meta:
        unique_together = ('user', 'subject')
        verbose_name = "Progresso na Matéria"
        verbose_name_plural = "Progresso nas Matérias"


class Mission(models.Model):
    title = models.CharField(max_length=200, verbose_name="Título da Missão")
    description = models.TextField(verbose_name="Descrição")
    XP_CHOICES = [
        (50, '50 XP'),
        (80, '80 XP'),
        (100, '100 XP'),
        (120, '120 XP'),
        (150, '150 XP'),
        (200, '200 XP'),
    ]
    xp_reward = models.PositiveIntegerField(choices=XP_CHOICES, default=100, verbose_name="Recompensa de XP")
    GOAL_TYPES = [
        ('answer_questions', 'Responder Questões'),
        ('correct_answers', 'Acertar Questões'),
    ]
    
    SUBJECT_CHOICES = [
        (None, 'Todas as Matérias (Geral)'),
        ('portugues', 'Português'),
        ('matematica', 'Matemática'),
    ]

    goal_type = models.CharField(max_length=50, choices=GOAL_TYPES, verbose_name="Tipo de Meta")
    goal_value = models.PositiveIntegerField(verbose_name="Quantidade Alvo")
    goal_subject = models.CharField(
        max_length=20, 
        choices=SUBJECT_CHOICES,
        blank=True, 
        null=True, 
        verbose_name="Matéria Específica",
        help_text="Se vazio, conta todas as matérias." 
    )
    REWARD_CHOICES = [
        ('AI_LIMIT', '+2 Explicações com IA'), 
    ]

    special_reward = models.CharField(
        max_length=50, 
        choices=REWARD_CHOICES,
        blank=True, 
        null=True, 
        verbose_name="Bônus Especial",
        help_text="Recompensa especial além do XP (opcional)."
    )
    
    class Meta:
        verbose_name = "Missão"
        verbose_name_plural = "Missões"


class UserMission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Aluno")
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE, verbose_name="Missão")
    progress = models.PositiveIntegerField(default=0, verbose_name="Progresso")
    completed = models.BooleanField(default=False, verbose_name="Missão completa?")
    xp_claimed = models.BooleanField(default=False, verbose_name="Recompensa recolhida?", help_text="XP da missão já foi creditado ao usuário")
    date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'mission', 'date')
        verbose_name = "Missão do Aluno"  
        verbose_name_plural = "Missões dos Alunos"


class UserAIDailyUsage(models.Model):
    """Controle de uso diário de explicações por IA."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_usage', verbose_name="Aluno")
    date = models.DateField(auto_now_add=True, verbose_name="Data")
    count = models.PositiveIntegerField(default=0, verbose_name="quantidade")
    bonus_limit = models.PositiveIntegerField(default=0, help_text="Bônus extra de cota ganho em missões hoje")

    class Meta:
        unique_together = ('user', 'date')
        verbose_name = 'Uso Diário de IA'
        verbose_name_plural = 'Usos Diários de IA'
