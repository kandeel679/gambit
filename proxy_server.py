import socket
import threading
import paramiko
import docker
import logging
import time
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [LiveProxy] %(message)s")

from analysis_agent import analyze_command, set_connection_info
from reporter import trigger_forensic_reporter

# ==========================================
# INTELLIGENCE STREAM AI INTEGRATION
# ==========================================
def dispatch_to_analysis_agent(session_id, command):
    """
    Phase 5 Integration: Sends raw command to LLM asynchronously.
    Strict Input Sanitization implemented to prevent prompt injection.
    """
    # Defensive programming: Strip non-printable chars
    clean_command = re.sub(r'[^\x20-\x7E]', '', command)
    logging.info(f"[Intelligence Stream -> Agentic LLM] Dispatched: '{clean_command}' (Session: {session_id})")
    analyze_command(session_id, clean_command)



# ==========================================
# SSH PROXY HANDLER
# ==========================================
# Weak credentials the honeypot accepts (realistic bait)
WEAK_CREDENTIALS = {
    ("root", "root"),
    ("root", "admin"),
    ("root", "password"),
    ("root", "123456"),
    ("root", "toor"),
    ("admin", "admin"),
    ("admin", "password"),
    ("admin", "123456"),
    ("user", "user"),
    ("user", "password"),
    ("test", "test"),
    ("ubuntu", "ubuntu"),
    ("guest", "guest"),
    ("pi", "raspberry"),
}

class ProxyServerInterface(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()
        self.auth_attempts = []  # Track all login attempts (including failed ones)
        self.authenticated_user = None

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        # Record every attempt for forensic profiling
        self.auth_attempts.append({"method": "password", "username": username, "password": password})
        
        if (username, password) in WEAK_CREDENTIALS:
            logging.warning(f"[Auth] Attacker AUTHENTICATED | User: {username} | Pass: {password}")
            self.authenticated_user = username
            return paramiko.AUTH_SUCCESSFUL
        else:
            logging.info(f"[Auth] Attacker login REJECTED | User: {username} | Pass: {password}")
            return paramiko.AUTH_FAILED
        
    def check_auth_publickey(self, username, key):
        logging.warning(f"[Auth] Attacker attempting key login | User: {username}")
        self.auth_attempts.append({"method": "publickey", "username": username, "key_fingerprint": key.get_fingerprint().hex()})
        self.authenticated_user = username
        return paramiko.AUTH_SUCCESSFUL
        
    def get_allowed_auths(self, username):
        return 'password,publickey'
        
    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True
        
    def check_channel_exec_request(self, channel, command):
        self.event.set()
        return True

class HoneypotSession(threading.Thread):
    def __init__(self, client_socket, docker_client, container_name="gambit-honeypot"):
        super().__init__()
        self.client_socket = client_socket
        self.docker_client = docker_client
        self.container_name = container_name
        self.session_id = f"session_{int(time.time())}"
        self.cwd = "/root"  # Persistent current working directory state
        self.in_newline_sequence = False # Fix for double shell prompt on \r\n
        # Capture attacker's IP and port from the socket
        try:
            self.attacker_ip, self.attacker_port = client_socket.getpeername()
        except Exception:
            self.attacker_ip, self.attacker_port = "unknown", 0

    def run(self):
        connect_time = time.strftime('%Y-%m-%d %H:%M:%S')
        transport = paramiko.Transport(self.client_socket)
        
        # Ephemeral Host Key for SSH
        try:
            host_key = paramiko.RSAKey.generate(2048)
            transport.add_server_key(host_key)
        except Exception as e:
            logging.error(f"Failed generating ephemeral RSA server key: {e}")
            return

        server = ProxyServerInterface()
        try:
            transport.start_server(server=server)
        except paramiko.SSHException:
            logging.error("SSH negotiation failed. Dropping connection.")
            return

        channel = transport.accept(20)
        if channel is None:
            logging.error("Channel dropped.")
            return

        server.event.wait(10)
        logging.info(f"[{self.session_id}] Shell opened from {self.attacker_ip}:{self.attacker_port}")

        # Register attacker connection info in the session profile
        set_connection_info(self.session_id, {
            "attacker_ip": self.attacker_ip,
            "attacker_port": self.attacker_port,
            "connect_time": connect_time,
            "auth_attempts": server.auth_attempts,
            "authenticated_user": server.authenticated_user
        })

        # Bind to Docker Isolation
        try:
            container = self.docker_client.containers.get(self.container_name)
            # Create a robust shell process inside Docker (sh is universally available)
            docker_cmd = "sh"
        except docker.errors.NotFound:
            logging.error(f"[{self.session_id}] Gambit Container '{self.container_name}' NOT FOUND. Ensure Phase 3 (Generator) has run.")
            channel.send("System maintenance. Disconnecting...\r\n")
            channel.close()
            return

        channel.send("Welcome to the server. Access granted.\r\n$ ")

        # DUAL-STREAM INTERACTIVE LOOP
        command_buffer = ""
        session_done = False
        analysis_threads = []  # Track analysis threads to join before reporting
        while not session_done:
            try:
                data = channel.recv(1024)
                if not data:
                    break # Connection dropped

                # Decode data character by character to handle various clients/encodings
                try:
                    chars = data.decode('utf-8')
                except UnicodeDecodeError:
                    # Fallback to latin-1 if utf-8 fails
                    chars = data.decode('latin-1')

                for char in chars:
                    if char in ('\r', '\n'):
                        if not self.in_newline_sequence:
                            channel.send('\r\n')
                            command = command_buffer.strip()
                            if command:
                                # --- 1. INTELLIGENCE STREAM (ASYNC LLM TTP MAPPING) ---
                                # Always dispatch to analysis, even for exit/logout
                                t = threading.Thread(
                                    target=dispatch_to_analysis_agent, 
                                    args=(self.session_id, command)
                                )
                                t.start()
                                analysis_threads.append(t)

                                if command in ["exit", "logout"]:
                                    channel.send("logout\r\n")
                                    session_done = True
                                    break
                                
                                # --- 2. EXECUTION STREAM (DOCKER PROXY) ---
                                try:
                                    logging.info(f"[{self.session_id}][EXEC] {command} (WORKDIR: {self.cwd})")
                                    
                                    # Special Handling for 'cd' to maintain persistent state
                                    if command == "cd" or command.startswith("cd "):
                                        # Attempt to resolve directory change INSIDE the container context
                                        new_dir = command[3:].strip() or "~"
                                        test_cmd = f"cd {self.cwd} && cd {new_dir} && pwd"
                                        exit_code, output = container.exec_run(
                                            cmd=["sh", "-c", test_cmd],
                                            user='root'
                                        )
                                        if exit_code == 0:
                                            self.cwd = output.decode('utf-8').strip()
                                            channel.send(f"") # cd usually has no output
                                        else:
                                            channel.send(f"sh: cd: {new_dir}: No such file or directory\r\n")
                                    else:
                                        # Execute command natively in docker sh context with workdir tracking
                                        exit_code, output = container.exec_run(
                                            cmd=["sh", "-c", command],
                                            tty=True,
                                            workdir=self.cwd,
                                            user='root'
                                        )
                                        # Return raw output
                                        channel.send(output.decode('utf-8').replace('\n', '\r\n'))
                                except Exception as e:
                                    logging.error(f"Exec failure: {e}")
                                    channel.send(f"sh: 1: {command}: not found\r\n")
                            
                            command_buffer = ""
                            if not session_done:
                                channel.send(f"root@decoy:{self.cwd}# ")
                            self.in_newline_sequence = True
                        
                    # Handle Backspace
                    elif char in ('\x08', '\x7f'):
                        self.in_newline_sequence = False
                        if len(command_buffer) > 0:
                            command_buffer = command_buffer[:-1]
                            # Erase char on terminal visually
                            channel.send('\b \b')
                    
                    # Handle Ctrl+C
                    elif char == '\x03': 
                        self.in_newline_sequence = False
                        channel.send("^C\r\nroot@decoy:" + self.cwd + "# ")
                        command_buffer = ""
                        
                    else:
                        self.in_newline_sequence = False
                        channel.send(char)
                        # We want to record as much as possible, including symbols
                        if char.isprintable() or char == '\t':
                            command_buffer += char

            except Exception as e:
                logging.error(f"Session error: {e}")
                break
                
        # Wait for all in-flight analysis threads to finish before reporting
        logging.info(f"[{self.session_id}] Waiting for {len(analysis_threads)} analysis threads to complete...")
        for t in analysis_threads:
            t.join(timeout=30)
        
        # Connection End - Trigger Reporting
        trigger_forensic_reporter(self.session_id)
        channel.close()

def start_proxy_server(host='0.0.0.0', port=2222):
    try:
        docker_client = docker.from_env()
    except Exception as e:
        logging.error(f"Docker Daemon unreachable. Ensure docker is running. Error: {e}")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind((host, port))
        sock.listen(100)
        logging.info(f"[*] Gambit Live Proxy Broker listening securely on port {port}")
    except OSError as e:
        logging.error(f"Failed to bind {host}:{port}: {e}")
        return

    active_sessions = []
    while True:
        try:
            client, addr = sock.accept()
            logging.info(f"[+] Proxy connection established from {addr[0]}:{addr[1]}")
            session = HoneypotSession(client, docker_client)
            session.daemon = True
            active_sessions.append(session)
            session.start()
        except KeyboardInterrupt:
            logging.info("Shutting down proxy broker. Generating final reports for all interrupted sessions...")
            for session in active_sessions:
                if session.is_alive():
                    trigger_forensic_reporter(session.session_id)
            break

if __name__ == "__main__":
    start_proxy_server()
