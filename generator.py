import docker
import json
import logging
import os
import shutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [Generator] %(message)s")

class GambitGenerator:
    """
    Phase 3: Deployment & Generation
    Programmatically builds and runs the honeypot Docker container in an isolated network 
    based on the AI-synthesized gambit_blueprint.json.
    """
    def __init__(self):
        self.client = docker.from_env()
        self.network_name = "gambit-isolation-net"
        self.container_name = "gambit-honeypot"
        self.build_context = "./build_context"

    def setup_isolation_network(self):
        """Creates an internal docker bridge network so the container cannot dial home."""
        try:
            network = self.client.networks.get(self.network_name)
            logging.info(f"Isolation network '{self.network_name}' found.")
        except docker.errors.NotFound:
            logging.info(f"Creating strictly isolated bridge network '{self.network_name}'...")
            # 'internal=True' disconnects the network from all external internet access
            self.client.networks.create(self.network_name, driver="bridge", internal=True)

    def prepare_build_context(self, blueprint):
        logging.info("Preparing Docker build context...")
        if os.path.exists(self.build_context):
            shutil.rmtree(self.build_context)
        os.makedirs(self.build_context)

        # 1. Write the Honey Artifacts locally to COPY them over safely
        artifacts = blueprint.get("honey_artifacts", [])
        for i, artifact in enumerate(artifacts):
            local_artifact_path = os.path.join(self.build_context, f"artifact_{i}")
            with open(local_artifact_path, 'w') as f:
                f.write(artifact.get("content", ""))

        # 2. Write the Dockerfile
        docker_bp = blueprint.get("docker_blueprint", {})
        base_image = docker_bp.get("base_image", "ubuntu:22.04")
        instructions = docker_bp.get("dockerfile_instructions", [])
        
        dockerfile_path = os.path.join(self.build_context, "Dockerfile")
        with open(dockerfile_path, 'w') as f:
            f.write(f"FROM {base_image}\n")
            
            # Universal commands to prevent crashes
            if "ubuntu" in base_image or "debian" in base_image:
                f.write("RUN apt-get update && apt-get install -y procps coreutils vim curl iproute2 \n")
            
            valid_cmds = ("RUN ", "COPY ", "ADD ", "ENV ", "USER ", "WORKDIR ", "EXPOSE ", "CMD ", "ENTRYPOINT ", "ARG ")
            for inst in instructions:
                inst_stripped = inst.strip()
                if not any(inst_stripped.startswith(cmd) for cmd in valid_cmds):
                    inst = f"RUN {inst_stripped}"
                
                # Sanitize literal newlines that break Dockerfile parsing
                inst = inst.replace('\n', '\\n')
                f.write(f"{inst}\n")
                
            # Copy artifacts into the container
            for i, artifact in enumerate(artifacts):
                target_path = artifact.get("path")
                target_dir = os.path.dirname(target_path)
                if target_dir and target_dir != "/":
                    f.write(f"RUN mkdir -p {target_dir}\n")
                f.write(f"COPY artifact_{i} {target_path}\n")
            
            # Idle loop to keep container alive indefinitely for the proxy Broker
            f.write('CMD ["tail", "-f", "/dev/null"]\n')
            
        logging.info(f"Context written. Included {len(artifacts)} embedded honey tokens.")

    def build_and_deploy(self, blueprint_path='gambit_blueprint.json'):
        if not os.path.exists(blueprint_path):
            logging.error(f"Blueprint {blueprint_path} not found. Synthesize it first.")
            return False

        with open(blueprint_path, 'r') as f:
            blueprint = json.load(f)

        self.setup_isolation_network()
        self.prepare_build_context(blueprint)

        logging.info("Building Honeypot Docker Image (Gambit Twin)...")
        try:
            image, build_logs = self.client.images.build(path=self.build_context, tag="gambit:latest", rm=True)
            for log in build_logs:
                if 'stream' in log:
                    line = log['stream'].strip()
                    if line: logging.info(f"Build: {line}")
        except Exception as e:
            logging.error(f"Docker Image Build Failed: {e}")
            return False

        # Terminate old twins
        try:
            old_container = self.client.containers.get(self.container_name)
            logging.info("Stopping obsolete honeypot container...")
            old_container.stop()
            old_container.remove()
        except docker.errors.NotFound:
            pass

        # Deploy Isolated Container
        logging.info(f"Deploying Honeypot container to strictly isolated namespace: {self.network_name}")
        try:
            container = self.client.containers.run(
                "gambit:latest",
                name=self.container_name,
                network=self.network_name,
                detach=True,
                tty=True
            )
            logging.info(f"[+] SUCCESS! Gambit Honeypot Deployment Complete. Container ID: {container.short_id}")
            return True
        except Exception as e:
            logging.error(f"Failed to launch Honeypot: {e}")
            return False

if __name__ == "__main__":
    pass
