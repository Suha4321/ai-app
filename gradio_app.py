import os
import sqlite3
import gradio as gr
import requests
from dotenv import load_dotenv

load_dotenv()

# ====================== CONFIG (12-Factor) ======================
API_URL = os.getenv("FASTAPI_URL", "http://fastapi:8000/ask")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "10"))
ENABLE_SHARE = os.getenv("ENABLE_SHARE", "false").lower() == "true"
SERVER_PORT = int(os.getenv("SERVER_PORT", "7860"))
DB_PATH = os.getenv("DB_PATH", "/app/data/chat_history.db")

# Fallback models from env (comma separated)
FALLBACK_MODELS = os.getenv(
    "FALLBACK_MODELS", 
    "llama3.2,phi3:mini,qwen2.5:3b,gemma2:2b"
).split(",")

# ====================== DATABASE (SQLite) ======================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def load_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM messages ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    history = []
    for i in range(0, len(rows), 2):
        if i + 1 < len(rows):
            history.append([rows[i][1], rows[i + 1][1]])
    return history

def save_message(role, content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (role, content) VALUES (?, ?)",
        (role, content)
    )
    conn.commit()
    conn.close()


# Initialize database
init_db()

# ====================== CHAT LOGIC ======================
def get_available_models():
    models_env = os.getenv("AVAILABLE_MODELS", "").strip()
    
    if models_env:
        return [m.strip() for m in models_env.split(",") if m.strip()]
    
    # Dynamic fetch from Ollama
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=OLLAMA_TIMEOUT)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            return models if models else FALLBACK_MODELS
        return FALLBACK_MODELS
    except:
        return FALLBACK_MODELS


def respond(message, history, model, temperature, system_prompt):
    print(">>> [DEBUG] respond() function was called!")
    
    if not message or not message.strip():
        return ""

    try:
        # Build prompt
        prompt_parts = []
        if system_prompt.strip():
            prompt_parts.append(f"System: {system_prompt.strip()}")

        for user_msg, assistant_msg in history:
            prompt_parts.append(f"Human: {user_msg}")
            if assistant_msg:
                prompt_parts.append(f"Assistant: {assistant_msg}")

        prompt_parts.append(f"Human: {message}")
        full_prompt = "\n".join(prompt_parts) + "\nAssistant:"

        payload = {
            "prompt": full_prompt,
            "model": model,
            "temperature": float(temperature)
        }

        response = requests.post(API_URL, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        result = response.json()
        assistant_response = result.get("response", "No response from model")

        # Save to database (this must come BEFORE the return)
        print(">>> [DEBUG] Saving to database...")
        save_message("user", message)
        save_message("assistant", assistant_response)

        return assistant_response

    except Exception as e:
        error_msg = f"Error: {str(e)}"
        try:
            save_message("user", message)
            save_message("assistant", error_msg)
        except:
            pass
        return error_msg


# ====================== UI ======================
with gr.Blocks(title="Local AI Assistant", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🧠 Local AI Assistant")

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Accordion("Settings", open=True):
                models = get_available_models()
                model = gr.Dropdown(models, value=models[0], label="Model")
                temperature = gr.Slider(0, 1.5, value=0.7, step=0.1, label="Temperature")
                system_prompt = gr.Textbox(
                    label="System Prompt", 
                    lines=3, 
                    placeholder="You are a helpful assistant..."
                )

        with gr.Column(scale=3):
            chatbot = gr.ChatInterface(
                respond,
                additional_inputs=[model, temperature, system_prompt],
                title="Chat with local models",
                description="Select a model and start chatting"
            )

demo.launch(
    server_name="0.0.0.0", 
    server_port=SERVER_PORT, 
    share=ENABLE_SHARE
)