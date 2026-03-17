Project: SentientSentry (LLM-Powered Conversational Honeypot)
The Vision: From Passive Decoys to Intelligent Deception

Traditional honeypots suffer from a "Deception Paradox": low-interaction systems are safe but easily fingerprinted, while high-interaction systems are realistic but present extreme operational risk. SentientSentry resolves this by using Large Language Models (LLMs) to imbue lightweight, simulated services with the dynamic, adaptive personality of a real system.

By acting as a Semantic Gateway, our system doesn't just log traffic—it engages the adversary in a believable dialogue, exhausting their resources while autonomously mapping their intent to the MITRE ATT&CK framework in real-time.
Core Value Proposition

    Dynamic High-Interaction Emulation: Uses LLaMA-3/GPT-4o to simulate complex environments (SSH terminals, Administrative APIs, and Login Forms) that "remember" attacker actions using a System State Register (SRi​) and Interaction History (Hi​).

    Real-Time TTP Classification: Every command is analyzed by a secondary "Analyst Agent" that maps activity to specific MITRE ATT&CK Technique IDs (e.g., T1110 for Brute Force, T1083 for File Discovery) as it happens.

    Maximized Attacker Dwell Time: Leverages Chain-of-Thought (CoT) prompting to generate contextually accurate, non-deterministic responses, making it indistinguishable from a real system (True Negative Rate ≈0.90).

    Automated Intelligence Reporting: Upon session termination, the system generates a SIEM-ready Attacker Intelligence Report (AIR) in NDJSON format, including chronological narratives and technique frequency heatmaps.

High-Level Architecture

    Protocol Interface: Lightweight listeners (Python/FastAPI) capture raw inputs.

    Prompt Orchestrator: Assembles the context (System State + History + Payload).

    LLM Backend: Generates the deceptive response and evaluates the Aggressiveness Score (Fi​).

    Telemetry Engine: Maps the event to MITRE ATT&CK and updates the session log.

    Declaration: This project utilizes Generative AI (LLMs) for dynamic response generation and TTP classification, as permitted by the CyberChain Hackathon rules.
