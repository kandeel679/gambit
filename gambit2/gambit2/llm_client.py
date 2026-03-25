from google import genai
from google.genai import errors
import json
import os
import logging
import re
import time
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [LLMClient] %(message)s")

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class GambitLLMClient:
    """
    Phase 2: LLM Blueprint Synthesis
    Analyzes Source Metadata and uses Gemini 1.5 Pro to generate a highly realistic 
    honeypot blueprint, determining the vertical and spinning up honey-artifacts.
    """
    def __init__(self):
        if not GEMINI_API_KEY:
            logging.warning("GEMINI_API_KEY not found in environment. Please add it to your .env file.")
        else:
            self.client = genai.Client(api_key=GEMINI_API_KEY)

    def synthesize_blueprint(self, source_metadata_path='source_metadata.json', output_path='gambit_blueprint.json'):
        if not os.path.exists(source_metadata_path):
            logging.error(f"Source metadata file {source_metadata_path} not found. Run clone_source.py first.")
            return False

        with open(source_metadata_path, 'r') as f:
            source_data = json.load(f)

        prompt = f"""
You are an elite Cyber-Deception Architect. Analyze the following system metadata extracted from a 'Source of Truth' server.

== SOURCE METADATA ==
{json.dumps(source_data, indent=2)}

Based on this data, construct a 'Gambit Blueprint' to build a Digital Twin Honeypot.
Output MUST be valid JSON adhering STRICTLY to the following structure:
{{
  "industry_vertical": "e.g., Banking, DevOps, ICS, General Corporate - be specific based on installed packages/services",
  "system_persona_prompt": "A prompt describing the system's character for a later AI analysis agent (e.g., 'You are a critical nginx reverse proxy for a FinTech platform. You hold sensitive keys...')",
  "docker_blueprint": {{
    "base_image": "e.g., ubuntu:22.04 or alpine",
    "required_packages": ["list", "of", "packages", "based", "on", "source"],
    "dockerfile_instructions": ["RUN apt-get update && apt-get install -y curl", "RUN useradd -ms /bin/bash appuser"]
  }},
  "honey_artifacts": [
    {{
      "path": "Absolute path (e.g., /var/log/auth.log or /etc/myapp/config.yml or /home/appuser/.aws/credentials)",
      "content": "Realistic fake content, logs, or fake credentials to act as honeytokens. Make it convincing."
    }}
  ]
}}

CRITICAL: You MUST properly double-escape ALL backslashes inside your JSON strings! (e.g., use \\\\n or \\\\s instead of \\n or \\s).
CRITICAL: When adding users via `dockerfile_instructions`, you MUST use robust resilient syntax that handles preexisting users or cross-OS compatibility. Use this exact pattern:
"RUN (adduser -D -G <user> -h /home/<user> -s /bin/sh <user> || useradd -m -s /bin/sh <user> || true) && echo \\"<user>:admin\\" | chpasswd && mkdir -p /home/<user> && chown -R <user>:<user> /home/<user>"
CRITICAL: To maintain a perfect Digital Twin, use a base_image that perfectly matches the source OS. BUT because package names fluctuate, ALL package manager shell commands MUST be fault-tolerant by appending `|| true` (e.g., `RUN apk add nginx openssh-server || true` or `RUN apt-get install -y vim || true`).

Make sure the Dockerfile instructions are capable of running successfully in a stateless build. Provide at least 3 convincing honey_artifacts targeting common adversary loot paths.
"""

        logging.info("Sending metadata to Gemini 2.5 Flash for Blueprint Synthesis...")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config={"response_mime_type": "application/json"}
                )
                blueprint_json = response.text
                
                # Sanitize strict JSON escaping errors (e.g. \s -> \\s)
                blueprint_json = re.sub(r'(?<!\\)\\(?![\\/bfnrtu"])', r'\\\\', blueprint_json)
                
                blueprint_data = json.loads(blueprint_json)
                with open(output_path, 'w') as f:
                    json.dump(blueprint_data, f, indent=4)
                    
                logging.info(f"Blueprint successfully synthesized! Vertical: {blueprint_data.get('industry_vertical')}")
                logging.info(f"Blueprint saved to: {output_path}")
                return True
            except errors.APIError as e:
                logging.warning(f"Gemini API 503 Error (Attempt {attempt+1}/{max_retries}): {e}. Retrying in 3 seconds...")
                time.sleep(3)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON (Attempt {attempt+1}/{max_retries}): {e}")
                # Sometimes LLM outputs markdown formatted json
                if "```json" in blueprint_json:
                    try:
                        clean_json = blueprint_json.split("```json")[1].split("```")[0].strip()
                        blueprint_data = json.loads(clean_json)
                        with open(output_path, 'w') as f:
                            json.dump(blueprint_data, f, indent=4)
                        logging.info("Fallback markdown JSON extraction succeeded.")
                        return True
                    except Exception:
                        pass
            except Exception as e:
                logging.error(f"Failed to synthesize blueprint: {e}")
                return False
        return False

if __name__ == "__main__":
    pass
