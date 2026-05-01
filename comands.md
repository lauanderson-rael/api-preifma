pip install -r requirements.txt
export GEMINI_API_KEY="AIzaSyBSy_8yd9ougoOWcW0UTNHzPH8-vsXIbPg"
python manage.py runserver  

chave gratis
https://aistudio.google.com/app/apikey

## projeto 
Subir o banco: No terminal, rode:

bash
docker-compose up -d
Isso vai subir o Postgres em segundo plano.

Rodar o Django localmente: Agora você pode rodar o Django normalmente no seu terminal (com seu venv ativo):

bash
python manage.py makemigrations game
python manage.py migrate
python manage.py runserver

python manage.py createsuperuser

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
python3 manage.py shell
exit()

python3 manage.py runserver [IP_ADDRESS]

## banco de dados
- se mudar os models: python3 manage.py makemigrations 
- aplicar as mudanças no banco: python3 manage.py migrate
