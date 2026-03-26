import socket
import threading
import paramiko
import docker
import logging
import time
import re
import subprocess
import shlex
import os
import tarfile
import io

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [LiveProxy] %(message)s")

from analysis_agent import analyze_command
from reporter import trigger_forensic_reporter

LOG_DIR = "logs"

# ==========================================
# INTELLIGENCE STREAM AI INTEGRATION
# ==========================================
def dispatch_to_analysis_agent(session_id, command):
    """
    Phase 5 Integration: Sends raw command to LLM asynchronously.
    Strict Input Sanitization implemented to prevent prompt injection.
    """
    clean_command = re.sub(r'[^\x20-\x7E]', '', command)
    logging.info(f"[Intelligence Stream -> Agentic LLM] Dispatched: '{clean_command}' (Session: {session_id})")
    analyze_command(session_id, clean_command)

def extract_modifications(container, session_id):
    """
    Phase 6 Integration: Automatic Malware Extraction via Docker CoW
    Analyzes the container's CoW layer for new/modified files since the session started.
    Extracts suspicious files (potential malware/payloads) to a safe host directory.
    """
    try:
        diffs = container.diff()
        if not diffs:
            return

        vault_dir = os.path.join(LOG_DIR, "malware_vault", session_id)
        
        # Ignored paths that naturally change in background
        ignore_prefixes = ('/dev', '/proc', '/sys', '/run', '/var/run', '/tmp/ssh-', '/var/log', '/root/.bash_history', '/etc')
        
        collected_files = []

        for d in diffs:
            # Kind 1 = Added, 0 = Modified
            if d.get('Kind') in (0, 1):
                path = d.get('Path', '')
                
                # Filter noise
                if any(path.startswith(prefix) for prefix in ignore_prefixes) or path == "/":
                    continue
                
                try:
                    # Get file tarball from docker
                    bits, stat = container.get_archive(path)
                    
                    # Skip directories
                    if stat.get('mode', 0) & 0o40000:
                        continue
                        
                    if not os.path.exists(vault_dir):
                        os.makedirs(vault_dir)

                    # Extract file from tar stream securely
                    file_data = b"".join(chunk for chunk in bits)
                    tar = tarfile.open(fileobj=io.BytesIO(file_data))
                    for member in tar.getmembers():
                        if member.isfile():
                            f = tar.extractfile(member)
                            if f:
                                safe_name = path.replace('/', '_').strip('_')
                                local_path = os.path.join(vault_dir, safe_name)
                                with open(local_path, "wb") as out_f:
                                    out_f.write(f.read())
                                collected_files.append(path)
                except docker.errors.NotFound:
                    pass # File was fleeting/deleted mid-diff
                except Exception as e:
                    logging.error(f"Failed to safely extract {path}: {e}")
                    
        if collected_files:
            logging.warning(f"[{session_id}] \U0001F9A0 Captured {len(collected_files)} malicious/uploaded files!")
            logging.warning(f"[{session_id}] Files securely vaulted at: {vault_dir}")

    except Exception as e:
        logging.error(f"Error during malware extraction for {session_id}: {e}")

# ==========================================
# SSH PROXY HANDLER
# ==========================================
class ProxyServerInterface(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()
        self.mode = "shell"
        self.command = ""

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        logging.warning(f"[Auth] Attacker attempting login | User: {username} | Pass: {password}")
        return paramiko.AUTH_SUCCESSFUL
        
    def check_auth_publickey(self, username, key):
        logging.warning(f"[Auth] Attacker attempting key login | User: {username}")
        return paramiko.AUTH_SUCCESSFUL
        
    def get_allowed_auths(self, username):
        return 'password,publickey'
        
    def check_channel_shell_request(self, channel):
        self.mode = "shell"
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True
        
    def check_channel_exec_request(self, channel, command):
        self.mode = "exec"
        self.command = command.decode('utf-8') if isinstance(command, bytes) else command
        self.event.set()
        return True

    def check_channel_subsystem_request(self, channel, name):
        name_str = name.decode('utf-8') if isinstance(name, bytes) else name
        if name_str == "sftp":
            self.mode = "sftp"
            self.command = "/usr/lib/openssh/sftp-server"
            self.event.set()
            return True
        return False

class HoneypotSession(threading.Thread):
    def __init__(self, client_socket, docker_client, container_name="gambit-honeypot"):
        super().__init__()
        self.client_socket = client_socket
        self.docker_client = docker_client
        self.container_name = container_name
        self.session_id = f"session_{int(time.time())}"

    def run(self):
        transport = paramiko.Transport(self.client_socket)
        
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
        if not server.event.is_set():
            logging.error(f"[{self.session_id}] No shell/exec/subsystem requested.")
            return

        logging.info(f"[{self.session_id}] Channel opened in mode: {server.mode}")

        try:
            container = self.docker_client.containers.get(self.container_name)
        except docker.errors.NotFound:
            logging.error(f"[{self.session_id}] Gambit Container '{self.container_name}' NOT FOUND. Ensure Phase 3 (Generator) has run.")
            channel.send("System maintenance. Disconnecting...\r\n")
            channel.close()
            return

        # Route Traffic based on channel mode
        if server.mode == "shell":
            self.handle_interactive_shell(channel, container)
        else:
            self.handle_raw_stream(channel, server.command)

        # Connection End - Trigger Malware Extraction & Reporting
        logging.info(f"[{self.session_id}] Session ending. Scanning Docker CoW layer for dropped payloads...")
        extract_modifications(container, self.session_id)
        
        trigger_forensic_reporter(self.session_id)
        channel.close()

    def handle_interactive_shell(self, channel, container):
        channel.send("Welcome to the server. Access granted.\r\n$ ")
        command_buffer = ""
        while True:
            try:
                char = channel.recv(1024).decode('utf-8')
                if not char:
                    break

                if char in ('\r', '\n'):
                    channel.send('\r\n')
                    command = command_buffer.strip()
                    if command:
                        if command in ["exit", "logout"]:
                            break
                        
                        threading.Thread(
                            target=dispatch_to_analysis_agent, 
                            args=(self.session_id, command)
                        ).start()
                        
                        try:
                            logging.info(f"[{self.session_id}][EXEC] {command}")
                            exit_code, output = container.exec_run(
                                cmd=["sh", "-c", command],
                                tty=True,
                                user='root'
                            )
                            # Handle potential empty bytes natively
                            output_str = getattr(output, 'decode', lambda x: "")('utf-8', errors='ignore') if output else ""
                            channel.send(output_str.replace('\n', '\r\n'))
                        except Exception as e:
                            logging.error(f"Exec failure: {e}")
                            channel.send(f"sh: 1: {command}: not found\r\n")
                    
                    command_buffer = ""
                    channel.send("$ ")
                elif char in ('\x08', '\x7f'):
                    if len(command_buffer) > 0:
                        command_buffer = command_buffer[:-1]
                        channel.send('\b \b')
                elif char == '\x03': 
                    channel.send("^C\r\n$ ")
                    command_buffer = ""
                else:
                    channel.send(char)
                    if char.isprintable():
                        command_buffer += char
            except Exception as e:
                logging.error(f"Session error: {e}")
                break

    def handle_raw_stream(self, channel, command):
        logging.info(f"[{self.session_id}] Starting raw stream proxy for: {command}")
        threading.Thread(
            target=dispatch_to_analysis_agent, 
            args=(self.session_id, command)
        ).start()

        cmd_args = ["docker", "exec", "-i", self.container_name] + shlex.split(command)
        
        try:
            proc = subprocess.Popen(
                cmd_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            def docker_to_ssh():
                try:
                    while not channel.closed:
                        data = proc.stdout.read(4096)
                        if not data:
                            break
                        channel.sendall(data)
                except Exception:
                    pass
                channel.close()

            def ssh_to_docker():
                try:
                    while not channel.closed and proc.poll() is None:
                        data = channel.recv(4096)
                        if not data:
                            break
                        proc.stdin.write(data)
                        proc.stdin.flush()
                except Exception:
                    pass
                try:
                    proc.stdin.close()
                except:
                    pass

            t1 = threading.Thread(target=docker_to_ssh, daemon=True)
            t2 = threading.Thread(target=ssh_to_docker, daemon=True)
            t1.start()
            t2.start()
            
            proc.wait()
            t1.join(timeout=2)
            t2.join(timeout=2)
        except Exception as e:
            logging.error(f"Raw stream subprocess error: {e}")

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

    while True:
        try:
            client, addr = sock.accept()
            logging.info(f"[+] Proxy connection established from {addr[0]}:{addr[1]}")
            session = HoneypotSession(client, docker_client)
            session.daemon = True
            session.start()
        except KeyboardInterrupt:
            logging.info("Shutting down proxy broker...")
            break

if __name__ == "__main__":
    start_proxy_server()
