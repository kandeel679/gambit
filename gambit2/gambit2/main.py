#!/usr/bin/env python3
import os
import sys
import time
import logging
from dotenv import load_dotenv, set_key

# Import Gambit Modules
from clone_source import CloneSource
from llm_client import GambitLLMClient
from generator import GambitGenerator
from proxy_server import start_proxy_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [GambitMain] %(message)s")

def print_banner():
    banner = """
    ========================================================
     ██████╗  █████╗ ███╗   ███╗██████╗ ██╗████████╗
    ██╔════╝ ██╔══██╗████╗ ████║██╔══██╗██║╚══██╔══╝
    ██║  ███╗███████║██╔████╔██║██████╔╝██║   ██║   
    ██║   ██║██╔══██║██║╚██╔╝██║██╔══██╗██║   ██║   
    ╚██████╔╝██║  ██║██║ ╚═╝ ██║██████╔╝██║   ██║   
     ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚═════╝ ╚═╝   ╚═╝   
    Project Gambit V2 - Unified Honeypot Orchestrator
    ========================================================
    """
    print(banner)

def main():
    print_banner()
    load_dotenv()
    env_path = ".env"
    
    print("\n=== LLM Configuration Setup ===")
    provider_choice = input("Choose LLM Provider (1 for Gemini API, 2 for Ollama) [default: 1]: ").strip()
    if provider_choice == "2":
        os.environ["LLM_PROVIDER"] = "ollama"
        set_key(env_path, "LLM_PROVIDER", "ollama")
        
        default_ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        ollama_host = input(f"Enter Ollama Host [default: {default_ollama_host}]: ").strip()
        if ollama_host:
            os.environ["OLLAMA_HOST"] = ollama_host
            set_key(env_path, "OLLAMA_HOST", ollama_host)
            
        default_ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1")
        ollama_model = input(f"Enter Ollama Model [default: {default_ollama_model}]: ").strip()
        if ollama_model:
            os.environ["OLLAMA_MODEL"] = ollama_model
            set_key(env_path, "OLLAMA_MODEL", ollama_model)
    else:
        os.environ["LLM_PROVIDER"] = "gemini"
        set_key(env_path, "LLM_PROVIDER", "gemini")
        if not os.getenv("GEMINI_API_KEY"):
            logging.warning("GEMINI_API_KEY is not set in your .env file! Analysis and Synthesis will run in fallback/stub mode.")
            time.sleep(2)

    print("\n=== Target Discovery Setup ===")
    target_ip = input("Enter target IP to clone [default: 127.0.0.1]: ") or "127.0.0.1"
    target_user = input("Enter SSH username [default: root]: ") or "root"
    target_port = input("Enter SSH Port [default: 22]: ") or "22"
    target_pass = input("Enter SSH password: ")

    print("\n[Phase 1/4] Remote Source Discovery (DNA Extraction)")
    discoverer = CloneSource(target_ip, target_port, target_user, password=target_pass)
    if not discoverer.connect():
        logging.error("Failed to connect to Source. Exiting pipeline.")
        sys.exit(1)
    
    success = discoverer.extract_dna("source_metadata.json")
    discoverer.close()
    if not success: sys.exit(1)

    print("\n[Phase 2/4] Agentic Blueprint Synthesis")
    llm = GambitLLMClient()
    success = llm.synthesize_blueprint("source_metadata.json", "gambit_blueprint.json")
    if not success: sys.exit(1)

    print("\n[Phase 3/4] Docker Honeypot Generation & Deployment")
    generator = GambitGenerator()
    success = generator.build_and_deploy("gambit_blueprint.json")
    if not success: sys.exit(1)

    print("\n[Phase 4/4] Activating Live Dual-Stream Proxy Broker")
    print("------------------------------------------------------------------")
    print("🎯 The Gambit Decoy is now LIVE & ISOLATED.")
    print("👾 Act as an attacker by opening a new terminal and running:")
    print("   ssh attacker@localhost -p 2222")
    print("------------------------------------------------------------------\n")
    try:
        start_proxy_server(host='0.0.0.0', port=2222)
    except KeyboardInterrupt:
        logging.info("\nShutting down Gambit Orchestrator. Goodbye!")

if __name__ == "__main__":
    main()
