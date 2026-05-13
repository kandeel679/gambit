<![CDATA[<div align="center">

# ⬢ GAMBIT

### Agentic AI-Powered Honeypot Orchestrator

*Automatically clone, synthesize, deploy, and analyze high-fidelity honeypot systems using LLM-driven intelligence.*

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Required-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

</div>

## Overview

**Gambit** is a fully autonomous honeypot orchestration platform that creates realistic digital-twin decoy systems. It connects to a real "Source of Truth" server, clones its DNA (metadata, services, users, file structure), uses an LLM to synthesize a convincing honeypot blueprint, deploys it as an isolated Docker container, and then proxies attacker SSH sessions through it — all while performing live MITRE ATT&CK analysis and generating forensic reports.

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Phase 1    │    │   Phase 2    │    │   Phase 3    │    │   Phase 4    │    │   Phase 5    │    │   Phase 6    │
│     DNA      │───▶│  Blueprint   │───▶│   Docker     │───▶│    Live      │───▶│   Agentic    │───▶│   Forensic   │
│  Extraction  │    │  Synthesis   │    │  Deployment  │    │    Proxy     │    │   Analysis   │    │   Report     │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
   CloneSource         LLMClient         Generator         ProxyServer        AnalysisAgent        Reporter
    (SSH →             (Gemini /         (Dockerfile       (SSH Honeypot       (Live TTP            (LLM Post-
   Metadata)            Ollama)           → Docker)         Broker)            Mapping)             Incident)
```

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **🧬 DNA Extraction** | SSH into any target server and extract OS, kernel, users, services, network topology, cron jobs, and file hierarchies |
| **🧠 LLM Blueprint Synthesis** | Gemini or Ollama analyze metadata to generate a full Dockerfile, package list, and realistic honey-artifacts (fake credentials, logs, configs) |
| **🐳 Isolated Docker Deployment** | Builds and deploys the honeypot in a strictly isolated Docker network (`internal=true`) — no internet access for the container |
| **🔀 Dual-Stream SSH Proxy** | Transparent SSH proxy that forwards attacker sessions to the Docker container while simultaneously streaming commands to the AI analysis pipeline |
| **🎯 Live MITRE ATT&CK Mapping** | Every attacker command is analyzed in real-time by an LLM, mapped to MITRE ATT&CK TTPs, and used to build a live adversary profile |
| **📊 Forensic Reporting** | On session disconnect, a comprehensive Markdown report is generated with attacker profile, connection info, attack timeline, and strategic recommendations |
| **🖥️ Web GUI** | Beautiful dark-themed web interface for configuration, deployment, live log monitoring, and report viewing |
| **🔐 Realistic Auth** | Honeypot accepts only common weak credentials (root/admin, admin/password, etc.) — attackers must brute-force their way in |

---

## 🏗️ Architecture

```
gambit2/
├── main.py                 # Entry point — launches the web GUI server
├── gui_server.py           # HTTP server with REST API + static file serving
├── clone_source.py         # Phase 1: SSH-based remote metadata extraction
├── llm_client.py           # Phase 2: LLM blueprint synthesis (Gemini/Ollama)
├── generator.py            # Phase 3: Dockerfile generation + Docker deployment
├── proxy_server.py         # Phase 4: SSH honeypot proxy with dual-stream
├── analysis_agent.py       # Phase 5: Real-time MITRE ATT&CK analysis
├── reporter.py             # Phase 6: Post-incident forensic report generation
├── gui_static/
│   ├── index.html          # Web interface markup
│   ├── app.js              # Frontend logic (form handling, live log polling)
│   └── styles.css          # Dark glassmorphism theme
├── build_context/          # Auto-generated Docker build context (Dockerfile + artifacts)
├── .env                    # Configuration (API keys, target credentials, LLM provider)
├── requirements.txt        # Python dependencies
├── source_metadata.json    # Extracted target metadata (auto-generated)
├── gambit_blueprint.json   # LLM-generated honeypot blueprint (auto-generated)
└── report_session_*.md     # Forensic reports (auto-generated per attacker session)
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Docker** (running daemon)
- **SSH access** to a target server (the "Source of Truth" to clone)
- **LLM Provider** — one of:
  - [Google Gemini API Key](https://aistudio.google.com/apikey)
  - [Ollama](https://ollama.ai/) running locally or on a remote host

### 1. Clone & Install

```bash
git clone <repository-url>
cd gambit2/gambit2
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create or edit the `.env` file:

```env
# LLM Provider: "gemini" or "ollama"
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here

# Or for Ollama:
# LLM_PROVIDER=ollama
# OLLAMA_HOST=http://localhost:11434
# OLLAMA_MODEL=llama3.1

# Target server to clone (can also be set via GUI)
TARGET_IP=192.168.1.100
TARGET_PORT=22
TARGET_USER=root
TARGET_PASS=your_password
```

### 3. Launch

```bash
python main.py
```

The web interface opens automatically at **http://localhost:8080**.

---

## 🖥️ Web Interface

### Dashboard

The dashboard provides a single-page control center:

1. **Honeypot Orchestration Form** — Configure target server credentials and LLM provider
2. **🚀 Launch** — Click to start the full 4-phase deployment pipeline
3. **Deployment Status Console** — Real-time progress of each phase (DNA → Blueprint → Docker → Proxy)
4. **Live System Logs** — Streams all backend activity: proxy connections, analysis agent TTP mappings, forensic report generation

### Analytics

Switch to the Analytics tab to browse generated forensic reports:
- Session list with timestamps
- Full Markdown-rendered reports with attacker profiles, MITRE ATT&CK mappings, and recommendations

---

## ⚙️ How It Works

### Phase 1 — DNA Extraction (`clone_source.py`)

Connects to the target server via SSH (using Paramiko) and extracts:
- OS release & kernel version
- Environment variables
- Active users (UID ≥ 1000)
- Network topology (ARP table, listening ports, established connections)
- Running services & cron jobs
- File hierarchy samples (`/var/www`, `/etc`, `/home`)

Output: `source_metadata.json`

### Phase 2 — Blueprint Synthesis (`llm_client.py`)

Sends the extracted metadata to an LLM (Gemini 2.5 Flash or Ollama) with a detailed prompt requesting:
- Industry vertical identification
- System persona description
- Complete Dockerfile instructions
- Realistic honey-artifacts (fake credentials, logs, configs placed at common adversary loot paths)

Output: `gambit_blueprint.json`

### Phase 3 — Docker Deployment (`generator.py`)

Programmatically:
1. Creates an isolated Docker bridge network (`internal=true` — no internet)
2. Generates a Dockerfile from the blueprint
3. Writes honey-artifacts to the build context
4. Builds the Docker image and deploys a container

### Phase 4 — SSH Proxy Broker (`proxy_server.py`)

Starts a Paramiko SSH server on port **2222** that:
- Accepts only weak/common credentials (realistic brute-force simulation)
- Records all authentication attempts (including failed ones)
- Captures attacker IP, port, and connection metadata
- Forwards commands to the Docker container via `docker exec`
- Maintains persistent `cd` state across commands
- Handles backspace, Ctrl+C, and terminal control characters

### Phase 5 — Real-Time Analysis (`analysis_agent.py`)

Every attacker command is dispatched asynchronously to the LLM for:
- MITRE ATT&CK TTP identification (technique ID, name, intent)
- Actor type classification (human vs. bot)
- Skill level assessment
- Live profile evolution

All analysis threads are tracked and joined before reporting to ensure no commands are lost.

### Phase 6 — Forensic Reporting (`reporter.py`)

Triggered on attacker disconnect. Sends the complete session profile to the LLM to generate a Markdown report containing:

1. **Executive Summary** — Actor type, skill level, primary intent
2. **Attacker Connection Profile** — Source IP, port, credentials used, session duration
3. **MITRE ATT&CK Heatmap** — All TTPs triggered with descriptions
4. **Attack Timeline** — Chronological command breakdown
5. **Adversary Behavioral Profile** — Skill assessment, motivation, tradecraft indicators
6. **Strategic Recommendations** — Vulnerability patching guidance

---

## 🔌 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/config` | Returns current configuration from `.env` |
| `POST` | `/api/launch` | Triggers the full deployment pipeline |
| `GET` | `/api/status` | Returns deployment progress, logs, and completion status |
| `GET` | `/api/live-logs?since=N` | Returns system logs from index N onwards (incremental) |
| `GET` | `/api/logs` | Lists all forensic report files |
| `GET` | `/api/logs/:filename` | Returns the content of a specific report |

---

## 🔐 Accepted Honeypot Credentials

The SSH proxy accepts these common weak credentials to simulate a realistic target:

| Username | Passwords |
|----------|-----------|
| `root` | `root`, `admin`, `password`, `123456`, `toor` |
| `admin` | `admin`, `password`, `123456` |
| `user` | `user`, `password` |
| `test` | `test` |
| `ubuntu` | `ubuntu` |
| `guest` | `guest` |
| `pi` | `raspberry` |

All failed and successful attempts are logged and included in forensic reports.

---

## 🛡️ Security Considerations

> **⚠️ WARNING:** Gambit is a honeypot system designed for controlled security research environments.

- The Docker honeypot runs on an **isolated internal network** — it cannot reach the internet
- The SSH proxy runs on port **2222** — do not expose this to the public internet without proper network segmentation
- API keys and credentials in `.env` should be treated as secrets
- Forensic reports may contain attacker IPs and credentials — store them securely
- Always run Gambit in an isolated lab or behind a properly configured firewall

---

## 📋 Requirements

```
paramiko          # SSH client/server
docker            # Docker SDK for Python
pydantic          # Data validation
python-dotenv     # Environment variable management
google-genai      # Google Gemini API client
requests          # HTTP client (for Ollama API)
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<div align="center">

*Built for cyber deception research. Deploy responsibly.*

**⬢ Gambit** — *The best defense is a convincing decoy.*

</div>
]]>
