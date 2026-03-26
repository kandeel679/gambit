from google import genai
from google.genai import errors
import json
import logging
import os
import time
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [AnalysisAgent] %(message)s")

# In-memory session profiling store
# Format: { "session_123": {"profile": {...}, "timeline": [...]} }
active_profiles = {}

class AdversaryAnalysisAgent:
    """
    Phase 5: Live Agentic Analysis & Profiling
    Processes real-time command streams, maps to MITRE ATT&CK TTPs, 
    and maintains a Live Adversary Profile.
    """
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "ollama" if os.getenv("OLLAMA_HOST") else "gemini")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://192.168.112.41:11434").rstrip('/')
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1")

        if self.provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                self.client = genai.Client(api_key=api_key)
            else:
                logging.warning("GEMINI_API_KEY missing. Analysis Agent will run in stub mapping mode.")
                self.model = None
        else:
            logging.info(f"Analysis Agent initialized with Ollama at {self.ollama_host} (Model: {self.ollama_model})")


    def _initialize_session(self, session_id):
        if session_id not in active_profiles:
            active_profiles[session_id] = {
                "start_time": datetime.utcnow().isoformat(),
                "profile": {
                    "estimated_skill_level": "Unknown",
                    "actor_type": "Unknown (Bot/Human)",
                    "primary_intent": "Enumeration"
                },
                "timeline": [],
                "mitre_ttps_observed": []
            }

    def analyze_command(self, session_id, command):
        """Called directly by the proxy broker's Intelligence Stream."""
        self._initialize_session(session_id)
        
        logging.info(f"Analyzing command payload for session {session_id}...")
        
        if self.provider == "gemini" and not hasattr(self, 'client'):
            # Fallback local heuristics if Gemini is requested but no key exists
            ttp = {"ttp_id": "T1059", "name": "Command and Scripting Interpreter", "intent": "Execution"}
            if "curl" in command or "wget" in command:
                ttp = {"ttp_id": "T1105", "name": "Ingress Tool Transfer", "intent": "Command and Control"}
            elif "whoami" in command or "id" in command or "ls" in command:
                ttp = {"ttp_id": "T1082", "name": "System Information Discovery", "intent": "Discovery"}
            
            self._update_profile_state(session_id, command, ttp, "Likely automated enumeration script.")
            return
            
        prompt = f"""
        Analyze the following Linux terminal command executed by an adversary in a honeypot.
        Command: `{command}`

        Map this strictly to the MITRE ATT&CK framework. Determine the exact TTP ID, Name, 
        and the immediate Adversary Intent. Also assess if this seems like an automated bot or a human.

        Output strictly valid JSON:
        {{
            "ttp_id": "TXXXX",
            "name": "TTP Name",
            "intent": "Adversary Intent",
            "actor_analysis": "Brief analysis of skill and actor type."
        }}
        """
        for _ in range(3): # Simple retry for 503s
            try:
                if getattr(self, "provider", "gemini") == "gemini":
                    response = self.client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config={"response_mime_type": "application/json"}
                    )
                    text = response.text
                else:
                    payload = {
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json"
                    }
                    resp = requests.post(f"{self.ollama_host}/api/generate", json=payload, timeout=20)
                    if not resp.ok:
                        logging.error(f"Ollama API Error: {resp.text}")
                    resp.raise_for_status()
                    text = resp.json().get("response", "")
                
                text = text.split("```json")[-1].split("```")[0].strip() if "```json" in text else text

                
                analysis = json.loads(text)
                self._update_profile_state(session_id, command, analysis, analysis.get("actor_analysis", "Unknown"))
                break
            except errors.APIError:
                time.sleep(2)
            except Exception as e:
                logging.error(f"Failed to analyze command '{command}': {e}")
                break

    def _update_profile_state(self, session_id, command, ttp_data, actor_analysis):
        session_data = active_profiles[session_id]
        
        # Timeline recording
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "command": command,
            "ttp": ttp_data
        }
        session_data["timeline"].append(event)
        
        # Unique TTP set
        if ttp_data["ttp_id"] not in session_data["mitre_ttps_observed"]:
            session_data["mitre_ttps_observed"].append(ttp_data["ttp_id"])
            
        # Profile Evolution based on AI hints
        if "human" in actor_analysis.lower():
            session_data["profile"]["actor_type"] = "Human"
        elif "bot" in actor_analysis.lower() or "automated" in actor_analysis.lower():
            session_data["profile"]["actor_type"] = "Automated Script/Bot"
            
        logging.info(f"[Profile Updated: {session_id}] Tag: {ttp_data['ttp_id']} ({ttp_data['name']}) -> {ttp_data['intent']}")

def get_session_data(session_id):
    return active_profiles.get(session_id, None)

agent = None

def analyze_command(session_id, command):
    global agent
    if agent is None:
        agent = AdversaryAnalysisAgent()
    agent.analyze_command(session_id, command)
