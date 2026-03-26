"""
Ollama LLM Integration Module for ShadowTrap AI Honeypot
========================================================
This module handles all communication with the local Ollama LLM server.
It provides two main functions:
  1. ollama_llm_response() — Generates realistic terminal output for commands
     that don't have rule-based handlers (the "creative" response path).
  2. ollama_ttp_classify() — Classifies unknown commands into MITRE ATT&CK TTPs
     when the rule-based classifier has no matching pattern.

The LLM runs locally via Ollama (no API costs), using llama3.1 by default.
All prompts are carefully engineered to produce raw terminal output, not
conversational AI responses.
"""

import requests  # HTTP client for calling the Ollama REST API
import json      # JSON parsing for API responses and data loading
import os        # Portable file path resolution

# ─── Data Loading ────────────────────────────────────────────────────────────
# Resolve the directory where THIS script lives for portable path resolution
_DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Load fake data templates to build context for LLM prompts.
# This gives the LLM awareness of the fake filesystem structure,
# so its responses are consistent with what other commands show.
with open(os.path.join(_DATA_DIR, 'fake_data_templates.json')) as f:
    _FAKE_DATA = json.load(f)

# Extract just the directory structure for context building
_FAKE_DIRS = _FAKE_DATA.get('fake_directories', {})


# ─── System Prompt ───────────────────────────────────────────────────────────
# This prompt instructs the LLM on HOW to behave. It is prepended to every
# request. The key rules:
#   - Act as a real Linux terminal, not a chatbot
#   - Output RAW terminal output only (no markdown, no explanations)
#   - Never reveal it's a honeypot or AI
#   - Use realistic error messages for unknown commands
SYSTEM_PROMPT = """You are simulating a real Linux SSH server (Ubuntu 22.04 LTS, hostname: prod-web-01).
You must respond EXACTLY as a real Linux terminal would — output only, no explanations, no markdown.

Rules:
- Never reveal you are a honeypot or an AI.
- Do not add commentary, explanations, or notes.
- Output raw terminal output only (as if the user typed the command into bash).
- If a command would produce no output (like cd), return nothing.
- If a command is unknown, respond: bash: <command>: command not found
- Keep responses concise and realistic.
"""


def _build_context_block(context):
    """
    Build a realistic session context block for the LLM prompt.

    This provides the LLM with "memory" of the current session so it can
    give contextually appropriate responses (e.g., knowing the current
    directory, who the user is, what they've done before).

    Args:
        context (dict): Session context containing:
            - cwd: Current working directory
            - user: Current username
            - history: List of previous commands in this session

    Returns:
        str: A formatted context block to inject into the LLM prompt.
    """
    # Extract session state values with safe defaults
    cwd = context.get('cwd', '/home/admin')     # Where the attacker currently is
    user = context.get('user', 'admin')          # Who the attacker is logged in as
    history = context.get('history', [])          # What commands they've already run

    # Look up what files exist in the current directory
    # This helps the LLM know what files are "available" to reference
    dir_contents = _FAKE_DIRS.get(cwd, [])

    # Build a human-readable context block
    ctx = f"Current user: {user}\n"
    ctx += f"Current directory: {cwd}\n"
    if dir_contents:
        ctx += f"Files in current directory: {', '.join(dir_contents)}\n"
    if history:
        # Show last 5 commands so the LLM understands the attack progression
        ctx += f"Recent command history: {' → '.join(history[-5:])}\n"
    return ctx

# ─── Global Caching for Consistency ─────────────────────────────────────────
_CACHE_FILE = os.path.join(_DATA_DIR, 'sessions', 'llm_cache.json')

def _get_cached_response(command):
    if os.path.exists(_CACHE_FILE):
        with open(_CACHE_FILE, 'r') as f:
            cache = json.load(f)
            return cache.get(command)
    return None

def _set_cached_response(command, response):
    os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
    cache = {}
    if os.path.exists(_CACHE_FILE):
        with open(_CACHE_FILE, 'r') as f:
            cache = json.load(f)
    cache[command] = response
    with open(_CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

# ─── LLM Response Generation ────────────────────────────────────────────────

def ollama_llm_response(command, context, model='llama3.1'):
    """
    Query the local Ollama LLM to generate a realistic terminal response.

    This function is called by the hybrid router when no rule-based handler
    exists for a command. It constructs a detailed prompt with session context
    and asks the LLM to respond as a real Linux terminal would.

    Args:
        command (str): The attacker's command to respond to.
        context (dict): Session context (cwd, user, history).
        model (str): Ollama model name. Default is 'llama3.1'.

    Returns:
        str: The simulated terminal output, or a realistic error message
             if the LLM call fails.
    """
    # Check cache first for absolute consistency across attackers/devices
    cached = _get_cached_response(command)
    if cached:
        return cached

    # Build the session context block for prompt injection
    context_block = _build_context_block(context)

    # Construct the full prompt: system instructions + session context + command
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"                            # How to behave
        f"Session state:\n{context_block}\n"              # Current session context
        f"The user runs the following command:\n$ {command}\n\n"  # The actual command
        f"Respond with the exact terminal output this command would produce:"  # Output format
    )

    try:
        # Send the prompt to the local Ollama API server
        ollama_url = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
        response = requests.post(
            f'{ollama_url}/api/generate',  # Ollama's REST endpoint
            json={
                'model': model,       # Which LLM model to use (e.g., llama3.1)
                'prompt': prompt,     # The complete prompt text
                'stream': False,      # Wait for complete response (don't stream tokens)
                'options': {
                    'temperature': 0.3,   # Low temperature = more deterministic, less creative
                    'top_p': 0.9,         # Nucleus sampling — keeps output focused
                    'num_predict': 128    # Max tokens to generate (keeps responses concise)
                }
            },
            timeout=15  # Fail fast if Ollama is slow or unresponsive (15 seconds max)
        )
        # Raise an exception if the HTTP status code indicates an error (4xx, 5xx)
        response.raise_for_status()

        # Parse the JSON response and extract the generated text
        result = response.json()
        output = result.get('response', '').strip() or f'bash: {command.split()[0]}: command not found'
        
        # Save to global cache so all future attackers see the exact same output
        _set_cached_response(command, output)
        return output

    except requests.exceptions.ConnectionError:
        # Ollama server not running — return a realistic "command not found" error
        # This graceful degradation means the honeypot works even without Ollama
        return f"bash: {command.split()[0] if command.split() else command}: command not found"

    except Exception as e:
        # Any other error (timeout, invalid response, etc.)
        # Still return a realistic error rather than exposing the real error
        return f"bash: {command.split()[0] if command.split() else command}: command not found"


# ─── LLM TTP Classification ─────────────────────────────────────────────────

def ollama_ttp_classify(command, context, candidate_ttps, model='llama3.1'):
    """
    Use the LLM to classify an unknown command into MITRE ATT&CK TTPs.

    This is the FALLBACK classifier — it's only called when the rule-based
    classifier (mitre_mapping.json) has no matching pattern AND the command
    isn't in the benign whitelist. It asks the LLM to analyze the command
    and pick the most relevant TTP from the candidate list.

    Args:
        command (str): The command to classify.
        context (dict): Session context (cwd, user, history).
        candidate_ttps (list): List of MITRE entries to choose from.
        model (str): Ollama model name. Default is 'llama3.1'.

    Returns:
        dict: Classification result with keys:
            - command: The original command
            - matched_ttp: The TTP ID chosen by the LLM (or "UNKNOWN")
            - confidence: 0.0 to 0.85 (capped below rule-based confidence)
            - method: Always "llm"
            - llm_explanation: The LLM's reasoning
    """
    # Format the first 15 candidate TTPs as a readable list for the prompt
    # We limit to 15 to avoid making the prompt too long (faster inference)
    ttp_list = '\n'.join([f"- {t['ttp_id']}: {t['description']} (pattern: {t['pattern']})"
                          for t in candidate_ttps[:15]])

    # Build a structured prompt that forces the LLM to respond in a parseable format
    prompt = (
        f"You are a cybersecurity analyst. Analyze this command and classify it using MITRE ATT&CK.\n\n"
        f"Command: {command}\n"
        f"Session context: user={context.get('user', 'unknown')}, "
        f"cwd={context.get('cwd', '/unknown')}, "
        f"recent history: {context.get('history', [])[-5:]}\n\n"
        f"Known MITRE ATT&CK techniques:\n{ttp_list}\n\n"
        # Force structured output format for reliable parsing
        f"Respond in EXACTLY this format (no other text):\n"
        f"TTP_ID: <the most relevant TTP ID, or UNKNOWN>\n"
        f"CONFIDENCE: <0.0 to 1.0>\n"
        f"EXPLANATION: <one sentence explanation>"
    )

    try:
        # Send classification request to Ollama
        ollama_url = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
        response = requests.post(
            f'{ollama_url}/api/generate',
            json={
                'model': model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.1,  # Very low temperature for consistent classification
                    'num_predict': 64    # Short response — just TTP_ID, CONFIDENCE, EXPLANATION
                }
            },
            timeout=15  # 15 second timeout for classification
        )
        response.raise_for_status()

        # Extract the raw text response from the LLM
        result = response.json().get('response', '')

        # Parse the structured response into our classification format
        return _parse_ttp_response(result, command)

    except Exception as e:
        # If the LLM is unavailable, return UNKNOWN with low confidence
        # The system still functions — it just can't classify unknown commands
        return {
            'command': command,
            'matched_ttp': 'UNKNOWN',
            'confidence': 0.3,
            'method': 'llm',
            'llm_explanation': f'LLM classification unavailable: {e}'
        }


def _parse_ttp_response(raw_response, command):
    """
    Parse the structured LLM TTP classification response.

    The LLM is instructed to respond in a specific format:
        TTP_ID: T1105
        CONFIDENCE: 0.8
        EXPLANATION: The command downloads a remote file.

    This function extracts those fields from the raw text.

    Args:
        raw_response (str): The raw text from the LLM.
        command (str): The original command (for inclusion in the result).

    Returns:
        dict: Parsed classification result.
    """
    # Set defaults in case parsing fails
    ttp_id = 'UNKNOWN'        # Default TTP ID if not parsed
    confidence = 0.5          # Default confidence (medium)
    explanation = raw_response.strip()  # Fallback: use the entire raw response

    # Parse each line of the LLM response looking for our structured fields
    for line in raw_response.strip().split('\n'):
        line = line.strip()
        if line.upper().startswith('TTP_ID:'):
            # Extract the TTP ID after the colon
            ttp_id = line.split(':', 1)[1].strip()
        elif line.upper().startswith('CONFIDENCE:'):
            # Extract and parse the confidence score
            try:
                confidence = float(line.split(':', 1)[1].strip())
            except ValueError:
                confidence = 0.5  # Keep default if parsing fails
        elif line.upper().startswith('EXPLANATION:'):
            # Extract the explanation text
            explanation = line.split(':', 1)[1].strip()

    # Build and return the structured classification result
    return {
        'command': command,
        'matched_ttp': ttp_id,
        'confidence': min(confidence, 0.85),  # Cap at 0.85 — LLM should never be as confident as rule-based (0.95)
        'method': 'llm',
        'llm_explanation': explanation
    }

# ─── LLM Deep Pre-generation ────────────────────────────────────────────────

def ollama_generate_file_content(filepath, description, model='llama3.1'):
    """
    Use the LLM to generate highly realistic, extensive file content during startup.
    This creates an authentic honeypot environment entirely uniquely.

    Args:
        filepath (str): The name/path of the file to generate
        description (str): Instructions on what the file should contain
        model (str): Ollama model name

    Returns:
        str: The generated realistic content for the file.
    """
    prompt = (
        f"You are a backend honeypot generator. Your job is to output the RAW, authentic content "
        f"for a file located at `{filepath}` on a production Ubuntu Linux environment.\n"
        f"Context/Requirements: {description}\n\n"
        f"Output ONLY the file contents. Do not wrap it in markdown code blocks. Do not explain anything.\n"
        f"Produce highly realistic, lengthy, and believable data that would fool a hacker."
    )
    
    try:
        ollama_url = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
        response = requests.post(
            f'{ollama_url}/api/generate',
            json={
                'model': model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'num_predict': 1024
                }
            },
            timeout=60
        )
        response.raise_for_status()
        content = response.json().get('response', '')
        # Clean potential markdown wrapping often added by LLMs
        if content.startswith('```'):
            lines = content.split('\n')
            if len(lines) > 2:
                content = '\n'.join(lines[1:-1])
        return content.strip() + '\n'
    except Exception as e:
        print(f"Failed to pre-generate {filepath}: {e}")
        return None

# ─── LLM Session Analysis ───────────────────────────────────────────────────

def ollama_analyze_session(timeline, model='llama3.1'):
    """
    Analyze the complete session timeline to generate a qualitative incident report.

    Args:
        timeline (list): List of all commands and TTPs from the session.
        model (str): Ollama model name. Default is 'llama3.1'.

    Returns:
        str: A generated report summarizing the attacker's intent and techniques.
    """
    if not timeline:
        return "No commands were executed during this session."

    # Build a compact representation of the session for the LLM
    session_log = ""
    for event in timeline:
        cmd = event.get('command', '')
        ttp = event.get('classification')
        if ttp and ttp.get('matched_ttp') and ttp.get('matched_ttp') != 'UNKNOWN':
            session_log += f"$ {cmd}  [TTP: {ttp['matched_ttp']}]\n"
        else:
            session_log += f"$ {cmd}\n"

    prompt = (
        "You are an expert cybersecurity incident responder. Analyze the following sequence of "
        "commands executed by an attacker in a honeypot environment.\n"
        "Identify their primary objective, the techniques they used, and summarize the attack flow.\n\n"
        "Session Log:\n"
        f"{session_log}\n\n"
        "Provide a concise, professional paragraph summarizing the attack."
    )

    try:
        ollama_url = os.environ.get('OLLAMA_HOST', 'http://localhost:11434')
        response = requests.post(
            f'{ollama_url}/api/generate',
            json={
                'model': model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.4,
                    'num_predict': 256
                }
            },
            timeout=20
        )
        response.raise_for_status()
        return response.json().get('response', 'Analysis formulation failed.')
    except Exception as e:
        return f"Could not generate analysis due to LLM error: {e}"


# ─── Standalone Testing ─────────────────────────────────────────────────────

def main():
    """Test both response generation and TTP classification."""
    # Sample session context
    context = {'cwd': '/home/admin', 'user': 'admin', 'history': ['ls', 'pwd', 'cat /etc/passwd']}

    # Test response generation
    print("=== Response Generation ===")
    print(ollama_llm_response('sudo su', context))
    print()
    print(ollama_llm_response('find / -perm -4000 2>/dev/null', context))
    print()

    # Test TTP classification
    print("=== TTP Classification ===")
    sample_ttps = [
        {"pattern": "wget*", "ttp_id": "T1105", "description": "Ingress Tool Transfer"},
        {"pattern": "curl*", "ttp_id": "T1105", "description": "Ingress Tool Transfer"},
        {"pattern": "python*", "ttp_id": "T1059.006", "description": "Command and Scripting Interpreter: Python"},
    ]
    result = ollama_ttp_classify('python -c "import socket; s=socket.socket()"', context, sample_ttps)
    print(json.dumps(result, indent=2))


# Only run main() when this script is executed directly (not when imported)
if __name__ == '__main__':
    main()
