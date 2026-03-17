# 🍯 Engineering Autonomous Deception (Project CyberChain)

## 🛡️ Overview
[cite_start]Traditional honeypots are static and easily fingerprinted by sophisticated adversaries[cite: 2, 3]. [cite_start]This project introduces a **Conversational LLM-Based Honeypot** designed for the **CyberChain Global Hackathon (Challenge 5)**[cite: 3]. [cite_start]By utilizing Large Language Models, this system resolves the tension between low-interaction safety and high-interaction depth, creating a dynamic, adaptive environment that lures attackers into revealing their intent[cite: 3, 4].

The system doesn't just sit there—it engages. [cite_start]It simulates vulnerable services like SSH panels and administrative APIs with a level of conversational fidelity that maximizes attacker dwell time while silently classifying every tactic against the **MITRE ATT&CK Framework**[cite: 3, 35].

---

## ✨ Key Features
* [cite_start]**Dynamic Persona Engine:** Uses LLMs (GPT-4/LLaMA3) to maintain consistent, believable personalities that avoid "persona breaks" and moralizing, ensuring attackers remain engaged[cite: 18, 30, 31].
* [cite_start]**Real-time TTP Classification:** Employs an "Analysis Agent" to map attacker commands—such as `nmap` scans or `cat /etc/passwd`—directly to MITRE ATT&CK Technique IDs ($TID$)[cite: 35, 36, 38].
* [cite_start]**Adaptive Dwell Time:** Incorporates Chain-of-Thought (CoT) reasoning to understand command consequences and generate realistic, stateful responses that prolong the attack session[cite: 22, 23, 25].
* [cite_start]**Automated Incident Reporting:** Automatically generates "Attacker Intelligence Reports" upon session termination, featuring chronological narratives, identified attack types, and frequency summaries[cite: 42, 43, 44].
* [cite_start]**Containerized Deployment:** Optimized for low-latency performance using Docker with minimal base images like `debian-slim` or `alpine`[cite: 52, 54, 56].

---

## 🚀 Quick Start

### Prerequisites
* [cite_start]Docker & Docker Compose [cite: 52]
* [cite_start]LLM API Key (OpenAI, Groq, or Local vLLM endpoint) [cite: 10, 74]

### Installation
1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/kandeel/conversational-honeypot.git](https://github.com/kandeel/conversational-honeypot.git)
    cd conversational-honeypot
    ```
2.  **Configure your environment:**
    ```bash
    echo "LLM_API_KEY=your_key_here" > .env
    echo "AUTH_POLICY=accept-all" >> .env
    ```
3.  **Launch the honeypot:**
    ```bash
    docker-compose up --build
    ```

---

## 📊 System Architecture
* [cite_start]**The Protocol Interface:** Uses Paramiko (SSH) or FastAPI (HTTP) to manage connection handshakes and credential capture[cite: 8, 10].
* [cite_start]**The Orchestrator:** A middleware that maintains a stateful representation of the environment (System State Register $SR$) and interaction history ($H$)[cite: 10, 12].
* [cite_start]**The LLM Backend:** The generative engine (GPT-4, LLaMA3, or vLLM) that emulates system behavior and terminal outputs[cite: 10, 18].
* [cite_start]**The Telemetry Analyst:** A RAG-enhanced module that performs semantic similarity searches against the MITRE ATT&CK dataset to tag events[cite: 10, 39, 40].

---

## 📝 MITRE ATT&CK Mapping
The system identifies and logs techniques including:
* [cite_start]**T1110:** Brute Force (Credential access attempts) [cite: 37, 38]
* [cite_start]**T1083:** File and Directory Discovery (Probing `/etc/` or `.env`) [cite: 37, 38]
* [cite_start]**T1046:** Network Service Scanning (Inbound `nmap` activity) [cite: 38]
* [cite_start]**T1611:** Escape to Host (Privileged container escape attempts) [cite: 38]

---

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for more information.

[cite_start]**Built for the CyberChain Global Hackathon 2026.** [cite: 3]
