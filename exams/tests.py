from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from exams.models import Exam, Question

User = get_user_model()

class ExamAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@test.com',
            password='password123'
        )
        self.client.force_authenticate(user=self.user)
        self.exam = Exam.objects.create(name="Simulado IFMA", year=2023, type="integrado")
        
        # Criar 35 questões 
        for i in range(35):
            Question.objects.create(
                exam=self.exam,
                statement=f"Questão {i}",
                subject="portugues" if i < 15 else "matematica",
                number=i+1
            )

    def test_simulated_exam_endpoint(self):
        """Testa se o simulado retorna 30 questões e numeração sequencial"""
        url = reverse('question-simulated')
        response = self.client.get(url, {'type': 'integrado'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data['results']), 30)
        
        # Verificar se o campo 'number' está em ordem (1, 2, 3... 
        numbers = [q['number'] for q in data['results']]
        self.assertEqual(numbers, list(range(1, 31))) 
