import os
import uuid
import uvicorn
import aiosqlite
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

load_dotenv()


API_KEY = os.getenv("GOOGLE_API_KEY")

if not API_KEY:
    raise ValueError("A variável de ambiente GOOGLE_API_KEY não foi definida.")


model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key=API_KEY,
    temperature=0.7,
)


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

DB_FILE = "./chatbot.db"

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
            role TEXT NOT NULL, -- 'human' ou 'ai'
            content TEXT NOT NULL,
            createdAt DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chatId) REFERENCES chats(id) ON DELETE CASCADE
        );
    """)
    await db.commit()

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

        history = []
        for row in history_rows:
            if row["role"] == 'human':
                history.append(HumanMessage(content=row["content"]))
            else:
                history.append(AIMessage(content=row["content"]))
        
        if history:
            history.pop()

        await db.commit() 
        
        return StreamingResponse(
            stream_and_save(prompt, history, db, current_chat_id),
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