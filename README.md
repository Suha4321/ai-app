# Local Multi-Model AI App

A fully containerized local AI application using "Ollama", "FastAPI", and "Gradio", built with 12-Factor principles.

## Features

- Run multiple open-source LLMs locally (llama3.2, phi3, qwen2.5, etc.)
- FastAPI backend with REST API
- Gradio web UI with model selector dropdown
- Open WebUI (ChatGPT-like interface)
- Docker Compose setup for easy development and deployment
- Pinned dependencies and multi-stage builds
- Environment-based configuration

## Tech Stack

- "Ollama" — Local LLM inference
- "FastAPI" — Backend API
- "Gradio" — Interactive UI with model selection
- "Docker + Docker Compose" — Containerization
- "Python 3.12"

## Quick Start

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd ai-app

## Start all services
docker compose up --build -d

## Access the applications
Access the applications:
Gradio UI (with model selector): http://localhost:7860
FastAPI Interactive Docs: http://localhost:8000/docs
Open WebUI: http://localhost:8080
Ollama API: http://localhost:11434

## Available models
docker exec -it ai-app-ollama-1 ollama pull llama3.2
docker exec -it ai-app-ollama-1 ollama pull phi3:mini
docker exec -it ai-app-ollama-1 ollama pull qwen2.5:3b

## Project structure 
```text
i-app/
├── app/
│   ├── main.py              # FastAPI backend logic
│   ├── chroma_db/          # Persistent collection for vector embeddings
│   ├── data/               # SQLite database path (chat_history.db)
│   └── ollama-models/      # Persistent local cache for downloaded LLM weights
├── .dockerignore
├── .gitignore
├── docker-compose.yml
├── Dockerfile.fastapi       # Build configuration for the FastAPI service
├── Dockerfile.gradio        # Build configuration for the Gradio interface
├── gradio_app.py           # Gradio frontend entry point
├── README.md               # System documentation
└── requirements.txt        # Shared package dependencies
```
# Development commands
docker compose up --build -d     # Start all services
docker compose logs -f gradio    # View Gradio logs
docker compose restart gradio    # Restart only Gradio
docker compose down              # Stop everything


# System Architecture & Resource Requirements

This project runs as a decoupled microservices stack managed via Docker Compose. It leverages native Apple Silicon virtualization to handle local document extraction, vector embeddings, and large language model (LLM) generation entirely on-device.

## Architecture Diagram & Component Breakdown
```text
                  ┌──────────────────────┐
                  │  Open WebUI (Port)   │ (Alternative Chat UI)
                  └──────────┬───────────┘
                             │
                             ▼
┌──────────────┐   HTTP   ┌──────────────┐   HTTP   ┌──────────────┐
│  Gradio UI   ├─────────►│ FastAPI App  ├─────────►│  Ollama API  │
│ (Port 7860)  │  /ask    │ (Port 8000)  │  /api    │ (Port 11434) │
└──────┬───────┘          └──────────────┘          └──────┬───────┘
       │                                                   │
       ├─► [ChromaDB (Vector Database)]                    ├─► [llama3.2] (LLM)
       │                                                   │
       └─► [SQLite (Chat History)]                         └─► [nomic-embed-text]

```
1. **Gradio UI (`ai-app-gradio-1`)**: The user interface. It handles file uploads (`.pdf`, `.txt`), parses document text, manages the local **ChromaDB** vector instance for RAG context, and connects to an underlying **SQLite** database for chat persistence.
2. **FastAPI (`ai-app-fastapi-1`)**: The routing middleware. It exposes an ingestion gateway (`/ask`), enforces system-wide timeouts, parses requests against strict Pydantic schemas, and handles upstream communication with Ollama.
3. **Ollama (`ai-app-ollama-1`)**: The heavy-computational core. It runs as a localized background service managing raw model weights, execution contexts, and token generation.
4. **Open WebUI (`ai-app-open-webui-1`)**: An optional, feature-rich alternative web console natively paired with the Ollama instance for direct model interaction.


## Hardware & Resource Thresholds

Running machine learning models locally introduces high resource volatility. While the stack uses ~2.1 GB of memory while idling, **it requires a minimum hardware allocation threshold to survive active workloads.**

### Minimum vs. Recommended Allocation (Docker Desktop)

| Resource | Hard Minimum | Recommended | Why it matters |
| :--- | :--- | :--- | :--- |
| **Memory (RAM)** | **8 GB** | **12 GB+** | Prevents **OOM (Out-of-Memory) crashes** when Ollama swaps LLM weights into memory or Gradio builds vector embeddings. |
| **CPUs** | **4 Cores** | **6+ Cores** | Prevents system UI lockups on your Mac during matrix calculations and heavy file tokenization. |

### Operational Memory Profiles (What to Expect)

* **Idle State (~2.1 GB Total Memory):** 
  The containers sit passively. Open WebUI holds its basic footprint (~1.1 GB), Gradio maintains the empty vector database context (~926 MiB), while FastAPI and Ollama run as lean daemons (<100 MiB combined).
* **Document Ingestion Spike (+500 MiB to 1 GB Memory, Heavy CPU):**
  When uploading PDFs, Gradio spins up `all-MiniLM-L6-v2` via PyTorch to generate vector embeddings. The CPU will briefly spike past 100% as it processes chunks into ChromaDB.
* **LLM Generation Spike (+2.5 GB to 5 GB Memory, Sustained CPU):**
  The moment a prompt is routed to Ollama, it immediately pulls the selected model (e.g., `llama3.2`) into memory. Memory usage for `ai-app-ollama-1` will violently jump from 34 MiB to several gigabytes until token generation completes.

---

## Configuration Setup for Apple Silicon (M1/M2/M3)

To ensure this architecture utilizes your Mac's native hardware layout instead of failing under Rosetta x86 emulation, your `docker-compose.yml` service configurations must match these definitions:

```yaml
services:
  gradio:
    platform: linux/arm64       # 1. Forces native ARM architecture to stop ONNX CPU errors
    image: ai-app-gradio
    environment:
      - CHROMA_TELEMETRY_ON=False # 2. Disables broken analytics packages to save memory
      - ANONYMIZED_TELEMETRY=False
    deploy:
      resources:
        limits:
          memory: 4G            # 3. Restricts individual containers without choking the host
```

### Rebuilding the Stack
If you have adjusted your Docker Desktop resource sliders to match the recommended thresholds above, completely reset and rebuild your cache:
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```
## roubleshooting & FAQs

### 1. I see `onnxruntime cpuid_info warning: Unknown CPU vendor` in the logs. Is it broken?
* **No, this is completely harmless.** 
* **Why it happens:** The underlying ONNX matrix engine searches for an Intel or AMD hardware signature to apply legacy x86 math optimizations. Because it is running inside a Linux Docker container virtualized on top of an Apple M-Series chip, it reads a blank vendor ID (`0`). 
* **Action:** Ignore it. Your vector embeddings are still calculated correctly using native ARM instruction sets.

### 2. The Gradio interface keeps loading indefinitely or says "Error communicating with backend"
This usually indicates an upstream routing or timeout issue. Check the following:
* **Verify FastAPI is awake:** Run `curl http://localhost:8000/`. You should receive a `{"status": "healthy"}` payload.
* **Check Ollama's model state:** Ensure the required model is actually downloaded inside the Ollama container. Run:
  ```bash
  docker compose exec ollama ollama list
  ```
  If your model (e.g., `llama3.2`) is missing, pull it manually:
  ```bash
  docker compose exec ollama ollama pull llama3.2
  ```
  
### 3. How do I completely wipe my vector database and start fresh?
If your PDF chunks become corrupted or you want to delete indexed knowledge bases:
1. Click the **Clear History** button directly inside the Gradio UI. This executes an internal script wrapper that drops the collection and resets the underlying SQLite tables.
2. For a nuclear system reset, bring down the stack and erase the localized data directories on your Mac:
   ```bash
   docker compose down -v
   rm -rf ./chroma_db ./data
   docker compose up -d
   ```

### 4. Docker Desktop is freezing or failing to launch on my Mac
If background hypervisor threads become hung or corrupted:
* Force-terminate all hidden zombie Docker processes via your Mac Terminal:
  ```bash
  pkill -9 -f Docker
  ```
* Clear corrupted GUI layout files (this will not delete your image layers):
  ```bash
  rm -f ~/Library/Group\ Containers/group.com.docker/settings.json
  ```
* Relaunch cleanly: `open -a Docker`
