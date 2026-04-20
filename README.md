# 🤖 Agentic SRE Pipeline

An autonomous Site Reliability Engineering (SRE) system that detects, investigates, and remediates Kubernetes pod memory issues in real-time — with zero human intervention.

> **Alert fires → AI wakes up → Investigates → Restarts → Escalates → Patches → Silence.**

---

## 📽️ Demo Flow

| Step | What Happens |
|------|-------------|
| 1️⃣ | Go agent detects pod memory > 80% of limit and fires alert |
| 2️⃣ | AI orchestrator receives alert and spins up an AI agent |
| 3️⃣ | AI checks limits, reads logs, decides to **restart** deployment |
| 4️⃣ | Problem returns → AI recognizes restart was ineffective |
| 5️⃣ | AI **escalates** and patches memory limit to 2x |
| 6️⃣ | Pod stabilizes, Go agent goes silent ✅ |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Kubernetes Cluster                  │
│                                                     │
│  ┌─────────────────┐      ┌──────────────────────┐  │
│  │  Go Cluster     │      │   Kube MCP Server    │  │
│  │  Agent          │      │   (Python/Flask)     │  │
│  │                 │      │                      │  │
│  │ • Queries       │      │ • Receives NL        │  │
│  │   Prometheus    │      │   commands from AI   │  │
│  │ • Computes      │      │ • Translates to K8s  │  │
│  │   memory %      │      │   API calls          │  │
│  │ • Fires HTTP    │      │ • Patch / Restart /  │  │
│  │   alert > 80%   │      │   Logs / Limits      │  │
│  └────────┬────────┘      └──────────────────────┘  │
│           │  alert                  ▲                │
└───────────┼─────────────────────────│───────────────┘
            │ HTTP POST               │ HTTP POST
            ▼                         │ (NL commands)
┌───────────────────────────────────────────────────┐
│           Python AI Orchestrator                  │
│                  (Flask + CrewAI)                 │
│                                                   │
│  • Receives alerts from Go agent                  │
│  • Deduplicates with 30s cooldown                 │
│  • Tracks restart history for escalation          │
│  • Spins up GPT-4o-mini powered AI agent          │
│  • Agent uses MCP tool to act on the cluster      │
└───────────────────────────────────────────────────┘
```

---

## 🧩 Components

### 1. Go Cluster Agent (`go-cluster-agent/`)
Runs **inside** the Kubernetes cluster as a deployment. Every 5 seconds it:
- Queries Prometheus for real-time memory usage and limits per pod
- Calculates usage as a percentage of the configured limit
- Fires an HTTP alert to the AI orchestrator if any pod exceeds **80%**
- Enforces a 30-second per-pod cooldown to prevent duplicate alerts

### 2. Python AI Orchestrator (`python-ai-orchestrator/`)
Runs **outside** the cluster on your local machine. On each alert it:
- Deduplicates using a 30-second cooldown per deployment
- Checks if a restart was attempted in the last 2 minutes (escalation tracking)
- Builds a context-aware task and hands it to a **CrewAI + GPT-4o-mini** agent
- The agent uses the MCP tool to get limits, read logs, restart, or patch
- Records outcomes for escalation decisions on future alerts

### 3. Kube MCP Server (`kube-mcp/`)
Runs **inside** the cluster. Translates the AI's natural language commands into real Kubernetes API calls:

| AI Says | MCP Does |
|---------|----------|
| `get limits` | Reads deployment memory limits from the K8s API |
| `get logs for pod <name>` | Fetches last 20 log lines (with fallback if pod is gone) |
| `restart deployment` | Triggers rolling restart via annotation patch |
| `patch memory to <value>Mi` | Patches deployment memory limits and requests |

---

## 🔁 Escalation Logic

```
Alert #1 (first time)
    └── AI restarts deployment  ← cheapest fix
    
Alert #2 (within 2 minutes of restart)
    └── Orchestrator injects escalation context
    └── AI patches memory limit to 2x current value  ← permanent fix
    
No more alerts
    └── Pod usage is now well below 80% threshold ✅
```

---

## 📁 Project Structure

```
Agenti-SRE-Pipeline/
│
├── go-cluster-agent/
│   ├── incluster.go       # Main loop — runs inside K8s, lists pods, triggers metrics
│   ├── metrics.go         # Queries Prometheus, computes %, fires HTTP alerts
│   ├── deployment.yaml    # K8s Deployment manifest for the Go agent (10Mi limit)
│   ├── rbac.yaml          # ServiceAccount, Role, RoleBinding for cluster access
│   ├── dockerfile         # Builds the Go agent Docker image
│   └── go.mod / go.sum    # Go dependencies (k8s client-go, apimachinery)
│
├── python-ai-orchestrator/
│   ├── server.py          # Flask server — receives alerts, runs CrewAI agent
│   └── requirements.txt   # Python deps (flask, crewai, python-dotenv)
│
├── kube-mcp/
│   ├── mcp_server.py      # Flask server — NL to K8s API translation layer
│   └── dockerfile         # Builds the MCP server Docker image
│
└── mcp-deployment.yaml    # K8s Deployment + Service for the MCP server
```

---

## 🚀 Getting Started

### Prerequisites
- Kubernetes cluster (e.g. Docker Desktop, Minikube)
- Prometheus installed in the cluster
- Docker
- Python 3.10+
- Go 1.21+
- OpenAI API key

### 1. Build & Deploy the Go Agent

```bash
cd go-cluster-agent
docker build -t incluster-agent:latest .
kubectl apply -f rbac.yaml
kubectl apply -f deployment.yaml
```

### 2. Build & Deploy the MCP Server

```bash
cd kube-mcp
docker build -t local-kube-mcp:latest .
kubectl apply -f ../mcp-deployment.yaml
```

### 3. Port-Forward the MCP Server

```bash
kubectl port-forward svc/kube-mcp-service 8080:80
```

### 4. Run the AI Orchestrator

```bash
cd python-ai-orchestrator
pip install -r requirements.txt
# Create a .env file with your OpenAI key:
# OPENAI_API_KEY=sk-...
python server.py
```

---

## 🔧 Key Configuration

| Setting | Location | Default | Purpose |
|---------|----------|---------|---------|
| Memory alert threshold | `metrics.go` | `80%` | Fires alert above this percentage |
| Alert cooldown | `metrics.go` | `30s` | Prevents duplicate pod alerts |
| Investigation cooldown | `server.py` | `30s` | Prevents parallel AI runs per deployment |
| Escalation window | `server.py` | `120s` | Restart within this window → escalate to patch |
| Pod memory limit | `deployment.yaml` | `10Mi` | Deliberately small to trigger alerts |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Cluster Agent | Go + Kubernetes `client-go` |
| Metrics | Prometheus + PromQL |
| AI Orchestrator | Python + Flask + CrewAI |
| LLM | OpenAI GPT-4o-mini |
| MCP Server | Python + Flask + Kubernetes Python Client |
| Infrastructure | Kubernetes + Docker |

---

## 💡 How It's Different

Most monitoring tools alert humans. This pipeline **alerts an AI** that:
- Reasons about the problem using live cluster data
- Picks the cheapest fix first (restart)
- Remembers what it already tried
- Escalates autonomously when the first fix fails
- Patches the root cause without human involvement
