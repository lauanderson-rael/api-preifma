# PREIFMA API

A **PREIFMA API** é o coração do ecossistema PreIFMA — uma plataforma gamificada desenvolvida como TCC para auxiliar candidatos a ingressarem no Seletivo Técnico do IFMA. Esta API fornece todos os recursos necessários para o funcionamento do aplicativo móvel, desde a gestão de questões até o sistema de recompensas.

## 🛠 Tecnologias Principais
*   **Framework:** Django 5.x & Django REST Framework (DRF)
*   **Banco de Dados:** PostgreSQL (via Docker)
*   **IA & Parsing:** Google Gemini API, PyMuPDF (fitz) e BeautifulSoup
*   **Autenticação:** JWT (Simple JWT)
*   **Ambiente:** Python 3.12+

---

## 🚀 Como Executar o Projeto

### 1. Requisitos Prévios
*   Docker e Docker Compose instalados.
*   Python 3.12+ e `venv`.

### 2. Configuração do Banco de Dados
O banco de dados roda em um container Docker para facilitar o setup:
```bash
docker compose up -d db
```

### 3. Ambiente Virtual e Dependências
```bash
# Crie e ative o venv
python -m venv venv
source venv/bin/activate  # Linux/macOS

# Instale as dependências
pip install -r requirements.txt
```

### 4. Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto seguindo este modelo:
```ini
DB_NAME=preifma_db
DB_USER=preifma_user
DB_PASSWORD=admin123
DB_HOST=localhost
DB_PORT=5432
# uma das duas é opcional
GEMINI_API_KEY=sua_chave_aqui
OPENROUTER_API_KEY=sua_chave_aqui
```

### 5. Migrations e Execução
```bash
python manage.py migrate
python manage.py runserver
```

---

## 📡 Principais Endpoints (Resumo)

### 🔐 Autenticação & Perfil
*   `POST /api/auth/register/`: Registro de novos alunos.
*   `POST /api/auth/login/`: Login e obtenção de tokens JWT.
*   `GET /api/auth/me/`: Dados básicos do usuário logado.
*   `GET /api/users/profile/`: Perfil detalhado com XP e Nível.
*   `GET /api/users/stats/`: Estatísticas de desempenho (precisão, total de questões).

### 🎮 Gamificação & Sessões
*   `GET /api/dashboard/`: Resumo para a home do App (Missões, XP, Streak).
*   `POST /api/sessions/start/`: Inicia uma nova sessão de estudos (Quick ou Simulado).
*   `POST /api/sessions/<id>/answers/`: Envia a resposta de uma questão.
*   `POST /api/sessions/<id>/finish/`: Finaliza a sessão (O backend calcula XP e duração automaticamente).
*   `GET /api/missions/daily/`: Lista as missões diárias do usuário.
*   `GET /api/achievements/`: Lista todas as conquistas disponíveis.

### 📚 Provas & Questões
*   `GET /api/exams/`: Lista de provas disponíveis.
*   `GET /api/questions/`: Banco de questões com filtros por matéria e prova.

---

## 📤 Ingestão de Provas (Parser)
O sistema possui ferramentas para transformar provas em dados estruturados.

### 1. Interface Web (IA)
Acesse `http://localhost:8000/` para usar o Parser Inteligente.

### 2. Ingestão via API (ZIP)
*   **Endpoint:** `POST /ingest-zip/` 
*   **Payload:** `multipart/form-data` (campo `zip_file`)
*   **Requisito:** O ZIP deve conter `prova.json` e uma pasta `images/`.
