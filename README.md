#  AGENTIC SRE PIPELINE
### **Autonomous Kubernetes Remediation with Gemini & MCP**

---

## 📌 OVERVIEW
This project is an advanced **Self-Healing Infrastructure** demonstration. It moves away from traditional "if-then" scripts and implements an **Autonomous AI Agent** that can investigate, diagnose, and repair a Kubernetes cluster using the **Model Context Protocol (MCP)**.

---

## 🏗️ SYSTEM ARCHITECTURE
The pipeline is divided into three core layers that work together to solve infrastructure incidents:

### **1. The Sensory System (Golang)**
* **Location:** `go-cluster-agent/`
* **Role:** A high-performance Go daemon that monitors Prometheus metrics. It acts as the "nervous system," identifying OOM (Out Of Memory) risks and triggering the AI.

### **2. The Reasoning Brain (Python & CrewAI)**
* **Location:** `python-ai-orchestrator/`
* **Role:** Powered by **Google Gemini 1.5 Flash** and the **CrewAI** framework. It receives alerts and performs "Chain of Thought" reasoning to decide how to fix the cluster.

### **3. The Execution Hands (MCP Server)**
* **Location:** `kube-mcp/`
* **Role:** A secure **Model Context Protocol** bridge. It allows the AI to securely "talk" to the Kubernetes API to fetch logs and apply patches without hardcoded credentials.



---

## 🛠️ TECH STACK
* **Cloud Native:** Kubernetes, Docker, Minikube
* **Languages:** Golang (Efficiency), Python (AI/ML)
* **AI Core:** CrewAI, Gemini API, Model Context Protocol (MCP)
* **Monitoring:** Prometheus Metrics
* **Security:** Kubernetes RBAC (Role-Based Access Control)

---

## 🔄 THE REMEDIATION LOOP
1. **DETECT:** Go agent identifies a memory spike in a container.
2. **TRIGGER:** Webhook wakes up the Python AI Orchestrator.
3. **INSPECT:** AI uses MCP to read **Pod Logs** and **Resource Limits**.
4. **PATCH:** AI applies a **Kubernetes Patch** to increase memory limits (e.g., to 512Mi).
5. **VERIFY:** Agent confirms the fix and generates a final SRE report.

---

## 📁 REPOSITORY STRUCTURE
```text
Agentic-SRE-Pipeline/
├── go-cluster-agent/    # Metrics watcher & K8s RBAC security
├── python-ai-brain/     # CrewAI Orchestrator (The "Brain")
├── kube-mcp/            # Custom MCP Server (The "Hands")
├── legacy/              # Archived static automation scripts
└── mcp-deployment.yaml  # K8s manifest for the AI bridge
```

---

##  QUICK START

### **Step 1: Apply Cluster Security**
```bash
kubectl apply -f go-cluster-agent/rbac.yaml
```

### **Step 2: Deploy the MCP Bridge**
```bash
cd kube-mcp
docker build -t local-kube-mcp:latest .
kubectl apply -f ../mcp-deployment.yaml
```

### **Step 3: Launch the AI Orchestrator**
```bash
cd python-ai-orchestrator
pip install -r requirements.txt
python server.py
```
