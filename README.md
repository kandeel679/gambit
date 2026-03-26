<![CDATA[# ⬢ Gambit — AI-Powered Honeypot Orchestrator
**CyberChain Hackathon — Challenge 5 (Honeypot Conversational)**

> Automatically clone real servers, build convincing decoys, and catch attackers with AI-driven forensic analysis.

---

## What Is Gambit?

Gambit is an autonomous honeypot platform that:
1. **Clones** a real server's identity (OS, services, users, file structure) via SSH
2. **Synthesizes** a convincing digital-twin blueprint using an LLM (Gemini / Ollama)
3. **Deploys** the decoy as an isolated Docker container
4. **Traps** attackers through a realistic SSH proxy with weak-credential brute-force simulation
5. **Analyzes** every command in real-time against the MITRE ATT&CK framework
6. **Generates** forensic reports with attacker profiling, IP attribution, and recommendations

---

## How to Use

### Prerequisites

| Requirement | Details |
|-------------|---------|
| **Python** | 3.10 or higher |
| **Docker** | Running daemon (`docker ps` should work) |
| **Target Server** | Any Linux machine with SSH access (the server to clone) |
| **LLM Provider** | Google Gemini API key **or** Ollama running locally/remotely |

### Step 1 — Install

```bash
cd gambit2/gambit2
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2 — Configure

Edit the `.env` file (or configure via the GUI later):

```env
# Choose your LLM: "gemini" or "ollama"
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here

# Or use Ollama instead:
# LLM_PROVIDER=ollama
# OLLAMA_HOST=http://localhost:11434
# OLLAMA_MODEL=llama3.1

# Target server to clone
TARGET_IP=192.168.1.100
TARGET_PORT=22
TARGET_USER=root
TARGET_PASS=your_password
```

### Step 3 — Launch the GUI

```bash
python main.py
```

Your browser opens automatically to **http://localhost:8080**.

### Step 4 — Deploy the Honeypot

1. On the **Dashboard**, fill in your target server's IP, SSH port, username, and password
2. Select your LLM provider (Gemini or Ollama)
3. Click **🚀 Launch Gambit Orchestrator**
4. Watch the 4 phases execute in the **Deployment Status** console:
   - **Phase 1** — Connects to target, extracts system DNA
   - **Phase 2** — LLM synthesizes a honeypot blueprint
   - **Phase 3** — Docker image built and container deployed
   - **Phase 4** — SSH proxy goes live on port 2222

### Step 5 — Catch Attackers

Once deployed, the honeypot listens on **port 2222**. Attackers connecting via SSH must brute-force their way in using weak credentials:

```bash
# Example: an attacker tries to connect
ssh root@your-server-ip -p 2222
# Password: admin  ← accepted (weak credential)
```

Accepted credential pairs include `root/admin`, `admin/password`, `test/test`, `pi/raspberry`, and others.

### Step 6 — Monitor Live

The **Live System Logs** panel on the dashboard streams everything in real-time:
- 🔐 Auth attempts (failed & successful)
- ⚡ Commands executed by the attacker
- 🎯 MITRE ATT&CK TTP mappings from the analysis agent
- 📊 Forensic report generation events

### Step 7 — View Reports

1. Switch to the **Analytics** tab in the sidebar
2. Select any session from the list
3. View the full forensic report including:
   - Attacker IP address and connection profile
   - Credentials used (with all failed attempts)
   - Full command timeline
   - MITRE ATT&CK technique breakdown
   - Adversary skill level and motivation assessment
   - Security recommendations

---

## Architecture

```
Attacker ──SSH──▶ [Port 2222: SSH Proxy] ──docker exec──▶ [Isolated Honeypot Container]
                       │                                          │
                       ▼                                          │
              [Analysis Agent]                                    │
              (Live TTP Mapping)                                  │
                       │                                          │
                       ▼                                          │
              [Forensic Reporter]◀────── on disconnect ───────────┘
              (Full Markdown Report)
```

| Module | File | Role |
|--------|------|------|
| Entry Point | `main.py` | Launches the web GUI |
| Web Server | `gui_server.py` | HTTP API + static file serving + live log streaming |
| DNA Extractor | `clone_source.py` | SSH metadata extraction from source server |
| Blueprint Synth | `llm_client.py` | LLM-driven Dockerfile and artifact generation |
| Docker Engine | `generator.py` | Builds image, creates isolated network, deploys container |
| SSH Proxy | `proxy_server.py` | Paramiko-based honeypot with dual-stream architecture |
| Analysis Agent | `analysis_agent.py` | Real-time MITRE ATT&CK TTP classification |
| Reporter | `reporter.py` | Post-incident forensic report generation |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/config` | Current `.env` configuration |
| `POST` | `/api/launch` | Start full deployment pipeline |
| `GET` | `/api/status` | Deployment progress and logs |
| `GET` | `/api/live-logs?since=N` | Incremental live system logs |
| `GET` | `/api/logs` | List forensic report files |
| `GET` | `/api/logs/:filename` | Read a specific report |

---

## ⚠️ Security Warning

- Run Gambit **only in isolated lab environments** — never expose port 2222 to the public internet without proper segmentation
- The Docker honeypot container is on an **internal-only network** (no internet access)
- Never commit real API keys — use `.env` (already in `.gitignore`)
- Forensic reports contain attacker data — store and handle securely

---

## Tech Stack

- **Python 3** — Core language
- **Paramiko** — SSH client/server
- **Docker SDK** — Container orchestration
- **Google Gemini / Ollama** — LLM providers
- **Vanilla HTML/CSS/JS** — Web interface (no frameworks)

---

*Built for the CyberChain Hackathon. Deploy responsibly.*
]]>
