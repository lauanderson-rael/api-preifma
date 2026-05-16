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

### Requisitos Prévios
*   Docker e Docker Compose instalados.

### 1. Clonar o Repositório
```bash
git clone git@github.com:lauanderson-rael/preifma_api.git
cd preifma_api
```

### 2. Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto seguindo este modelo:
```ini
# Banco de Dados
DB_NAME=preifma_db
DB_USER=preifma_user
DB_PASSWORD=admin123
DB_HOST=localhost
DB_PORT=5432

# OpenRouter (IA) 
OPENROUTER_API_KEY=sua_chave_aqui
OPENROUTER_PARSER_MODEL=nome_do_modelo
OPENROUTER_EXPLAINER_MODEL=nome_do_modelo 
OPENROUTER_SITE_URL=url_do_seu_site 
```

### 3. 🐳 Instalação via Docker
Se você tem o Docker instalado, pode subir o ambiente completo (API + Banco) com poucos comandos:

```bash
# 1. Subir os containers
docker compose up -d --build

# 2. Configurar e popular o banco
docker exec -it preifma_api python manage.py makemigrations
docker exec -it preifma_api python manage.py migrate
docker exec -it preifma_api python manage.py seed_db

# (Opcional) Resetar senhas para o padrão
docker exec -it preifma_api python manage.py shell -c "from accounts.models import User; u = User.objects.get(username='admin'); u.set_password('admin123'); u.save()"
docker exec -it preifma_api python manage.py shell -c "from accounts.models import User; u = User.objects.get(username='aluno_teste'); u.set_password('aluno123'); u.save()"
```
---

### 🔑 Credenciais de Teste
Após rodar o `seed_db` e os comandos de reset, utilize as seguintes credenciais:

| Perfil | Usuário (E-mail) | Senha |
| :--- | :--- | :--- |
| **Administrador** | `admin@preifma.com` | `admin123` |
| **Aluno Teste** | `aluno@preifma.com` | `aluno123` |

Onde testar:
* Interface Web: http://localhost:8000
* Documentação da API: http://localhost:8000/api/docs/
* Admin: http://localhost:8000/admin/
* Parser: http://localhost:8000/parser/ 
---

## 📡 Principais Endpoints (Resumo)

### 🔐 Autenticação & Perfil
*   `POST /api/auth/register/`: Registro de novos alunos.
*   `POST /api/auth/login/`: Login e obtenção de tokens JWT.
*   `GET /api/auth/me/`: Dados básicos do usuário logado.
*   `GET /api/users/profile/`: Perfil detalhado com XP e Nível.
*   `GET /api/users/stats/`: Estatísticas de desempenho (precisão, total de questões).

### 🎮 Gamificação & Sessões
*   `GET /api/dashboard/`: Resumo para a home do App (Missões, XP, Cota de IA).
*   `POST /api/sessions/start/`: Inicia uma nova sessão de estudos (Quick ou Simulado).
*   `POST /api/sessions/<id>/answers/`: Envia a resposta de uma questão.
*   `POST /api/sessions/<id>/finish/`: Finaliza a sessão (O backend calcula XP e duração automaticamente).
*   `GET /api/missions/daily/`: Lista as missões diárias do usuário.

### 📚 Provas & Questões
*   `GET /api/exams/`: Lista de provas disponíveis.
*   `GET /api/questions/`: Banco de questões com filtros por matéria e prova.
*   `GET /api/questions/<id>/explain/`: Obtém explicação detalhada via IA. 

---

## 🛠️ Recursos Técnicos & Documentação
O projeto oferece ferramentas de processamento inteligente e documentação técnica completa para desenvolvedores.

### 1. Parser de Provas (IA)
Acesse `/parser/` para usar o Parser Inteligente.

### 2. Documentação da API
Para integração com clientes ou consulta técnica:  
- **Swagger UI**: acesse `/api/docs/`.  
- **Redoc**: acesse `/api/redoc/`. 
### 3. Arquitetura de IA (OpenRouter)
O sistema utiliza uma camada de abstração para modelos de linguagem através da **OpenRouter**, permitindo trocar o provedor de IA via `.env` sem alteração de código:
- **Parser**: Otimizado para modelos de raciocínio (ex: `google/gemini-3-flash-preview`).
- **Explicações**: Otimizado para modelos didáticos e econômicos (ex: `google/gemini-2.0-flash-001`).

--- 

### 👨‍💻 Autor
Desenvolvido por **Lauanderson Rael** como parte do Trabalho de Conclusão de Curso (TCC).

---
