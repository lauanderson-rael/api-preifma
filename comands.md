pip install -r requirements.txt
export GEMINI_API_KEY="xxxxxxx" 
python manage.py runserver  

chave gratis
https://aistudio.google.com/app/apikey

## projeto 
Subir o banco: No terminal, rode:
docker-compose up -d

 
## SuperUser
Email: lauanderson38@gmail.com  
Username: lauanderson
Nome: Lauanderson Rael
Password: admin123

E-mail (Login): admin@admin.com
Senha: admin123
Nome: Lauanderson Rael 
  
## limpar banco
python manage.py shell

from django.db import connection
from game.models import Exam, Question, Alternative, Attachment, QuestionAttachment

QuestionAttachment.objects.all().delete()
Attachment.objects.all().delete()
Alternative.objects.all().delete()
Question.objects.all().delete()
Exam.objects.all().delete()

with connection.cursor() as cursor:
    for table in ['game_questionattachment', 'game_attachment', 'game_alternative', 'game_question', 'game_exam']:
        cursor.execute(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1;")

print("✅ Banco zerado e IDs reiniciados!")
exit()


## comands
python3 manage.py runserver [IP_ADDRESS]

## banco de dados
- se mudar os models: python3 manage.py makemigrations 
- aplicar as mudanças no banco: python3 manage.py migrate
