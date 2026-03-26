# Conversational Honeypot (WIP)
**CyberChain Hackathon - Challenge 5 (Honeypot Conversational)**

> ⚠️ **STATUS: UNDER DEVELOPMENT - DO NOT DEPLOY TO PRODUCTION** ⚠️
> This project is currently in the active coding phase. Core protocol interfaces and LLM orchestration are being built.

## Overview
This project engineers an LLM-based conversational honeypot designed to simulate vulnerable services (SSH panels, administrative APIs, login forms) to maximize attacker dwell time. It classifies tactics, techniques, and procedures (TTPs) in real-time according to the MITRE ATT&CK framework.

By decoupling network protocol handling from deceptive logic, this system uses generative models to provide dynamic, adaptive environments that lure sophisticated attackers.

## Architecture
The system functions as a semantic gateway and is divided into four main layers:

* **Protocol Interface:** Traffic interception and connection management using Paramiko (SSH) and FastAPI (HTTP). Employs an "accept-all" authentication policy.
* **Prompt Orchestrator:** Context assembly and history management. Maintains a stateful representation of the environment via a System State Register and Interaction History.
* **LLM Backend:** Generative response and behavior emulation utilizing models like GPT-4, LLaMA3, or local vLLM.
* **Telemetry Analysis:** TTP mapping and report generation (MITRE ATT&CK integration).

## Current Sprint & Roadmap
Development follows an agile sprint structure to meet hackathon deadlines.

- [ ] **Sprint I (Kick-off):** Port opening and Paramiko/FastAPI setup. Functional connection loop for SSH/HTTP.
- [ ] **Model Refinement:** Implement prompt engineering and Chain-of-Thought (CoT) reasoning for credible Ubuntu terminal/API responses.
- [ ] **Intelligence Phase:** Real-time MITRE TTP classification and structured JSON logging.
- [ ] **Optimization Phase:** Docker containerization, minimal base images (Alpine/Debian-slim), and vLLM setup for low-latency deployment.

## Deployment (Local Dev)
*Environment optimization using Docker is essential for minimizing latency.* 1. Clone the repository.
2. Ensure Docker is installed. 
3. *Note: Configuration for GPU acceleration (NVIDIA Container Toolkit) is required if testing local inference.*
4. Run the development container (Command TBA).

## Security Warning
If you are testing this locally, ensure the environment is strictly segmented with no outbound access to the production environment. Do not commit real API keys or credentials; use secret environment variables.
