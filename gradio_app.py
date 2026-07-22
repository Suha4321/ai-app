import os
import sqlite3
import gradio as gr
import requests
import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

# ====================== CONFIG ======================
API_URL = os.getenv("FASTAPI_URL", "http://fastapi:8000/ask")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))
ENABLE_SHARE = os.getenv("ENABLE_SHARE", "false").lower() == "true"
SERVER_PORT = int(os.getenv("SERVER_PORT", "7860"))
DB_PATH = os.getenv("DB_PATH", "/app/data/chat_history.db")

AVAILABLE_MODELS = os.getenv("AVAILABLE_MODELS", "llama3.2,phi3:mini,qwen2.5:3b,gemma2:2b").split(",")

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ====================== CHROMA VECTOR DB ======================
chroma_client = chromadb.PersistentClient(path="./chroma_db")
EMBEDDING_MODEL = "nomic-embed-text"

local_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# Bind Ollama directly into your Chroma collection instance
collection = chroma_client.get_or_create_collection(
    name="documents",
    embedding_function=local_ef
)

def chunk_text(text, chunk_size=500, overlap=50):
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size]
        chunks.append(chunk)
    return chunks

def add_to_vector_db(text, filename):
    chunks = chunk_text(text)
    
    documents = []
    metadatas = []
    ids = []
    
    for i, chunk in enumerate(chunks):
        documents.append(chunk)
        metadatas.append({"filename": filename, "chunk": i})
        ids.append(f"{filename}_{i}")
        
    if documents:
        # Chroma automatically batches these and ships them to your Ollama Docker for vectorization
        collection.add(documents=documents, metadatas=metadatas, ids=ids)

def search_vector_db(query, n_results=3):
    # Chroma handles querying Ollama to convert your search string automatically
    results = collection.query(query_texts=[query], n_results=n_results)
    if results and "documents" in results and results["documents"]:
        inner_docs = results["documents"][0]
        # Ensure it is a valid list of text strings before returning
        if isinstance(inner_docs, list) and len(inner_docs) > 0:
            return inner_docs
    return []

# ====================== DATABASE ======================
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

# ====================== FILE EXTRACTION (FIX) ======================
def extract_text(file_path):
    """Safely extracts text from uploaded .txt or .pdf files."""
    try:
        if file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        elif file_path.endswith('.pdf'):
            # Lazy import so pypdf is only required if a PDF is actually uploaded
            import pypdf
            reader = pypdf.PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        else:
            return "Error: Unsupported file format."
    except Exception as e:
        return f"Error reading file: {str(e)}"

# ====================== CHAT LOGIC ======================
def generate_response(message, history, model, mode):
    if not message.strip():
        return "", history

    save_message("user", message)
    history.append({"role": "user", "content": message})

    if mode == "RAG (FastAPI)":
        relevant_chunks = search_vector_db(message)
        
        # 🔍 DEBUG LOG: Check if anything was pulled from ChromaDB
        print(f"\n[RAG DEBUG] Found {len(relevant_chunks)} relevant chunks for query: '{message}'")
        for idx, chunk in enumerate(relevant_chunks):
            print(f"  -> Chunk {idx}: {chunk[:100]}...")

        if relevant_chunks:
            context = "\n\n".join(relevant_chunks)
            # FIX: Explicitly tell the LLM that this context IS the uploaded document content
            full_prompt = (
                f"You are a helpful assistant. The following text contains segments extracted directly "
                f"from the user's uploaded document/PDF. Use this text to fulfill their request or question.\n\n"
                f"--- EXTRACTED DOCUMENT TEXT START ---\n"
                f"{context}\n"
                f"--- EXTRACTED DOCUMENT TEXT END ---\n\n"
                f"User Instruction: {message}\n\n"
                f"Answer:"
            )
        else:
            context = "(No relevant content found)"
            full_prompt = message
        
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
        bot_message = f"Error communicating with backend: {str(e)}"

    save_message("assistant", bot_message)
    history.append({"role": "assistant", "content": bot_message})
    
    return "", history

# ====================== UI ======================
with gr.Blocks(title="Local AI Research Assistant", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 Local LLM & RAG Chat Interface")

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
                file_types=[".pdf", ".txt"],
                type="filepath" # Ensures we get a string path to process
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

    def process_file(file_path):
        if file_path is None:
            return "No file uploaded."
        text = extract_text(file_path)
        if text.startswith("Error"):
            return text
        filename = os.path.basename(file_path)
        add_to_vector_db(text, filename)
        return f"✅ Processed and indexed {filename}"

    file_uploader.change(fn=process_file, inputs=file_uploader, outputs=upload_status)

    msg_input.submit(
        fn=generate_response,
        inputs=[msg_input, chatbot, model_dropdown, mode_radio],
        outputs=[msg_input, chatbot]
    )

    def clear_chat():
        global collection
        # Clear SQL
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        conn.commit()
        conn.close()
        
        # FIX: Correct way to wipe a ChromaDB Collection
        try:
            chroma_client.delete_collection("documents")
        except Exception:
            pass # Collection might already be missing
        collection = chroma_client.get_or_create_collection(name="documents")
        
        return [], "Context and history cleared."

    clear_btn.click(fn=clear_chat, inputs=None, outputs=[chatbot, upload_status])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=SERVER_PORT, share=ENABLE_SHARE, show_api=False)
