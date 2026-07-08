import os
import gradio as gr
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("FASTAPI_URL", "http://fastapi:8000/ask")

AVAILABLE_MODELS = ["llama3.2", "phi3:mini", "qwen2.5:3b", "gemma2:2b"]

def ask_ai(prompt, model):
    if not prompt or not prompt.strip():
        return "Please enter a question."
    
    try:
        response = requests.post(
            API_URL, 
            json={"prompt": prompt.strip(), "model": model}, 
            timeout=90
        )
        response.raise_for_status()
        return response.json()["response"]
    except Exception as e:
        return f"Error: {str(e)}"

with gr.Blocks(title="Multi-Model Local AI") as demo:
    gr.Markdown("# Local AI with Model Selection")
    
    model_dropdown = gr.Dropdown(
        choices=AVAILABLE_MODELS,
        value="llama3.2",
        label="Select Model",
        interactive=True
    )
    
    with gr.Row():
        prompt = gr.Textbox(label="Your question", lines=4, placeholder="Ask anything...")
        output = gr.Textbox(label="Response", lines=10)
    
    gr.Button("Send", variant="primary").click(
        ask_ai, 
        inputs=[prompt, model_dropdown], 
        outputs=output
    )

demo.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", 7860)))