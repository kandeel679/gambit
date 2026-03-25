import paramiko
import socket
import threading
import json
import time
from datetime import datetime
import subprocess
import select
import sys
import os
import traceback
import uuid
import queue
import requests

# Configuration
HOST = '0.0.0.0'
PORT = 2222
BANNER = 'SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.1' # Anti-Fingerprinting custom banner
LOGS_DIR = 'logs'
AI_API_URL = "http://127.0.0.1:11434/api/generate" # Dummy local AI URL

log_queue = queue.Queue()

def ai_forwarder_thread():
    """Background worker that continuously reads from log_queue and POSTs to the AI API."""
    while True:
        try:
            log_entry = log_queue.get()
            try:
                # Using a 2 second timeout to prevent hanging the worker on bad connections
                response = requests.post(
                    AI_API_URL, 
                    json={"model": "dummy", "prompt": json.dumps(log_entry)},
                    timeout=2
                )
                print(f"[*] [AI Hook] Forwarded event '{log_entry.get('event_type')}' -> HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"[-] [AI Hook] Could not reach AI API: {e}")
            finally:
                log_queue.task_done()
        except Exception as e:
            print(f"[-] [AI Hook] Thread error: {e}")

# Ensure logs directory exists
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Weak Credentials accepted by the honeypot
WEAK_CREDS = {
    'root': 'root',
    'admin': 'password123',
    'user': '123456'
}

log_lock = threading.Lock()

def log_activity(session_id, event_type, **kwargs):
    """Outputs all activity into a structured NDJSON format for SIEM ingestion."""
    log_entry = {
        'session_id': session_id,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'event_type': event_type,
    }
    log_entry.update(kwargs)
    
    log_filename = os.path.join(LOGS_DIR, f"session_{session_id}.ndjson")
    
    with log_lock:
        with open(log_filename, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
            
    # Asynchronously push to real-time AI forwarding queue
    log_queue.put(log_entry)

def analyze_with_llm(command, session_metadata):
    """
    Placeholder LLM Analysis Hook.
    Synchronously evaluates the command for MITRE ATT&CK TTPs and an aggressiveness score.
    """
    # In a real environment, you might use the `requests` library to query a local LLaMA-3 backend
    # Example: response = requests.post("http://localhost:11434/api/generate", ...)
    
    # Returning mocked data for the placeholder
    return {
        "mitre_ttps": ["T1059.004"], # Command and Scripting Interpreter: Unix Shell
        "aggressiveness_score": 2,    # 0-4 Scale
        "analyzed_command": command.strip()
    }

class HoneypotServer(paramiko.ServerInterface):
    def __init__(self, client_ip, session_id):
        self.event = threading.Event()
        self.client_ip = client_ip
        self.username = None
        self.session_id = session_id

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        self.username = username
        
        # Weak Credential Authentication check
        if username in WEAK_CREDS and WEAK_CREDS[username] == password:
            log_activity(self.session_id, "auth_success", ip=self.client_ip, username=username, password=password)
            return paramiko.AUTH_SUCCESSFUL
            
        log_activity(self.session_id, "auth_failed", ip=self.client_ip, username=username, password=password)
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        # We accept PTY requests to allow complex terminals like vim or top to execute 
        # normally inside the backend environment.
        return True

    def check_channel_exec_request(self, channel, command):
        self.event.set()
        return True

def handle_connection(client_socket, client_addr, host_key):
    """Handles an individual SSH connection session in its own thread."""
    client_ip = client_addr[0]
    session_id = str(uuid.uuid4())
    log_activity(session_id, "connection_attempt", ip=client_ip, port=client_addr[1])
    
    try:
        transport = paramiko.Transport(client_socket)
        
        # Anti-fingerprinting: set a local version string mimicking a typical Ubuntu OpenSSH server
        transport.local_version = BANNER 
        transport.add_server_key(host_key)
        
        server = HoneypotServer(client_ip, session_id)
        try:
            transport.start_server(server=server)
        except paramiko.SSHException as e:
            log_activity(session_id, "ssh_negotiation_failed", ip=client_ip, error=str(e))
            return

        # Wait for authentication
        channel = transport.accept(20)
        if channel is None:
            log_activity(session_id, "channel_timeout", ip=client_ip)
            transport.close()
            return

        server.event.wait(10)
        if not server.event.is_set():
            transport.close()
            return

        # Start Real Server Forwarding
        # Note: In a production environment, this should ideally exec into an isolated Docker container
        # e.g., ["docker", "exec", "-it", "honeypot_sandbox", "/bin/bash"]
        backend_cmd = ["bash"] if os.name != 'nt' else ["cmd.exe"]
        
        # We start the backend subprocess
        # PTY mode could be more highly refined on linux using `pty` or `pexpect`.
        backend = subprocess.Popen(
            backend_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )

        channel.send("Welcome to Ubuntu 22.04.1 LTS (GNU/Linux 5.15.0-53-generic x86_64)\r\n\r\n")

        # Session Interception Loop
        # Capturing raw stream of keystrokes before sending them to the backend process.
        cmd_buffer = ""
        while True:
            # Check if there is data to read from the attacker
            if channel.recv_ready():
                try:
                    data = channel.recv(1024)
                    if not data:
                        break # Connection closed
                    
                    decoded_char = data.decode("utf-8", errors="replace")
                    cmd_buffer += decoded_char
                    
                    # Intercept complete commands on carriage return
                    if '\r' in decoded_char or '\n' in decoded_char:
                        issued_command = cmd_buffer.strip()
                        cmd_buffer = "" # reset buffer
                        
                        if issued_command:
                            # 1. LLM Analysis Hook (Synchronous execution)
                            llm_results = analyze_with_llm(issued_command, {"ip": client_ip, "user": server.username})
                            
                            # 2. Forensic Logging
                            log_activity(session_id, "command_executed", 
                                ip=client_ip, 
                                username=server.username, 
                                command=issued_command, 
                                llm_analysis=llm_results
                            )
                    
                    # Forward attacker data to backend
                    if backend.poll() is None:
                        backend.stdin.write(data)
                        backend.stdin.flush()
                except Exception as e:
                    log_activity(session_id, "channel_error", error=str(e), traceback=traceback.format_exc())
                    break

            # Forward output from backend to the attacker
            # We use select if possible on linux, fallback to non-blocking reads where desired.
            if os.name != 'nt':
                r_ready, _, _ = select.select([backend.stdout, backend.stderr], [], [], 0.1)
                for stream in r_ready:
                    out = stream.read1(1024) if hasattr(stream, 'read1') else stream.read(1024)
                    if out:
                        # Logging the server response optionally
                        channel.send(out)
            else:
                # Windows fallback (simplified, blocking might cause hangs natively here 
                # without threading the IO, but left simpler for demonstration).
                backend.stdout.flush()
                time.sleep(0.1)

            if channel.exit_status_ready() or backend.poll() is not None:
                break
                
        backend.kill()
        channel.close()
        transport.close()
        log_activity(session_id, "session_closed", ip=client_ip)

    except Exception as e:
        log_activity(session_id, "server_error", ip=client_ip, error=str(e), traceback=traceback.format_exc())
        try:
            transport.close()
        except:
            pass

def start_honeypot():
    # Start the background AI worker
    # ai_thread = threading.Thread(target=ai_forwarder_thread, daemon=True)
    # ai_thread.start()

    # Load or generate persistent server RSA key
    host_key_file = 'server_rsa.key'
    if os.path.exists(host_key_file):
        print("[*] Loading existing RSA key...")
        host_key = paramiko.RSAKey(filename=host_key_file)
    else:
        print("[*] Generating new RSA key...")
        host_key = paramiko.RSAKey.generate(2048)
        host_key.write_private_key_file(host_key_file)

    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(100)
        
        print(f"[*] Starting Custom SSH Honeypot Listener on {HOST}:{PORT}")
        print(f"[*] Fingerprint/Banner configured as: {BANNER}")
        print(f"[*] Activity logs will be written in NDJSON to the '{LOGS_DIR}' directory")
        
        while True:
            client_socket, client_addr = server_socket.accept()
            # Spawn a new thread to handle concurrent sessions natively
            thread = threading.Thread(target=handle_connection, args=(client_socket, client_addr, host_key))
            thread.daemon = True
            thread.start()
            
    except KeyboardInterrupt:
        print("\n[*] Shutting down honeypot.")
        server_socket.close()
        sys.exit(0)
    except Exception as e:
        print(f"[-] Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    start_honeypot()
