# Chatbot 1500 (Projeto Full-Stack com Gemini e FastAPI)

Este é um projeto de chatbot full-stack que demonstra a integração de um modelo de linguagem avançado (Google Gemini) com um backend Python (FastAPI) e um frontend interativo em JavaScript puro.

O aplicativo permite conversas em tempo real, salva o histórico de chats em um banco de dados SQLite e apresenta as respostas da IA em streaming (palavra por palavra) com formatação Markdown.

## ✨ Features

* **IA Conversacional:** Conectado ao modelo `gemini-2.5-flash` do Google através da biblioteca LangChain.
* **Respostas em Streaming:** As respostas da IA são exibidas em tempo real, palavra por palavra.
* **Histórico de Chat:** Todas as conversas são salvas em um banco de dados SQLite.
* **Gerenciamento de Chats:** O usuário pode criar novos chats e excluir chats antigos.
* **Frontend Responsivo:** O layout se adapta 100% à altura e largura da janela do navegador.
* **Renderização de Markdown:** As respostas do bot são formatadas (listas, tabelas, negrito, etc.) usando a biblioteca `marked.js`.
* **Tema Light/Dark:** O usuário pode alternar entre os temas, e a preferência é salva no `localStorage` do navegador.

## 🛠️ Tech Stack

| Área | Tecnologia | Descrição |
| :--- | :--- | :--- |
| **Backend** | Python 3.9+ | Linguagem principal da API. |
| | FastAPI | Framework web para criar os endpoints da API. |
| | Uvicorn | Servidor ASGI para rodar o FastAPI. |
| | LangChain | Framework para orquestrar a lógica da IA e gerenciar prompts. |
| | Google Gemini | Modelo de linguagem (LLM) que gera as respostas. |
| | aiosqlite | Driver assíncrono para o banco de dados SQLite. |
| | python-dotenv | Para gerenciar chaves de API no arquivo `.env`. |
| **Frontend** | HTML5 | Estrutura semântica da página. |
| | CSS3 | Estilização moderna, incluindo Variáveis CSS para os temas. |
| | Vanilla JavaScript | Lógica do app, incluindo chamadas `fetch` e manipulação do DOM. |
| | marked.js | Biblioteca para converter Markdown (da IA) em HTML. |
| | http-server | Servidor local (via npm) para servir os arquivos estáticos. |

## 🚀 Como Instalar e Rodar

Siga os passos abaixo para configurar e rodar o projeto localmente.

### Pré-requisitos

* **Python 3.9** ou superior
* **Node.js 18** ou superior (incluindo npm)
* Uma **Google API Key** (configurada no [Google AI Studio](https://aistudio.google.com/app/apikey))

---

### 1. Configuração do Backend (Python)

1.  **Navegue até a pasta `backend`:**
    ```bash
    cd backend
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    # No Mac/Linux
    python3 -m venv .venv
    source .venv/bin/activate

    # No Windows (PowerShell)
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```

3.  **Instale as dependências Python:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Crie o arquivo `.env`:**
    * Na pasta `backend`, crie um arquivo chamado `.env`.
    * Adicione sua chave de API do Google nele:

    ```ini
    GOOGLE_API_KEY="SUA_CHAVE_DE_API_DO_GOOGLE_AQUI"
    ```

### 2. Configuração do Frontend (Node.js)

1.  **Em outro terminal,** navegue até a pasta `frontend`:
    ```bash
    cd frontend
    ```

2.  **Instale as dependências Node (o `http-server`):**
    ```bash
    npm install
    ```
    *(Isso lerá o `package.json` e instalará o que for necessário).*

---

### 3. Rodando o Projeto

Você precisará de **dois terminais** abertos simultaneamente.

**Terminal 1 - Rodar o Backend:**
* (Certifique-se de estar na pasta `backend` e com o ambiente virtual ativado)
```bash
uvicorn main:app --reload
```
> 🛰️ O backend estará rodando em `http://localhost:3000`

**Terminal 2 - Rodar o Frontend:**
* (Certifique-se de estar na pasta `frontend`)
```bash
npm start
```
> 🖥️ O frontend estará sendo servido em `http://localhost:8080` (ou outra porta definida no `package.json`).

Agora, abra seu navegador e acesse **`http://localhost:8080`** para usar o chatbot!

## 📁 Estrutura do Projeto

```
CHATBOT/
├── backend/
│   ├── .venv/               (Ambiente virtual Python)
│   ├── .env                 (Onde você coloca sua API Key)
│   ├── chatbot.db           (Banco de dados - criado automaticamente)
│   ├── main.py              (API FastAPI, lógica da IA)
│   └── requirements.txt     (Dependências Python)
│
└── frontend/
    ├── node_modules/        (Dependências do npm)
    ├── index.html           (Estrutura do chat)
    ├── package.json         (Define o 'npm start' e dependências)
    ├── script.js            (Lógica do frontend, chamadas de API)
    └── style.css            (Estilos e temas)
```
