# Kubernetes Helm Deployment Guide for AI App

This guide walks you through deploying your AI App (Ollama + FastAPI + Gradio) to Kubernetes using Helm.

## Prerequisites

- Local Kubernetes cluster running (`kind` cluster should be set up)
- `kubectl` installed and configured
- `helm` installed
- Docker images built and available

---

## Quick Start

### Step 1: Build Docker Images

From your ai-app repo root:

```bash
# Build FastAPI image
docker build -f Dockerfile.fastapi -t ai-app-fastapi:latest .

# Build Gradio image
docker build -f Dockerfile.gradio -t ai-app-gradio:latest .

# Load images into kind cluster
kind load docker-image ai-app-fastapi:latest --name ai-app
kind load docker-image ai-app-gradio:latest --name ai-app
```

### Step 2: Create Namespace

```bash
kubectl create namespace ai-app
```

### Step 3: Deploy with Helm

```bash
helm install ai-app ./helm/ai-app \
  -n ai-app \
  --values helm/ai-app/values.yaml
```

For local testing with NodePort:
```bash
helm install ai-app ./helm/ai-app \
  -n ai-app \
  --set gradio.service.type=NodePort
```

### Step 4: Check Status

```bash
# Watch pods startup
kubectl get pods -n ai-app -w

# Get services
kubectl get svc -n ai-app

# View logs
kubectl logs -n ai-app -l app.kubernetes.io/name=ai-app -f
```

### Step 5: Access Application

**Local (kind):**
```bash
# Port forward
kubectl port-forward -n ai-app svc/ai-app-gradio 7860:7860

# Access at http://localhost:7860
```

**Cloud (CoreWeave):**
```bash
# Get LoadBalancer external IP
kubectl get svc -n ai-app ai-app-gradio

# Access at http://<EXTERNAL-IP>:7860
```

---

## Helm Commands Cheat Sheet

```bash
# Validate chart
helm lint ./helm/ai-app

# Dry-run
helm install ai-app ./helm/ai-app -n ai-app --dry-run --debug

# View rendered manifests
helm template ai-app ./helm/ai-app -n ai-app

# Upgrade deployment
helm upgrade ai-app ./helm/ai-app -n ai-app

# Get values
helm get values ai-app -n ai-app

# History
helm history ai-app -n ai-app

# Rollback
helm rollback ai-app 1 -n ai-app

# Uninstall
helm uninstall ai-app -n ai-app
```

---

## Customization

### Scale Replicas
```bash
helm install ai-app ./helm/ai-app -n ai-app \
  --set gradio.replicaCount=3 \
  --set fastapi.replicaCount=3
```

### Change Resource Limits
```bash
helm install ai-app ./helm/ai-app -n ai-app \
  --set ollama.resources.limits.memory=16Gi \
  --set gradio.resources.limits.cpu=4
```

### Enable GPU Support (CoreWeave)
Edit values.yaml or:
```bash
helm install ai-app ./helm/ai-app -n ai-app \
  --set ollama.resources.requests."nvidia\.com/gpu"=1 \
  --set ollama.resources.limits."nvidia\.com/gpu"=1
```

---

## Troubleshooting

### Pods Pending
```bash
kubectl describe pod <pod-name> -n ai-app
```

### Pods Crashing
```bash
kubectl logs -n ai-app <pod-name> --previous
```

### Service Can't Communicate
```bash
kubectl exec -it -n ai-app <pod-name> -- nslookup ai-app-ollama
kubectl exec -it -n ai-app <pod-name> -- curl http://ai-app-ollama:11434
```

### PVC Not Binding
```bash
kubectl get pvc -n ai-app
kubectl get storageclass
```

---

## Cleanup

```bash
helm uninstall ai-app -n ai-app
kubectl delete namespace ai-app
```
