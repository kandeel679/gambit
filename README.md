🍯 Conversational AI Honeypot (Project CyberChain)

🛡️ Overview

Traditional honeypots are static and easily detected by sophisticated attackers. This project introduces a Conversational Honeypot that utilizes Large Language Models (LLMs) to dynamically simulate vulnerable services (SSH, Admin APIs, Login Portals).

The system doesn't just sit there—it engages. It talks back, feigns incompetence, leaks "sensitive" breadcrumbs, and maintains attacker dwell time while silently classifying every move against the MITRE ATT&CK Framework.

✨ Key Features

Dynamic Persona Engine: Uses Gemini 2.5 Flash to simulate a panicked or negligent system administrator responding to unauthorized access.

Real-time TTP Classification: Automatically maps attacker commands and behaviors to MITRE ATT&CK techniques.

Adaptive Dwell Time: Automatically generates "system friction" (fake errors, slow responses) to keep attackers engaged and gathering data.

Automated Incident Reporting: Generates a comprehensive session report with an executive summary, timeline of events, and attack hypotheses.

Containerized Deployment: Ready for real-world deployment via Docker in seconds.

🚀 Quick Start

Prerequisites

Docker & Docker Compose

Google Gemini API Key

Installation

Clone the repository:

git clone [https://github.com/your-org/conversational-honeypot.git](https://github.com/your-org/conversational-honeypot.git)
cd conversational-honeypot


Configure your environment:

echo "GEMINI_API_KEY=your_key_here" > .env


Launch the honeypot:

docker-compose up --build


📊 System Architecture

The Decoy: A frontend/service facade simulating a vulnerable entry point.

The Orchestrator: A Python-based middleware that proxies traffic to the LLM.

The Analyst: A secondary LLM agent that observes the interaction and classifies TTPs.

The Reporter: A module that aggregates logs into a structured forensic report.

📝 MITRE ATT&CK Mapping

Our system identifies techniques including, but not limited to:

T1059: Command and Scripting Interpreter

T1078: Valid Accounts (Brute force attempts)

T1552: Unsecured Credentials

T1083: File and Directory Discovery

⚖️ License

Distributed under the MIT License. See LICENSE for more information.

Built for the CyberChain Global Hackathon 2026.
