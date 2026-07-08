from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Local AI Service")

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434") + "/api/generate"
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

class AskRequest(BaseModel):
    prompt: str
    model: str | None = None

@app.get("/")
def home():
    return {"status": "healthy", "default_model": DEFAULT_MODEL}

@app.post("/ask")
def ask_ollama(request: AskRequest):
    try:
        model_to_use = request.model or DEFAULT_MODEL
        
        payload = {
            "model": model_to_use,
            "prompt": request.prompt,
            "stream": False
        }
        resp = requests.post(OLLAMA_URL, json=payload, timeout=90)
        resp.raise_for_status()
        result = resp.json()
        return {"response": result.get("response", "No response")}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}