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
git clone git@github.com:lauanderson-rael/api-preifma.git
cd api-preifma
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

# Resend (Serviço de Email) 
RESEND_API_KEY=re_sua_chave_aqui 
DEFAULT_FROM_EMAIL="Pré-IFMA <onboarding@resend.dev>"
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

### Como Testar o Parser de Provas e Gabaritos

A plataforma disponibiliza uma interface visual amigável (Web UI) para que o administrador possa acompanhar todo o fluxo de ingestão, realizar correções de qualidade e homologar os dados das provas e gabaritos extraídos por IA.
 
#### Passo 1: Ingestão de Prova via PDF
1. Certifique-se de que os contêineres estão rodando localmente (`docker compose up -d`).
2. Acesse a interface do Parser em seu navegador: **`http://localhost:8000/parser/`**.
3. Realize o login com as credenciais de **Administrador** (`admin@preifma.com` / `admin123`).
4. Na tela de processamento, realize o upload dos arquivos de amostra fornecidos diretamente na **raiz do repositório**:
   * **`prova_pdf`**: Faça o upload do arquivo contido em `2025-prova-integrado.pdf`.
   * **`gabarito_pdf`**: Faça o upload do arquivo contido em `2025-gabarito-integrado.pdf`. 
5. Clique em **"Começar Processamento"**. 
 
#### Passo 2: Interface de Edição e Curadoria Humana
Após o processamento concluído, o sistema redirecionará você para a **Interface de Revisão Curatorial**:
* **Correção Tipográfica:** Navegue pelas 30 questões capturadas pela IA e edite diretamente na tela enunciados, alternativas ou gabaritos se desejar fazer correções gramaticais.
* **Ajuste Fino de Imagens:** Visualize as mídias de apoio (diagramas, tabelas) recortadas fisicamente. Se desejar refinar o enquadramento, altere as coordenadas delimitadoras diretamente e visualize o recorte instantaneamente.

#### Passo 3: Publicação ou Exportação  
Após homologar a revisão: 
* **Persistir Direto no Banco:** Clique em **"Salvar no Banco de Dados"** para persistir as tabelas via Django ORM. As questões estarão disponíveis instantaneamente no aplicativo React Native móvel para os alunos!
* **Exportar Pacote (Portabilidade):** Clique em **"Exportar como ZIP"** para baixar o pacote portátil estruturado contendo o `prova.json` e a pasta `images/`. Este arquivo ZIP poderá ser reimportado futuramente de forma instantânea através da opção **"Importação Rápida via ZIP"** (sem custos IA).


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
