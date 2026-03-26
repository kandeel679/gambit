#!/usr/bin/env python3
import logging
from gui_server import run_gui_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [GambitMain] %(message)s")

def main():
    print("""
    ========================================================
     GAMBIT V2 - Unified Honeypot Orchestrator
    ========================================================
    """)
    print("[*] Launching Unified Web Interface...")
    try:
        run_gui_server(blocking=True)
    except KeyboardInterrupt:
        print("\nShutting down. Goodbye!")

if __name__ == "__main__":
    main()
