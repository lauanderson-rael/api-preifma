from django.db import models
from accounts.models import User
from exams.models import Question, Alternative 

class StudySession(models.Model):
    SESSION_TYPES = [
        ('quick', 'Partida Rápida'),
        ('simulated', 'Simulado'),
        ('practice', 'Prática Livre'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=SESSION_TYPES)
    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    xp_gained = models.PositiveIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(
        default=0,
        help_text="Duração total da sessão em segundos"
    )
    finished = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def accuracy_percentage(self):
        """Percentual de acerto da sessão."""
        if self.total_questions == 0:
            return 0
        return round((self.correct_answers / self.total_questions) * 100, 2)

    def __str__(self):
        return f"Sessão {self.id} - {self.user.username}"


class Answer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    session = models.ForeignKey(StudySession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)

    selected_alternative = models.ForeignKey(
        Alternative,
        on_delete=models.SET_NULL,
        null=True,
        related_name='answers',
        help_text="Alternativa escolhida pelo aluno"
    )

    correct_letter = models.CharField(
        max_length=2,
        default='',
        help_text="Letra correta no momento em que o aluno respondeu"
    )

    is_correct = models.BooleanField()
    response_time = models.PositiveIntegerField(help_text="Tempo em segundos")
    created_at = models.DateTimeField(auto_now_add=True)


class SubjectProgress(models.Model):
    SUBJECT_CHOICES = [
        ('portugues', 'Português'),
        ('matematica', 'Matemática'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES)
    questions_answered = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)

    @property
    def accuracy_percentage(self):
        if self.questions_answered == 0:
            return 0
        return round((self.correct_answers / self.questions_answered) * 100, 2)

    def __str__(self):
        return f"{self.user.username} - {self.subject}: {self.accuracy_percentage}%"

    class Meta:
        unique_together = ('user', 'subject')


class Mission(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    XP_CHOICES = [
        (50, '50 XP'),
        (80, '80 XP'),
        (100, '100 XP'),
        (120, '120 XP'),
        (150, '150 XP'),
        (200, '200 XP'),
    ]
    xp_reward = models.PositiveIntegerField(choices=XP_CHOICES, default=100)
    GOAL_TYPES = [
        ('answer_questions', 'Responder Questões'),
        ('correct_answers', 'Acertar Questões'),
    ]
    
    SUBJECT_CHOICES = [
        (None, 'Todas as Matérias (Geral)'),
        ('portugues', 'Português'),
        ('matematica', 'Matemática'),
    ]

    goal_type = models.CharField(max_length=50, choices=GOAL_TYPES)
    goal_value = models.PositiveIntegerField()
    goal_subject = models.CharField(
        max_length=20, 
        choices=SUBJECT_CHOICES,
        blank=True, 
        null=True, 
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
        help_text="Recompensa especial além do XP (opcional)."
    )


class UserMission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    mission = models.ForeignKey(Mission, on_delete=models.CASCADE)
    progress = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    xp_claimed = models.BooleanField(default=False, help_text="XP da missão já foi creditado ao usuário")
    date = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'mission', 'date')


class UserAIDailyUsage(models.Model):
    """Controle de uso diário de explicações por IA."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_usage')
    date = models.DateField(auto_now_add=True)
    count = models.PositiveIntegerField(default=0)
    bonus_limit = models.PositiveIntegerField(default=0, help_text="Bônus extra de cota ganho em missões hoje")

    class Meta:
        unique_together = ('user', 'date')
        verbose_name = 'Uso Diário de IA'
        verbose_name_plural = 'Usos Diários de IA'
