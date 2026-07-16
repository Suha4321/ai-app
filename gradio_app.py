import os
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
ENABLE_SHARE = os.getenv("ENABLE_SHARE", "true").lower() == "true"
SERVER_PORT = int(os.getenv("SERVER_PORT", "7860"))

# Fallback models from env (comma separated)
FALLBACK_MODELS = os.getenv(
    "FALLBACK_MODELS", 
    "llama3.2,phi3:mini,qwen2.5:3b,gemma2:2b"
).split(",")


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
    if not message:
        return ""

    # Build prompt with history + system prompt
    prompt_parts = []
    if system_prompt.strip():
        prompt_parts.append(f"System: {system_prompt.strip()}")

    for user_msg, assistant_msg in history:
        prompt_parts.append(f"Human: {user_msg}")
        if assistant_msg:
            prompt_parts.append(f"Assistant: {assistant_msg}")

    prompt_parts.append(f"Human: {message}")
    full_prompt = "\n".join(prompt_parts) + "\nAssistant:"

    try:
        payload = {
            "prompt": full_prompt,
            "model": model,
            "temperature": float(temperature)
        }

        response = requests.post(
            API_URL, 
            json=payload, 
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "No response from model")

    except Exception as e:
        return f"Error: {str(e)}"


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