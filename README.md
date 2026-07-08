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
ai-app/
├── app/main.py                 # FastAPI backend
├── gradio_app.py               # Gradio frontend with model selector
├── Dockerfile                  # Multi-stage build with virtualenv
├── docker-compose.yml
├── requirements.txt            # Pinned dependencies
├── .env.example
├── .gitignore
├── .dockerignore
└── README.md

# Development commands
docker compose up --build -d     # Start all services
docker compose logs -f gradio    # View Gradio logs
docker compose restart gradio    # Restart only Gradio
docker compose down              # Stop everything