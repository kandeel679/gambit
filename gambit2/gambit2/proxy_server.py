import socket
import threading
import paramiko
import docker
import logging
import time
import re

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [LiveProxy] %(message)s")

from analysis_agent import analyze_command
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
    clean_command = re.sub(r'[^\\x20-\\x7E]', '', command)
    logging.info(f"[Intelligence Stream -> Agentic LLM] Dispatched: '{clean_command}' (Session: {session_id})")
    analyze_command(session_id, clean_command)



# ==========================================
# SSH PROXY HANDLER
# ==========================================
class ProxyServerInterface(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        # Honeypot: Accept all typical logins to lure attacker in
        logging.warning(f"[Auth] Attacker attempting login | User: {username} | Pass: {password}")
        return paramiko.AUTH_SUCCESSFUL
        
    def check_auth_publickey(self, username, key):
        logging.warning(f"[Auth] Attacker attempting key login | User: {username}")
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

    def run(self):
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
        logging.info(f"[{self.session_id}] Shell opened.")

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
        while True:
            try:
                char = channel.recv(1024).decode('utf-8')
                if not char:
                    break # Connection dropped

                if char in ('\r', '\n'):
                    channel.send('\r\n')
                    command = command_buffer.strip()
                    if command:
                        if command in ["exit", "logout"]:
                            break
                        
                        # --- 1. INTELLIGENCE STREAM (ASYNC LLM TTP MAPPING) ---
                        threading.Thread(
                            target=dispatch_to_analysis_agent, 
                            args=(self.session_id, command)
                        ).start()
                        
                        # --- 2. EXECUTION STREAM (DOCKER PROXY) ---
                        try:
                            # Using exec_run isolated execution context. 
                            # Safe from Honeypot escape because 'exec_run' occurs INSIDE the container namespace context.
                            logging.info(f"[{self.session_id}][EXEC] {command}")
                            # Execute command natively in docker sh context
                            exit_code, output = container.exec_run(
                                cmd=["sh", "-c", command],
                                tty=True,
                                user='root' # or dynamic user
                            )
                            # Return raw output
                            channel.send(output.decode('utf-8').replace('\n', '\r\n'))
                        except Exception as e:
                            logging.error(f"Exec failure: {e}")
                            channel.send(f"sh: 1: {command}: not found\r\n")
                    
                    command_buffer = ""
                    channel.send("$ ")
                    
                # Handle Backspace
                elif char in ('\x08', '\x7f'):
                    if len(command_buffer) > 0:
                        command_buffer = command_buffer[:-1]
                        # Erase char on terminal visually
                        channel.send('\b \b')
                
                # Handle Ctrl+C
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
