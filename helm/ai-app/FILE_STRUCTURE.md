# AI-App Repository File Structure - Helm Chart

This document shows the complete directory structure for your helm chart that should be added to your ai-app repository.

```
ai-app/
├── app/                          (existing)
│   ├── main.py
│   └── ...
├── gradio_app.py                 (existing)
├── docker-compose.yml            (existing)
├── Dockerfile.fastapi            (existing)
├── Dockerfile.gradio             (existing)
├── requirements.txt              (existing)
├── README.md                     (existing)
│
├── helm/                         ← NEW DIRECTORY
│   └── ai-app/                   ← Chart directory
│       ├── Chart.yaml            ← Chart metadata
│       ├── values.yaml           ← Default configuration (ALL SETTINGS GO HERE)
│       ├── DEPLOYMENT_GUIDE.md   ← How to deploy the chart
│       │
│       └── templates/            ← Kubernetes manifests (templated)
│           ├── _helpers.tpl      ← Reusable template functions
│           ├── configmap.yaml    ← Configuration values
│           ├── pvc.yaml          ← Persistent volumes
│           ├── deployment-ollama.yaml
│           ├── deployment-fastapi.yaml
│           ├── deployment-gradio.yaml
│           ├── service-ollama.yaml
│           ├── service-fastapi.yaml
│           └── service-gradio.yaml
│
└── (future files - Week 3)
    └── .github/workflows/        ← GitHub Actions CI/CD
```

---

## Files to Create (11 files total)

### Root Chart Files (3 files)

1. **helm/ai-app/Chart.yaml**
   - Metadata about your Helm chart
   - Version, name, description

2. **helm/ai-app/values.yaml**
   - DEFAULT configuration for all components
   - ALL ports, replicas, resources, models, etc.
   - **This is the only file you change to customize deployments**

3. **helm/ai-app/DEPLOYMENT_GUIDE.md**
   - Instructions for deploying to kind, CoreWeave, etc.

### Template Helper (1 file)

4. **helm/ai-app/templates/_helpers.tpl**
   - Reusable functions used in all templates
   - Chart name expansion, labels, selectors

### Configuration (1 file)

5. **helm/ai-app/templates/configmap.yaml**
   - Kubernetes ConfigMap with all env variables
   - Auto-generated service URLs
   - References values from values.yaml

### Storage (1 file)

6. **helm/ai-app/templates/pvc.yaml**
   - PersistentVolumeClaim for Ollama (50Gi)
   - PersistentVolumeClaim for Gradio (20Gi)

### Deployments (3 files)

7. **helm/ai-app/templates/deployment-ollama.yaml**
   - Ollama Deployment configuration
   - Probes, resources, volume mounts

8. **helm/ai-app/templates/deployment-fastapi.yaml**
   - FastAPI Deployment configuration
   - Init container to wait for Ollama

9. **helm/ai-app/templates/deployment-gradio.yaml**
   - Gradio Deployment configuration
   - Init container to wait for FastAPI

### Services (3 files)

10. **helm/ai-app/templates/service-ollama.yaml**
    - ClusterIP Service for Ollama (internal only)

11. **helm/ai-app/templates/service-fastapi.yaml**
    - ClusterIP Service for FastAPI (internal only)

12. **helm/ai-app/templates/service-gradio.yaml**
    - LoadBalancer/NodePort Service for Gradio (external access)

---

## What Each File Does

### values.yaml (The Brain)
- **All configuration in ONE place**
- Ports, replicas, resources, storage size, models, environment variables
- Change here → redeploy → new configuration
- No code changes needed

### ConfigMap (The Delivery System)
- Takes values from values.yaml
- Creates environment variables for pods
- Injected into containers at runtime

### Deployments (The Workers)
- Read from ConfigMap
- Use resources/replicas from values.yaml
- Manage pod creation and self-healing
- Include health checks (liveness/readiness probes)
- Init containers ensure startup order

### Services (The Networking)
- Expose pods to network
- Ollama & FastAPI: ClusterIP (internal)
- Gradio: LoadBalancer (external)

### PVC (The Storage)
- Persistent volumes for Ollama models (50Gi)
- Persistent volumes for Gradio data (20Gi)
- Survives pod restarts

---

## How to Add These Files to Your Repo

### Option 1: Manual Copy (Simple)
```bash
# Create directories
mkdir -p ~/Projects/personal_git/ai-app/helm/ai-app/templates

# Copy all files from downloaded package into these directories
# Then commit to git
cd ~/Projects/personal_git/ai-app
git add helm/
git commit -m "Add Helm chart for Kubernetes deployment"
git push
```

### Option 2: Use the Download
1. Download all files I'm sending you
2. Create the directory structure locally
3. Copy files into appropriate folders
4. Commit and push

---

## Key Points

✅ **All settings centralized in values.yaml**
✅ **No hardcoding in templates**
✅ **Production-ready structure**
✅ **Same chart works for local (kind) and cloud (CoreWeave)**
✅ **Easy to customize without code changes**

---

## Next Steps

1. Add these 12 files to your repo
2. Add `/health` endpoint to FastAPI (app/main.py)
3. Build Docker images
4. Load into kind cluster
5. Deploy with Helm
6. Test Gradio UI at localhost:7860
