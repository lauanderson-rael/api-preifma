import os
import json
import zipfile
import tempfile
import shutil
from django.core.management.base import BaseCommand
from django.core.management import call_command
from exams.services import save_exam_to_db

class Command(BaseCommand):
    help = 'Popula o banco de dados com fixtures e processa os ZIPs das provas.'

    def handle(self, *args, **options):
        # 1. Carregar Fixture Base
        self.stdout.write(self.style.SUCCESS('--- Iniciando Carga de Dados Base ---'))
        try:
            call_command('loaddata', 'fixtures/base.json')
            self.stdout.write(self.style.SUCCESS('Fixture base.json carregada com sucesso!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao carregar fixture: {e}'))

        # 2. Processar ZIPs de Provas
        self.stdout.write(self.style.SUCCESS('\n--- Iniciando Processamento de Provas (ZIPs) ---'))
        backup_dir = 'fixtures/backups'
        
        if not os.path.exists(backup_dir):
            self.stdout.write(self.style.WARNING(f'Pasta {backup_dir} não encontrada. Pulando ingestão de ZIPs.'))
            return

        zip_files = [f for f in os.listdir(backup_dir) if f.endswith('.zip')]
        
        if not zip_files:
            self.stdout.write(self.style.WARNING('Nenhum arquivo .zip encontrado em fixtures/backups/.'))
            return

        for zip_name in zip_files:
            zip_path = os.path.join(backup_dir, zip_name)
            self.stdout.write(f'Processando: {zip_name}...')
            
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    # Extrair
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(tmp_dir)

                    # Localizar prova.json
                    json_path = None
                    base_extract_path = tmp_dir
                    for root, dirs, files in os.walk(tmp_dir):
                        if 'prova.json' in files:
                            json_path = os.path.join(root, 'prova.json')
                            base_extract_path = root
                            break

                    if not json_path:
                        self.stdout.write(self.style.ERROR(f'  [!] prova.json não encontrado no ZIP {zip_name}'))
                        continue

                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Salvar no banco
                    result = save_exam_to_db(data, base_path=base_extract_path)
                    
                    if "error" in result:
                        self.stdout.write(self.style.ERROR(f'  [!] Erro ao salvar {zip_name}: {result["error"]}'))
                    else:
                        self.stdout.write(self.style.SUCCESS(f'  [OK] {zip_name} importado: {result.get("exam_name", "")}'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [!] Falha crítica ao processar {zip_name}: {e}'))

        self.stdout.write(self.style.SUCCESS('\n--- Processo Finalizado com Sucesso! ---'))
