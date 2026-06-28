from django.db import models

class Attachment(models.Model):
    """Biblioteca unificada de mídias (Texto ou Imagem) para reaproveitamento."""
    TYPE_CHOICES = [
        ('text', 'Texto de Apoio'), 
        ('image', 'Imagem'),
    ]
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="Tipo de anexo")
    label = models.CharField(max_length=100, blank=True, null=True,verbose_name="Rótulo", help_text="Ex: Texto 1, Trecho 2...")
    content = models.TextField(blank=True, null=True, verbose_name="Conteúdo de Texto", help_text="Usado se for tipo 'text'")
    file = models.ImageField(upload_to='questions/', blank=True, null=True, verbose_name="Arquivo de Imagem", help_text="Usado se for tipo 'image'")
    hash = models.CharField(max_length=64, unique=True)

    def __str__(self):
        if self.type == 'text':
            return f"[TEXTO] {self.content[:50]}..."
        return f"[IMAGEM] {self.hash[:10]}"

    class Meta:
        verbose_name = 'Anexo (Biblioteca)'
        verbose_name_plural = 'Anexos (Biblioteca)'


class Exam(models.Model):
    TYPE_CHOICES = [
        ('integrado', 'Técnico Integrado'),
        ('subsequente', 'Técnico Subsequente'),
        ('concomitante', 'Técnico Concomitante'),
    ]
    name = models.CharField(max_length=200, verbose_name="Nome")
    year = models.IntegerField(verbose_name="Ano")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Tipo de Curso")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Prova'
        verbose_name_plural = 'Provas'


class Question(models.Model):
    SUBJECT_CHOICES = [
        ('portugues', 'Português'),
        ('matematica', 'Matemática'),
    ]
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions', verbose_name="Prova")
    number = models.IntegerField(default=0, verbose_name="Número da Questão")
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES, verbose_name="Matéria")
    statement = models.TextField(verbose_name="Enunciado da Questão")

    attachments = models.ManyToManyField(Attachment(), through='QuestionAttachment', related_name='questions')

    def __str__(self):
        return f"Q{self.number} - {self.subject} ({self.exam.name})"

    class Meta:
        verbose_name = 'Questão'
        verbose_name_plural = 'Questões'


class QuestionAttachment(models.Model):
    """Tabela de Ligação: Questão <-> Anexo (Mantém a ordem da prova)"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    attachment = models.ForeignKey(Attachment,verbose_name="Anexo", on_delete=models.CASCADE)
    order = models.IntegerField(default=1, verbose_name="Ordem")

    class Meta:
        ordering = ['order']
        verbose_name = 'Vínculo de Anexo'
        verbose_name_plural = 'Vínculos de Anexo'


class Alternative(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='alternatives', verbose_name="Questão")
    letter = models.CharField(max_length=2, verbose_name="Letra")
    text = models.TextField(verbose_name="Texto")
    is_correct = models.BooleanField(default=False, verbose_name="Correta?")

    def __str__(self):
        return f"{self.letter}) {self.text[:30]}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['question'],
                condition=models.Q(is_correct=True),
                name='exams_unique_correct_alt_per_question'
            )
        ]
        verbose_name = 'Alternativa'
        verbose_name_plural = 'Alternativas'


class QuestionExplanation(models.Model):
    """Cache de explicações geradas pela IA para uma questão."""
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='explanation')
    content = models.TextField(help_text="Texto da explicação gerado pela IA")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Explicação Q{self.question.number} ({self.question.exam.name})"

    class Meta:
        verbose_name = 'Explicação de Questão'
        verbose_name_plural = 'Explicações de Questões'
