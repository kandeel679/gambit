from google import genai
from google.genai import errors
import json
import logging
import os
import time
from analysis_agent import get_session_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [ForensicReporter] %(message)s")

class ForensicReporter:
    """
    Phase 6: Forensic Reporting
    Triggered upon SSH disconnect, synthesizes the live profile into 
    a highly readable Markdown report.
    """
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
        else:
            self.model = None

    def generate_report(self, session_id):
        data = get_session_data(session_id)
        if not data:
            logging.warning(f"No active session data tracked for {session_id}. No report needed.")
            return False

        report_path = f"report_{session_id}.md"
        logging.info(f"Synthesizing Post-Incident Forensic Report for {session_id}...")

        if not hasattr(self, 'client'):
            self._write_stub_report(report_path, data)
            return True

        prompt = f"""
        You are an elite Incident Responder. Compile a comprehensive post-incident Forensic Report 
        in elegant Markdown format based on the following Adversary Session Data captured by the Gambit Honeypot.

        Session Data:
        {json.dumps(data, indent=2)}

        The report MUST include:
        1. Executive Summary (Actor Type, Skill Level, Primary Intent)
        2. MITRE ATT&CK Heatmap Summary (List all TTPs triggered with descriptions)
        3. Attack Timeline (Chronological breakdown of exactly what commands were executed and why)
        4. Strategic Recommendations (What was the attacker looking for and how to patch vulnerabilities)
        """
        
        for _ in range(3):
            try:
                response = self.client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                with open(report_path, 'w') as f:
                    f.write(response.text)
                logging.info(f"[+] Forensic Report successfully generated: {report_path}")
                return True
            except errors.APIError:
                time.sleep(3)
            except Exception as e:
                logging.error(f"Failed to generate LLM report: {e}")
                break
                
        self._write_stub_report(report_path, data)
        return False

    def _write_stub_report(self, path, data):
        with open(path, 'w') as f:
            f.write(f"# Forensic Report (Fallback Mode)\n\nRaw Session Telemetry:\n```json\n{json.dumps(data, indent=2)}\n```")
        logging.info(f"[+] Fallback Report generated: {path}")

# Hook for the proxy server
reporter = ForensicReporter()

def trigger_forensic_reporter(session_id):
    reporter.generate_report(session_id)
