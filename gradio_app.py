import os
import gradio as gr
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("FASTAPI_URL", "http://fastapi:8000/ask")


def get_available_models():
    models_env = os.getenv("AVAILABLE_MODELS", "").strip()
    if models_env:
        return [m.strip() for m in models_env.split(",") if m.strip()]
    try:
        resp = requests.get("http://ollama:11434/api/tags", timeout=10)
        if resp.status_code == 200:
            return [m["name"] for m in resp.json().get("models", [])] or ["llama3.2"]
        return ["llama3.2", "phi3:mini", "qwen2.5:3b", "gemma2:2b"]
    except:
        return ["llama3.2", "phi3:mini", "qwen2.5:3b", "gemma2:2b"]


def respond(message, history, model, temperature, system_prompt):
    if not message:
        return ""

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

    try:
        payload = {
            "prompt": full_prompt,
            "model": model,
            "temperature": float(temperature)
        }

        # Non-streaming call (more stable)
        response = requests.post(API_URL, json=payload, timeout=120)
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

demo.launch(server_name="0.0.0.0", server_port=7860, share=True)