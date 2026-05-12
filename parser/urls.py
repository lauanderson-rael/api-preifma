from django.urls import path
from . import views

app_name = "parser"

urlpatterns = [
    path("landing/", views.landing, name="landing"), # Rota interna da landing
    path("", views.index, name="index"),
    path("process/", views.process, name="process"),
    path("save-to-db/", views.save_to_db_view, name="save_to_db"),
    path("ingest-zip/", views.ingest_zip_view, name="ingest_zip"),
]
