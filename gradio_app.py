import os
import sqlite3
import gradio as gr
import requests
from pypdf import PdfReader
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("FASTAPI_URL", "http://fastapi:8000/ask")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))
ENABLE_SHARE = os.getenv("ENABLE_SHARE", "false").lower() == "true"
SERVER_PORT = int(os.getenv("SERVER_PORT", "7860"))
DB_PATH = os.getenv("DB_PATH", "/app/data/chat_history.db")

AVAILABLE_MODELS = os.getenv("AVAILABLE_MODELS", "llama3.2,phi3:mini,qwen2.5:3b,gemma2:2b").split(",")

document_context = ""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL
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
    return [{"role": role, "content": content} for role, content in rows]

def save_message(role, content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

init_db()

def extract_text(file):
    if file is None:
        return ""
    try:
        if file.name.endswith(".pdf"):
            reader = PdfReader(file.name)
            return "\n".join([p.extract_text() or "" for p in reader.pages]).strip()
        else:
            with open(file.name, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        return f"[Error: {str(e)}]"

def generate_response(message, history, model, mode, document_context):
    save_message("user", message)

    if mode == "RAG (FastAPI)" and document_context and document_context.strip():
        prompt_parts = [
            "You are a helpful assistant. Answer ONLY using the Document Context below.",
            "If the answer cannot be found in the document, say 'I don't have that information in the document.'",
            "\n=========================================",
            f"DOCUMENT CONTEXT:\n{document_context}",
            "=========================================\n",
            "CONVERSATION HISTORY:"
        ]
        for msg in load_history():
            role_label = "Human" if msg["role"] == "user" else "Assistant"
            prompt_parts.append(f"{role_label}: {msg['content']}")
        prompt_parts.append(f"\nCURRENT QUESTION: {message}")
        prompt_parts.append("=========================================")
        prompt_parts.append("Assistant:")

        full_prompt = "\n".join(prompt_parts)
        payload = {"prompt": full_prompt, "model": model}
        url = API_URL
    else:
        payload = {"prompt": message, "model": model}
        url = API_URL

    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        bot_message = response.json().get("response", "No response")
    except Exception as e:
        bot_message = f"Error: {str(e)}"

    save_message("assistant", bot_message)
    return "", load_history()

def process_file(file):
    global document_context
    if file is None:
        return "No file uploaded."
    text = extract_text(file)
    document_context = text
    return f"Successfully processed {os.path.basename(file.name)}. Context updated!"

with gr.Blocks(title="Local AI Research Assistant", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Local LLM & RAG Chat Interface")

    with gr.Row():
        with gr.Column(scale=2):
            mode_radio = gr.Radio(
                choices=["Standard Chat", "RAG (FastAPI)"],
                value="Standard Chat",
                label="Execution Mode"
            )
            model_dropdown = gr.Dropdown(
                choices=AVAILABLE_MODELS,
                value=DEFAULT_MODEL,
                label="Model Selection"
            )
            file_uploader = gr.File(
                label="Upload Document (.pdf, .txt)",
                file_types=[".pdf", ".txt"]
            )
            upload_status = gr.Textbox(label="Upload Status", interactive=False)
           
        with gr.Column(scale=4):
            chatbot = gr.Chatbot(
                value=load_history(),
                label="Chat History",
                type="messages"
            )
            msg_input = gr.Textbox(placeholder="Type your message here...", label="Your Message")
            clear_btn = gr.Button("Clear History")

    file_uploader.change(fn=process_file, inputs=file_uploader, outputs=upload_status)

    msg_input.submit(
        fn=generate_response,
        inputs=[msg_input, chatbot, model_dropdown, mode_radio, doc_state],
        outputs=[msg_input, chatbot]
    )

    def clear_chat():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        conn.commit()
        conn.close()
        global document_context
        document_context = ""
        return [], "Context and history cleared."

    clear_btn.click(fn=clear_chat, inputs=None, outputs=[chatbot, upload_status])

demo.launch(server_name="0.0.0.0", server_port=SERVER_PORT, share=ENABLE_SHARE, show_api=False)