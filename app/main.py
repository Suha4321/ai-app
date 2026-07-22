from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Local AI Service")

# ====================== 12-FACTOR CONFIG ======================
BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")  
OLLAMA_URL = f"{BASE_URL.rstrip('/')}/api/generate"
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama3.2")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "90"))


class AskRequest(BaseModel):
    prompt: str
    model: str | None = None
    temperature: float | None = 0.7


@app.get("/")
def home():
    return {
        "status": "healthy",
        "default_model": DEFAULT_MODEL
    }


@app.post("/ask")
def ask_ollama(request: AskRequest):
    try:
        model_to_use = request.model or DEFAULT_MODEL
        print(f"FastAPI Routing Request to Model: {model_to_use}", flush=True)

        payload = {
            "model": model_to_use,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature 
            }
        }

        resp = requests.post(
            OLLAMA_URL, 
            json=payload, 
            timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        result = resp.json()

        return {"response": result.get("response", "No response from model")}

    except Exception as e:
        return {"response": f"Error: {str(e)}"}