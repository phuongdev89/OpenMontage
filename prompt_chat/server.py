import os
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

# Load environment
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

AI_CHAT_URL = os.getenv("AI_CHAT_URL")
AI_CHAT_KEY = os.getenv("AI_CHAT_KEY")
AI_CHAT_MODEL = os.getenv("AI_CHAT_MODEL", "gpt-4o")

DB_PATH = Path(__file__).resolve().parent / "data" / "chat.db"
STATIC_INDEX = Path(__file__).resolve().parent / "index.html"
PROMPT_RULES_PATH = Path(__file__).resolve().parent / "prompt_rules.md"

SYSTEM_PROMPT = (
    "You are an expert video generation prompt engineer. "
    "Output ONLY finalized video generation prompts in markdown text code blocks. "
    "Use one self-contained code block per question when there are multiple questions. "
    "Do NOT include greetings, conversational filler, reasoning, preamble, or outro. "
    "When user requests edits, return the entire updated video prompt inside the code block."
)

def get_system_prompt() -> str:
    # Read on each request so edits to the rules apply without a server restart.
    return SYSTEM_PROMPT + "\n\n" + PROMPT_RULES_PATH.read_text(encoding="utf-8")

app = FastAPI(title="Video Prompt Chat Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        conn.commit()

init_db()

def get_ai_client() -> OpenAI:
    if not AI_CHAT_KEY:
        raise HTTPException(status_code=500, detail="AI_CHAT_KEY not configured in .env")
    return OpenAI(base_url=AI_CHAT_URL, api_key=AI_CHAT_KEY)

class CreateConversationRequest(BaseModel):
    title: Optional[str] = "Hội thoại mới"

class MessageRequest(BaseModel):
    content: str

@app.get("/", response_class=HTMLResponse)
def index():
    if not STATIC_INDEX.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(STATIC_INDEX)

@app.get("/api/conversations")
def list_conversations():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

@app.post("/api/conversations")
def create_conversation(req: CreateConversationRequest):
    conv_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO conversations (id, title) VALUES (?, ?)",
            (conv_id, req.title or "Hội thoại mới")
        )
        conn.commit()
    return {"id": conv_id, "title": req.title or "Hội thoại mới"}

@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: str):
    with get_db() as conn:
        conv = conn.execute("SELECT id, title, created_at FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        messages = conn.execute(
            "SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conv_id,)
        ).fetchall()
        return {"conversation": dict(conv), "messages": [dict(m) for m in messages]}

@app.delete("/api/conversations/{conv_id}")
def delete_conversation(conv_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conv_id,))
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        conn.commit()
    return {"status": "ok"}

@app.post("/api/conversations/{conv_id}/messages")
def send_message(conv_id: str, req: MessageRequest):
    user_text = req.content.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Empty message")

    with get_db() as conn:
        conv = conn.execute("SELECT id, title FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'user', ?)",
            (conv_id, user_text)
        )
        if conv["title"] in ("Hội thoại mới", "New Chat"):
            new_title = user_text[:35] + ("..." if len(user_text) > 35 else "")
            conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (new_title, conv_id))

        history_rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC LIMIT 20",
            (conv_id,)
        ).fetchall()
        conn.commit()

    client = get_ai_client()
    messages_payload: List[Dict[str, str]] = [{"role": "system", "content": get_system_prompt()}]
    for row in history_rows:
        messages_payload.append({"role": row["role"], "content": row["content"]})

    def event_generator():
        full_reply = []
        try:
            stream = client.chat.completions.create(
                model=AI_CHAT_MODEL,
                messages=messages_payload,
                temperature=0.7,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_reply.append(delta)
                    yield f"data: {json.dumps({'chunk': delta})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        full_content = "".join(full_reply).strip()
        if not (full_content.startswith("```") and full_content.endswith("```")):
            full_content = f"```text\n{full_content}\n```"

        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?, 'assistant', ?)",
                (conv_id, full_content)
            )
            msg_id = cursor.lastrowid
            conn.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conv_id,)
            )
            conn.commit()

        yield f"data: {json.dumps({'done': True, 'id': msg_id, 'content': full_content})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
