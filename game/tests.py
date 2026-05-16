from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from game.models import StudySession, Answer
from exams.models import Exam, Question
from accounts.level_utils import level_progress

User = get_user_model()

class GamificationAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='password123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.exam = Exam.objects.create(name="Prova Teste", year=2024, type="integrado")
        self.question = Question.objects.create(
            exam=self.exam,
            statement="Quanto é 2+2?",
            subject="matematica",
            number=1
        )

    def test_xp_progression_via_api(self):
        """Testa se o XP sobe ao finalizar a sessão via endpoint da API"""
        session = StudySession.objects.create(user=self.user, type='quick')
        Answer.objects.create(
            user=self.user,
            session=session,
            question=self.question,
            is_correct=True,
            response_time=10
        )
        
        url = reverse('session-finish', kwargs={'pk': session.pk})
        response = self.client.post(url, {}) 
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar se o XP subiu no banco 
        self.user.refresh_from_db()
        self.assertEqual(self.user.xp, 10)

    def test_level_up_logic(self):
        """Testa a lógica matemática de subida de nível em level_utils"""
        data = level_progress(120)
        self.assertEqual(data['level'], 2)
        
        data = level_progress(50)
        self.assertEqual(data['level'], 1)
