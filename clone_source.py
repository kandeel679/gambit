import paramiko
import json
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [CloneSource] %(message)s")

class CloneSource:
    """
    Phase 1: Remote Source Discovery
    Connects to a 'Source of Truth' server via SSH and extracts its DNA (metadata)
    to generate highly realistic honeypot environments.
    """
    def __init__(self, host, port, username, password=None, key_filename=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self):
        logging.info(f"Connecting to Source Server {self.host}:{self.port} as {self.username}...")
        try:
            self.client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                key_filename=self.key_filename,
                timeout=15
            )
            logging.info("Connected successfully.")
            return True
        except Exception as e:
            logging.error(f"Failed to connect: {e}")
            return False

    def run_command(self, cmd, default=""):
        try:
            stdin, stdout, stderr = self.client.exec_command(cmd)
            result = stdout.read().decode('utf-8').strip()
            err = stderr.read().decode('utf-8').strip()
            if err and not result:
                return default
            return result
        except Exception as e:
            logging.error(f"Error executing command '{cmd}': {e}")
            return default

    def extract_dna(self, output_file='source_metadata.json'):
        if not self.client.get_transport() or not self.client.get_transport().is_active():
            logging.error("SSH client is not connected.")
            return False

        metadata = {}
        logging.info("Initiating DNA Extraction protocol...")

        # 1. OS & Kernel Versions
        logging.info("-> Extracting OS & Kernel Version")
        metadata['os_release'] = self.run_command('cat /etc/os-release')
        metadata['kernel_version'] = self.run_command('uname -r')

        # 2. Environment Variables
        logging.info("-> Extracting Environment Variables (Filtered)")
        metadata['env_vars'] = self.run_command('env | grep -E "PATH|USER|HOME|SHELL|LANG"')

        # 3. Active User List (Real Users)
        logging.info("-> Extracting Active User List")
        metadata['users'] = self.run_command("cat /etc/passwd | awk -F: '$3 >= 1000 {print $1\":\"$3\":\"$6\":\"$7}'")

        # 4. Network Topology 
        logging.info("-> Mapping Network Topology (ARP & Open Ports)")
        metadata['arp_table'] = self.run_command('arp -a')
        metadata['listening_ports'] = self.run_command('ss -tuln || netstat -tuln')
        metadata['established_connections'] = self.run_command('ss -unpA tcp state established || netstat -tun | grep ESTABLISHED | head -n 20')

        # 5. Service Configurations
        logging.info("-> Scraping Service Configurations")
        metadata['active_services'] = self.run_command('systemctl list-units --type=service --state=running || ls /var/run/*.pid')
        metadata['cron_jobs'] = self.run_command('crontab -l 2>/dev/null || ls -la /etc/cron.*')

        # 6. File Hierarchy Samples
        logging.info("-> Sampling File Hierarchies (/var/www, /etc, /home)")
        metadata['file_hierarchy'] = {
            'var_www': self.run_command('ls -la /var/www 2>/dev/null | head -n 30'),
            'etc': self.run_command('ls -la /etc 2>/dev/null | head -n 30'),
            'home_dirs': self.run_command('ls -la /home 2>/dev/null')
        }

        # Dump to JSON
        with open(output_file, 'w') as f:
            json.dump(metadata, f, indent=4)
        
        logging.info(f"DNA Extraction Complete. Metadata saved securely to {output_file}")
        return True

    def close(self):
        self.client.close()
        logging.info("Connection closed.")

if __name__ == "__main__":
    # Example local stub invocation for verification
    # discoverer = CloneSource("127.0.0.1", 22, "root", password="root")
    # if discoverer.connect():
    #     discoverer.extract_dna("source_metadata.json")
    #     discoverer.close()
    pass
