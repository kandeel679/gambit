import http.server
import socketserver
import json
import os
import glob
import urllib.parse
import threading
import logging
import time
import webbrowser
from dotenv import load_dotenv, set_key
from typing import Dict, Any

# Import Gambit Modules
from clone_source import CloneSource
from llm_client import GambitLLMClient
from generator import GambitGenerator
from proxy_server import start_proxy_server

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
GUI_STATIC_DIR = os.path.join(DIRECTORY, "gui_static")
ENV_PATH = os.path.join(DIRECTORY, ".env")

# Global State for Deployment Tracking
deployment_status: Dict[str, Any] = {
    "progress": 0,
    "logs": [],
    "complete": False,
    "error": None
}

# Global live system logs (captures ALL backend logs for live streaming to GUI)
live_logs = []

def add_log(message, type="info"):
    deployment_status["logs"].append({
        "message": f"[{time.strftime('%H:%M:%S')}] {message}",
        "type": type
    })
    logging.info(f"[GUI-Deploy] {message}")

class GuiLogHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            
            log_type = "info"
            if record.levelno >= logging.ERROR:
                log_type = "error"
            elif record.levelno >= logging.WARNING:
                log_type = "warning"
            
            log_entry = {
                "message": f"[{time.strftime('%H:%M:%S')}] {msg}",
                "type": log_type
            }
            
            # Add to live system logs (all backend logs)
            live_logs.append(log_entry)
            
            # Also add to deployment status logs (skip duplicated deploy logs)
            if "[GUI-Deploy]" not in msg:
                deployment_status["logs"].append(log_entry)
        except Exception:
            pass

class GambitOrchestrator(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.daemon = True

    def run(self):
        global deployment_status
        deployment_status = {"progress": 0, "logs": [], "complete": False, "error": None}
        
        # Re-load .env so this thread picks up freshly saved config
        load_dotenv(ENV_PATH, override=True)
        
        # Use absolute paths for metadata/blueprint files
        metadata_path = os.path.join(DIRECTORY, "source_metadata.json")
        blueprint_path = os.path.join(DIRECTORY, "gambit_blueprint.json")
        
        try:
            # Phase 1: DNA Extraction
            deployment_status["progress"] = 10
            add_log("Phase 1: DNA Extraction - Connecting to target...", "info")
            discoverer = CloneSource(
                self.config['target_ip'], 
                int(self.config.get('target_port', 22)), 
                self.config['target_user'], 
                password=self.config.get('target_pass', '')
            )
            if not discoverer.connect():
                raise Exception("Failed to connect to Source. Check credentials/network.")
            
            add_log("Extracting system state and metadata...", "info")
            success = discoverer.extract_dna(metadata_path)
            discoverer.close()
            if not success: raise Exception("DNA Extraction failed.")
            
            # Phase 2: Synthesis
            deployment_status["progress"] = 40
            add_log("Phase 2: Agentic Blueprint Synthesis...", "info")
            llm = GambitLLMClient()
            success = llm.synthesize_blueprint(metadata_path, blueprint_path)
            if not success: raise Exception("Blueprint synthesis failed.")

            # Phase 3: Generation
            deployment_status["progress"] = 70
            add_log("Phase 3: Docker Honeypot Generation & Deployment...", "info")
            generator = GambitGenerator()
            success = generator.build_and_deploy(blueprint_path)
            if not success: raise Exception("Docker deployment failed.")

            # Phase 4: Proxy
            deployment_status["progress"] = 100
            add_log("Phase 4: Activating Live Dual-Stream Proxy Broker...", "success")
            deployment_status["complete"] = True
            
            # Start Proxy (This is blocking, so we run it in its own thread too if we want the GUI server to stay responsive)
            # However, start_proxy_server usually has its own loop. 
            # We'll run it in a separate daemon thread so the GUI doesn't hang.
            proxy_thread = threading.Thread(target=start_proxy_server, kwargs={'host': '0.0.0.0', 'port': 2222}, daemon=True)
            proxy_thread.start()
            add_log("Gambit Decoy is now LIVE on port 2222.", "success")

        except Exception as e:
            deployment_status["error"] = str(e)
            add_log(f"CRITICAL ERROR: {str(e)}", "error")

class LogHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=GUI_STATIC_DIR, **kwargs)

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == "/api/config":
            load_dotenv(ENV_PATH)
            config = {
                "target_ip": os.getenv("TARGET_IP", "127.0.0.1"),
                "target_port": os.getenv("TARGET_PORT", "22"),
                "target_user": os.getenv("TARGET_USER", "root"),
                "llm_provider": os.getenv("LLM_PROVIDER", "gemini"),
                "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                "ollama_model": os.getenv("OLLAMA_MODEL", "llama3.1")
            }
            self._send_json(config)
            return

        elif path == "/api/status":
            self._send_json(deployment_status)
            return

        elif path == "/api/live-logs":
            # Incremental live log streaming: ?since=N returns logs from index N onwards
            query = urllib.parse.parse_qs(parsed_path.query)
            since = int(query.get("since", ["0"])[0])
            self._send_json({
                "logs": live_logs[since:],
                "total": len(live_logs)
            })
            return

        elif path == "/api/logs":
            log_files = glob.glob(os.path.join(DIRECTORY, "report_session_*.md"))
            files_data = [{"filename": os.path.basename(f), "mtime": os.path.getmtime(f)} for f in log_files]
            files_data.sort(key=lambda x: x["mtime"], reverse=True)
            self._send_json(files_data)
            return

        elif path.startswith("/api/logs/"):
            filename = urllib.parse.unquote(path.replace("/api/logs/", ""))
            file_path = os.path.join(DIRECTORY, filename)
            if not filename.startswith("report_session_") or not os.path.isfile(file_path):
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            with open(file_path, "r", encoding="utf-8") as f:
                self.wfile.write(f.read().encode("utf-8"))
            return

        if path == "/": self.path = "/index.html"
        return super().do_GET()

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/launch":
            content_length = int(self.headers['Content-Length'])
            post_data = json.loads(self.rfile.read(content_length).decode('utf-8'))
            
            # Save to .env
            for key, value in post_data.items():
                if value:
                    set_key(ENV_PATH, key.upper(), value)
                    os.environ[key.upper()] = value
            
            # Trigger Background Orchestration
            orchestrator = GambitOrchestrator(post_data)
            orchestrator.start()
            
            self._send_json({"status": "launched"})
            return

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def run_gui_server(blocking=True):
    # Attach GuiLogHandler to root logger so ALL backend logs 
    # (proxy, analysis agent, reporter) are captured for the GUI
    logging.basicConfig(level=logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    gui_handler = GuiLogHandler()
    gui_handler.setFormatter(logging.Formatter('[%(module)s] %(message)s'))
    root_logger.addHandler(gui_handler)

    with ReusableTCPServer(("", PORT), LogHandler) as httpd:
        print(f"[*] Gambit Web Interface running at http://localhost:{PORT}")
        webbrowser.open(f"http://localhost:{PORT}")
        if blocking:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nServer stopped.")

if __name__ == "__main__":
    run_gui_server()
