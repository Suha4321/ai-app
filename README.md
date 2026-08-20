# Local Multi-Model AI App

A fully containerized local AI application using Ollama, FastAPI, and Gradio, built with 12-Factor principles. Runs two ways: locally via Docker Compose for development, or on Kubernetes via a Helm chart (tested on a local Kind cluster) as the production-shaped deployment path.

## Features

- Run multiple open-source LLMs locally (llama3.2, phi3:mini, qwen2.5:3b, gemma2:2b)
- FastAPI backend with a REST API and health/readiness probes
- Gradio web UI with a model-selector dropdown and Standard-Chat / RAG modes
- RAG over uploaded PDFs/TXT using ChromaDB + nomic-embed-text embeddings
- SQLite chat-history persistence
- Docker Compose setup for local development
- Helm chart for Kubernetes: Deployments, Services, PVCs, ConfigMap, liveness/readiness probes
- Config-driven model provisioning — the model list in values.yaml is the single source of truth
- Environment-based configuration

## Tech Stack

- Ollama — Local LLM inference
- FastAPI — Backend API
- Gradio — Interactive UI with model selection
- ChromaDB — Vector store for RAG
- Docker + Docker Compose — Containerization / local dev
- Kubernetes + Helm + Kind — Orchestrated deployment
- Python 3.12

## Two Ways to Run
Path	Use for	Entry point
Docker Compose - Fast local development on your Mac	- docker compose up --build -d
Kubernetes (Kind + Helm)- Production-shaped deploy, K8s learning, the portfolio story - helm install ai-app ./helm/ai-app

## (A) DOCKER COMPOSE QUICK START (LOCAL DEV)
## Quick Start

1. Clone the repository:
   ```   ```bash
   git clone <your-repo-url>
   cd ai-app

## Development commands
docker compose up --build -d     # Start all services
docker compose logs -f gradio    # View Gradio logs
docker compose restart gradio    # Restart only Gradio
docker compose down              # Stop everything

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

## B) KUBERNETES DEPLOYMENT (Kind + Helm)
This deploys the same three services onto a Kubernetes cluster using the Helm chart in helm/ai-app/. Kind (Kubernetes-in-Docker) runs the cluster nodes as Docker containers, so Docker Desktop must be running before you start.

## Prerequisites
Tool	Install (macOS / Homebrew)
- Docker Desktop	brew install --cask docker then open -a Docker
- kind	brew install kind
- kubectl	brew install kubectl
- helm	brew install helm

## Build the images

The chart expects the images tagged exactly as below (imagePullPolicy: IfNotPresent):

   ```bash
docker build -t ai-app-fastapi:latest -f Dockerfile.fastapi .
docker build -t ai-app-gradio:latest  -f Dockerfile.gradio .
docker images | grep ai-app   # verify both exist
```
## Create the cluster
   ```bash
kind create cluster
kubectl get nodes             # wait until the node shows Ready
```
## Load the images into Kind

Kind nodes have their own image store, separate from your Docker daemon. Local images must be loaded in explicitly, or pods fail with ErrImageNeverPull:

   ```bash
kind load docker-image ai-app-fastapi:latest ai-app-gradio:latest
```
Verify (optional):

   ```bash
docker exec -it kind-control-plane crictl images | grep ai-app
```
## Install the Helm chart
   ```bash
helm install ai-app ./helm/ai-app -n ai-app --create-namespace
```
## Watch it come up
   ```bash
kubectl get pods -n ai-app -w
```
The pods start in a deliberate cascade — this is expected, not a hang:

- ollama — its init container starts an Ollama server, waits for it, then pulls every model in values.yaml (llama3.2, phi3:mini, qwen2.5:3b, gemma2:2b, nomic-embed-text). First run is slow (several GB of downloads); the pod sits in Init:0/1 → - PodInitializing while this happens.
- fastapi — comes up once ollama is reachable; goes 1/1 after its /ready probe passes.
- gradio — has a wait-for-fastapi init container, so it clears last, after FastAPI answers /health.

Watch the model pull live if you want:

   ```bash
kubectl logs -n ai-app -l component=ollama -c pull-models -f
```
You're done when all three read 1/1 Running. Confirm the models landed:

   ```bash
kubectl exec -n ai-app -c ollama deploy/ai-app-ollama -- ollama list
```
### Access the UI

Gradio's Service is ClusterIP (see note below), so reach it with a port-forward. Leave this command running — it holds the tunnel open:

   ```bash
kubectl port-forward svc/ai-app-gradio 7860:7860 -n ai-app
```
Open http://localhost:7860. Test Standard Chat, switch models in the dropdown, then upload a PDF and try RAG mode.
  - Why ClusterIP, not LoadBalancer: Kind has no cloud load-balancer, so a LoadBalancer Service stays stuck at <pending> forever. gradio.service.type is set to ClusterIP for local Kind and should be switched back to LoadBalancer when deploying to a real cloud (e.g. CoreWeave).

## Config-driven model provisioning

The list of models to pull lives in one place — values.yaml — and the ollama init container loops over it, so the dropdown and the actually-pulled models never drift out of sync:

yaml
# helm/ai-app/values.yaml
ollama:
  models:
    - "llama3.2"
    - "phi3:mini"
    - "qwen2.5:3b"
    - "gemma2:2b"
    - "nomic-embed-text"
yaml
# helm/ai-app/templates/deployment-ollama.yaml (init container)
command:
  - /bin/sh
  - -c
  - |
    ollama serve &
    pid=$!
    until ollama list >/dev/null 2>&1; do echo "waiting for ollama..."; sleep 1; done
    {{- range .Values.ollama.models }}
    ollama pull {{ . }}
    {{- end }}
    kill $pid

### Upgrading / changing models

After editing values.yaml or a template:

   ```bash
helm upgrade ai-app ./helm/ai-app -n ai-app
```
Because models are pulled by the ollama init container, they are only (re)pulled when a new ollama pod is created. If your change didn't alter the pod spec, force a fresh pod:

   ```bash
kubectl rollout restart deploy/ai-app-ollama -n ai-app
```
The rolling update keeps the old pod serving until the new one is healthy — if the new init container fails, you'll see Init:Error / Init:CrashLoopBackOff on the new pod while the old one stays Running.

### Tear down
   ```bash
helm uninstall ai-app -n ai-app
kind delete cluster
```
### Observability: metrics-server

Kind doesn't ship metrics-server, so kubectl top returns Metrics API not available out of the box. Installing it enables resource visibility and is a prerequisite for HPA (autoscaling reads pod CPU/memory from the metrics API).

   ```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```
Kind gotcha: metrics-server can't verify Kind's kubelet serving certs and will sit 0/1 Running until you tell it to skip TLS verification (fine for local dev, never for production):

   ```bash
kubectl patch deployment metrics-server -n kube-system --type='json' \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```
Wait for it to become ready, then read usage:

   ```bash
kubectl get pods -n kube-system -l k8s-app=metrics-server -w
kubectl top pods -n ai-app
kubectl top nodes
```
During inference on this CPU-only setup, the ollama pod saturates its allocation (~4 CPU / ~7.45 GB), which is the direct cause of the multi-second-to-minute response times — see the performance note below.

### SYSTEM ARCHITECTURE

The stack is three decoupled services, deployed and versioned together by the Helm chart. On Kubernetes each service is a Deployment fronted by a ClusterIP Service, with PersistentVolumeClaims backing Ollama's model cache and Gradio's data/vector store.

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
### Kubernetes objects (Helm-managed)
```text
namespace: ai-app
├── Deployment  ai-app-ollama    ─ initContainer pulls models ─ PVC ai-app-ollama-pvc (50Gi)
│     └── Service  ai-app-ollama   (ClusterIP :11434)
├── Deployment  ai-app-fastapi   ─ probes: /health, /ready
│     └── Service  ai-app-fastapi  (ClusterIP :8000)
├── Deployment  ai-app-gradio    ─ initContainer waits for FastAPI ─ PVC ai-app-gradio-pvc (20Gi)
│     └── Service  ai-app-gradio   (ClusterIP :7860)  ← port-forward target
└── ConfigMap   ai-app-config    ─ service URLs, model list, env
```

1. **Gradio UI (`ai-app-gradio-1`)**: The user interface. It handles file uploads (`.pdf`, `.txt`), parses document text, manages the local **ChromaDB** vector instance for RAG context, and connects to an underlying **SQLite** database for chat persistence.
2. **FastAPI (`ai-app-fastapi-1`)**: The routing middleware. It exposes an ingestion gateway (`/ask`), enforces system-wide timeouts, parses requests against strict Pydantic schemas, and handles upstream communication with Ollama.
3. **Ollama (`ai-app-ollama-1`)**: The heavy-computational core. It runs as a localized background service managing raw model weights, execution contexts, and token generation.
4. **Open WebUI (`ai-app-open-webui-1`)**: An optional, feature-rich alternative web console natively paired with the Ollama instance for direct model interaction.

### Project Structure
```text
ai-app/
├── app/
│   └── main.py                 # FastAPI backend (routes + /health, /ready)
├── gradio_app.py               # Gradio frontend entry point
├── chroma_db/                  # Persistent ChromaDB vector store
├── data/                       # SQLite chat_history.db
├── Dockerfile.fastapi          # FastAPI image build
├── Dockerfile.gradio           # Gradio image build
├── docker-compose.yml          # Local-dev stack
├── requirements.txt            # Shared Python dependencies
├── helm/
│   └── ai-app/
│       ├── Chart.yaml
│       ├── values.yaml         # Single source of truth (images, models, resources, probes)
│       └── templates/
│           ├── deployment-ollama.yaml   # + model-pull init container
│           ├── deployment-fastapi.yaml
│           ├── deployment-gradio.yaml   # + wait-for-fastapi init container
│           ├── service-ollama.yaml
│           ├── service-fastapi.yaml
│           ├── service-gradio.yaml
│           ├── configmap.yaml
│           ├── pvc.yaml
│           └── _helpers.tpl
├── docs/                       # Screenshots referenced in this README
└── README.md
```
## Hardware & Resource Thresholds
Running LLMs locally is resource-volatile. The stack idles at a few GB but needs real headroom under load. Whatever you give Docker Desktop (Settings → Resources) is the hard ceiling for the entire Kind cluster, so size it for the cluster plus inference.

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

![alt text](<Screenshot 2026-08-20 at 2.43.03 PM.png>)
---
### Performance Note: CPU vs GPU

On this Kind setup everything runs on CPU, and metrics-server confirms the ollama pod saturates ~4 CPU during generation. As a result a single short prompt against llama3.2 can take tens of seconds to ~1 minute. This is not a bug — it's a CPU doing a GPU's job.

To iterate faster on CPU: use a smaller model (gemma2:2b, phi3:mini), give Docker Desktop more cores, and keep the model warm (the first call is always slowest as weights load into memory).
The real fix is a GPU. The same Helm chart deployed onto a GPU node (nvidia.com/gpu resources + nodeSelector) returns the identical query in low single-digit seconds, with CPU near-idle. That CPU→GPU before/after is the intended demonstration of this project.

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
### Troubleshooting & FAQs

**Kubernetes / Kind**

- kind load → no nodes found for cluster "kind" No cluster exists yet. Run kind create cluster, wait for the node to be Ready, then re-run the load.
- Pods stuck ErrImageNeverPull The image wasn't loaded into Kind, or the tag doesn't match the chart. Rebuild with the exact tags and kind load docker-image ai-app-fastapi:latest ai-app-gradio:latest.
- Gradio unreachable / LoadBalancer stuck <pending> Kind has no cloud LB. Ensure gradio.service.type: ClusterIP in values.yaml and reach the UI via kubectl port-forward svc/ai-app-gradio 7860:7860 -n ai-app.
- localhost:7860 refuses to connect The port-forward dropped (terminal closed, laptop slept, or pod restarted). Restart it. Check the port isn't held by a stale forward with lsof -i :7860, or forward to a different local port - (7861:7860).
- ollama pod Init:Error / Init:CrashLoopBackOff Read the init logs: kubectl logs -n ai-app <ollama-pod> -c pull-models. A /bin/sh: Illegal option error means the init-container command block is mis-indented — the {{- range }}/{{ - end }} and ollama pull lines must align inside the | block. Preview the render with helm template ai-app ./helm/ai-app | grep -A20 pull-models.
- A model 404s (Not Found for url .../api/generate) That model was never pulled. Confirm with kubectl exec -n ai-app -c ollama deploy/ai-app-ollama -- ollama list. Add it to ollama.models in values.yaml and helm upgrade + kubectl - rollout restart deploy/ai-app-ollama, or pull it live: kubectl exec -n ai-app -c ollama deploy/ai-app-ollama -- ollama pull <model>.
- kubectl top → Metrics API not available metrics-server isn't installed. Install it and apply the --kubelet-insecure-tls patch (see Observability).


### 1. I see `onnxruntime cpuid_info warning: Unknown CPU vendor` in the logs. Is it broken?
* **No, this is completely harmless.** 
* **Why it happens:** The underlying ONNX matrix engine searches for an Intel or AMD hardware signature to apply legacy x86 math optimizations. Because it is running inside a Linux Docker container virtualized on top of an Apple M-Series chip, it reads a blank vendor ID (`0`). 
* **Action:** Ignore it. Your vector embeddings are still calculated correctly using native ARM instruction sets.

### 2. The Gradio interface keeps loading indefinitely or says "Error communicating with backend"
This usually indicates an upstream routing or timeout issue. Check the following:
* **Verify FastAPI is awake:** Run `curl http://localhost:8000/`. You should receive a `{"status": "healthy"}` payload.
* **Check Ollama's model state:** Ensure the required model is actually downloaded inside the Ollama container. Run:
  ```   ```bash
  docker compose exec ollama ollama list
  ```
  If your model (e.g., `llama3.2`) is missing, pull it manually:
  ```   ```bash
  docker compose exec ollama ollama pull llama3.2
  ```
  
### 3. How do I completely wipe my vector database and start fresh?
If your PDF chunks become corrupted or you want to delete indexed knowledge bases:
1. Click the **Clear History** button directly inside the Gradio UI. This executes an internal script wrapper that drops the collection and resets the underlying SQLite tables.
2. For a nuclear system reset, bring down the stack and erase the localized data directories on your Mac:
   ```   ```bash
   docker compose down -v
   rm -rf ./chroma_db ./data
   docker compose up -d
   ```

### 4. Docker Desktop is freezing or failing to launch on my Mac
If background hypervisor threads become hung or corrupted:
* Force-terminate all hidden zombie Docker processes via your Mac Terminal:
  ```   ```bash
  pkill -9 -f Docker
  ```
* Clear corrupted GUI layout files (this will not delete your image layers):
  ```   ```bash
  rm -f ~/Library/Group\ Containers/group.com.docker/settings.json
  ```
* Relaunch cleanly: `open -a Docker`



