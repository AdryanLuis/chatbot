import os
import uuid
import uvicorn
import aiosqlite
import pandas as pd
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from sqlalchemy import create_engine

load_dotenv()


API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("A variável de ambiente GOOGLE_API_KEY não foi definida.")


model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=API_KEY,
    temperature=0.7,
)

async def stream_agent_and_save(prompt: str, history: list, db, chat_id: str):
    full_response = ""
    
    print(f"\n[Agente SQL] Invocando com o prompt: {prompt}")
    
    async for chunk in sql_agent_executor.astream({"input": prompt, "history": history}):
        
        if "output" in chunk:
            chunk_content = chunk["output"]
            
            if isinstance(chunk_content, str):
                full_response += chunk_content
                yield chunk_content
            
    print(f"\n[Agente SQL] Resposta completa: {full_response}")

    if full_response: 
        await db.execute(
            "INSERT INTO messages (chatId, role, content) VALUES (?, ?, ?)",
            (chat_id, 'ai', full_response)
        )
        await db.commit()
    else:
        print("[Agente SQL] Aviso: Resposta final estava vazia. Nada salvo no DB.")
        yield "[O agente não produziu uma resposta em texto. Verifique o console.]"


async def stream_and_save(prompt: str, history: list, db, chat_id: str):
    full_response = ""
    
    async for chunk in chain.astream({"input": prompt, "history": history}):
        chunk_content = chunk.content
        full_response += chunk_content
        yield chunk_content  
    
    await db.execute(
        "INSERT INTO messages (chatId, role, content) VALUES (?, ?, ?)",
        (chat_id, 'ai', full_response)
    )
    await db.commit()

promptTemplate = ChatPromptTemplate.from_messages([
    ("system", "Você é um assistente de chatbot muito prestativo e amigável."),
    MessagesPlaceholder("history"),
    ("human", "{input}"),
])

chain = promptTemplate | model

print("Criando o Roteador de Intenção...")
router_prompt_template = PromptTemplate.from_template(
"""Dada a pergunta do usuário, classifique-a como 'sql' ou 'conversa'.

Use 'sql' para perguntas que buscam informações específicas, cálculos, totais, médias, ou listas sobre vendas, produtos, clientes, ou regiões.
Exemplos de 'sql':
- Quanto vendemos de Calça Jeans?
- Qual o total de vendas no Nordeste?
- Liste os 5 produtos mais vendidos.
- Quem foi o Cliente G?

Use 'conversa' para saudações, despedidas, perguntas gerais, ou qualquer coisa que não possa ser respondida pela tabela 'vendas'.
Exemplos de 'conversa':
- Olá, tudo bem?
- Quem é você?
- Qual a capital da França?

Pergunta do usuário: {input}
Classificação:"""
)

router_chain = router_prompt_template | model | StrOutputParser()
print("Roteador criado com sucesso.")

DB_FILE = "./chatbot.db"

print("Conectando ao banco de dados para o Agente SQL...")
db_uri = f"sqlite:///{DB_FILE}"

engine = create_engine(db_uri) 

sql_db_connection = SQLDatabase(engine) 


print("Criando o Agente SQL...")

agent_prompt_suffix = """
IMPORTANTE: Responda sempre em Português do Brasil.

Ao filtrar por uma coluna de texto (como 'Produto', 'Cliente', 'Categoria'), você DEVE usar a função `LOWER()` na coluna e no valor, e usar o operador `LIKE` com `%` para correspondências parciais.
Isso garante que você encontre 'mochila', 'Mochila' ou 'Mochila de Couro'.

Exemplo de consulta CORRETA:
SELECT COUNT(*) FROM vendas WHERE LOWER(Produto) LIKE LOWER('%mochila%')

Exemplo de consulta ERRADA (NÃO FAÇA ISSO):
SELECT COUNT(*) FROM vendas WHERE Produto = 'Mochila'
"""

sql_agent_executor = create_sql_agent(
    llm=model, 
    db=sql_db_connection, 
    agent_type="openai-tools", 
    verbose=True,
    suffix=agent_prompt_suffix
)
print("Agente SQL criado com sucesso (e mais inteligente!).")




async def setup_database(db):
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chatId TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chatId) REFERENCES chats(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS vendas (
            ID INTEGER PRIMARY KEY,
            Data DATETIME NOT NULL,
            Cliente TEXT,
            Produto TEXT,
            Categoria TEXT,
            Quantidade INTEGER,
            Preco_Unitario REAL,
            Total REAL,
            Regiao TEXT,
            Observacoes TEXT
        );
    """)
    print("Tabelas 'chats', 'messages' e 'vendas' verificadas.")

    async with db.execute("SELECT COUNT(ID) as count FROM vendas") as cursor:
        result = await cursor.fetchone()
        count = result['count']

    if count == 0:
        print("Tabela 'vendas' está vazia. Carregando dados...")
        try:
            file_name = 'Vendas.xlsx' 
            
            print(f"Lendo arquivo: '{file_name}'...")
            
            if file_name.endswith('.csv'):
                print("Arquivo é CSV. Lendo com 'latin1' e sep=';'...")

                df = pd.read_csv(
                    file_name, 
                    encoding='latin1', 
                    sep=';'
                )
            elif file_name.endswith('.xlsx'):
                print("Arquivo é Excel. Lendo com 'read_excel'...")
                df = pd.read_excel(file_name)
            else:
                raise ValueError("Formato de arquivo não reconhecido. Use .csv ou .xlsx")

            print("Arquivo lido com sucesso. Renomeando colunas...")
            df.rename(columns={
                'Preço Unitário': 'Preco_Unitario',
                'Observações': 'Observacoes',
                'Região': 'Regiao'
            }, inplace=True)

            print("Formatando datas...")
            df['Data'] = pd.to_datetime(df['Data']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            df_sql = df[['ID', 'Data', 'Cliente', 'Produto', 'Categoria', 'Quantidade', 'Preco_Unitario', 'Total', 'Regiao', 'Observacoes']]
            
            data_tuples = list(df_sql.itertuples(index=False, name=None))
            
            print("Inserindo dados no banco...")
            await db.executemany(
                "INSERT INTO vendas (ID, Data, Cliente, Produto, Categoria, Quantidade, Preco_Unitario, Total, Regiao, Observacoes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                data_tuples
            )
            
            await db.commit()
            print(f"Sucesso! {len(data_tuples)} linhas inseridas na tabela 'vendas'.")

        except FileNotFoundError:
            print(f"ERRO: Arquivo '{file_name}' não encontrado.")
            print("Certifique-se que o arquivo está no mesmo diretório do main.py")
        except Exception as e:
            print(f"Erro ao carregar dados do arquivo: {e}")
            await db.rollback()
    else:
        print(f"Tabela 'vendas' já contém {count} linhas. Carregamento pulado.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    db = await aiosqlite.connect(DB_FILE)
    db.row_factory = aiosqlite.Row
    await setup_database(db)
    app.state.db = db
    yield
    await app.state.db.close()
    print("Conexão com o banco de dados fechada.")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
    expose_headers=["X-Chat-Id", "X-Chat-Title"]
)

class ChatRequest(BaseModel):
    prompt: str
    chatId: Optional[str] = None


@app.get("/api/chats", response_model=List[Dict[str, Any]])
async def get_chats(request: Request):
    db = request.app.state.db
    try:
        async with db.execute("SELECT * FROM chats ORDER BY createdAt DESC") as cursor:
            chats = await cursor.fetchall()
            return [dict(chat) for chat in chats]
    except Exception as e:
        print(f"Erro ao buscar chats: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar chats do banco de dados.")

@app.get("/api/chat/{id}", response_model=List[Dict[str, str]])
async def get_chat_messages(id: str, request: Request):
    db = request.app.state.db
    try:
        async with db.execute(
            "SELECT role, content FROM messages WHERE chatId = ? ORDER BY createdAt ASC",
            (id,)
        ) as cursor:
            messages = await cursor.fetchall()
            return [dict(msg) for msg in messages]
    except Exception as e:
        print(f"Erro ao buscar mensagens do chat: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar mensagens.")

@app.post("/api/chat")
async def post_chat(chat_request: ChatRequest, request: Request):
    db = request.app.state.db
    prompt = chat_request.prompt
    current_chat_id = chat_request.chatId
    response_headers = {}

    if not prompt:
        raise HTTPException(status_code=400, detail="O 'prompt' é obrigatório.")

    try:
        if not current_chat_id:
            current_chat_id = str(uuid.uuid4())
            title = (prompt[:50] + '...') if len(prompt) > 50 else prompt
            
            await db.execute(
                "INSERT INTO chats (id, title) VALUES (?, ?)",
                (current_chat_id, title)
            )
            response_headers["X-Chat-Id"] = current_chat_id
            response_headers["X-Chat-Title"] = title

        await db.execute(
            "INSERT INTO messages (chatId, role, content) VALUES (?, ?, ?)",
            (current_chat_id, 'human', prompt)
        )
        
        async with db.execute(
            "SELECT role, content FROM messages WHERE chatId = ? ORDER BY createdAt ASC",
            (current_chat_id,)
        ) as cursor:
            history_rows = await cursor.fetchall()

        history_messages = [] 
        for row in history_rows:
            if row["role"] == 'human':
                history_messages.append(HumanMessage(content=row["content"]))
            else:
                history_messages.append(AIMessage(content=row["content"]))
        
        if history_messages:
            history_messages.pop()

        await db.commit()

        print(f"\n[Roteador] Classificando o prompt: {prompt}")
        route = await router_chain.ainvoke({"input": prompt})
        print(f"[Roteador] Decisão: {route}")

        if "sql" in route.lower():
            print("[Roteador] Usando o Agente SQL.")
            streaming_function = stream_agent_and_save(prompt, history_messages, db, current_chat_id)
        else:
            print("[Roteador] Usando o Chat Conversacional.")
            streaming_function = stream_and_save(prompt, history_messages, db, current_chat_id)
        

        return StreamingResponse(
            streaming_function,
            media_type="text/plain",
            headers=response_headers
        )

    except Exception as e:
        await db.rollback() 
        print(f"Erro ao processar /api/chat: {e}")
        raise HTTPException(status_code=500, detail="Desculpe, algo deu errado.")
    
@app.delete("/api/chat/{id}")
async def delete_chat(id: str, request: Request):
    db = request.app.state.db
    try:
        await db.execute("DELETE FROM chats WHERE id = ?", (id,))
        await db.commit()
        return {"message": "Chat excluído com sucesso"}
    except Exception as e:
        await db.rollback()
        print(f"Erro ao excluir chat: {e}")
        raise HTTPException(status_code=500, detail="Erro ao excluir chat.")

if __name__ == "__main__":
    print("Servidor LangChain rodando na porta 3000.")
    uvicorn.run("main:app", host="127.0.0.1", port=3000, reload=True)