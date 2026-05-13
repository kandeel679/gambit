# Post-Incident Forensic Report

## Incident ID: Gambit-20260512-Honeypot-SSH

**Date of Report:** 2026-05-12
**Prepared By:** Elite Incident Response Team

---

### 1. Executive Summary

On 2026-05-12, the Gambit honeypot detected and logged an unauthorized access attempt and subsequent activity. The adversary successfully authenticated using a public key against the `root` account. Initial reconnaissance focused on file system discovery and sensitive credential file enumeration. The attacker's behavior indicates a **Human actor** with a **Novice to Script Kiddie skill level**, primarily driven by an **Opportunistic Enumeration** intent, likely seeking exploitable information or credentials.

---

### 2. Attacker Connection Profile

*   **Source IP Address:** `127.0.0.1`
*   **Source Port:** `58180`
*   **Authentication Method:** Public Key authentication was successfully used.
    *   **Attempts:** 2 attempts were made with the same public key.
    *   **Username:** `root`
    *   **Key Fingerprint:** `c966e332a1784d4f6e84e05ce47ee32b`
*   **Connection Timestamp (Attacker Perspective):** 2026-05-12 23:54:31
*   **Session Start (Honeypot Observation):** 2026-05-12T20:54:36.954838
*   **Session Disconnect:** 2026-05-12T20:57:41.769142
*   **Session Duration:** 0 hours, 3 minutes, 4 seconds
*   **Geographic/Network Attribution Assessment:** The attacker IP address `127.0.0.1` is the local loopback address. This typically indicates that the honeypot itself was compromised or accessed locally, or that network Address Translation (NAT) or a proxy is obscuring the true source. Without further network logs or context, external geographic or network attribution is not possible from this data alone.

---

### 3. MITRE ATT&CK Heatmap Summary

The following MITRE ATT&CK TTPs were observed during this incident:

*   **T1083 - File and Directory Discovery**
    *   **Description:** Adversaries may enumerate files and directories to gain information about a system to look for ways to gain access, find information of interest, or discover opportunities for further actions.
*   **T1074 - Data Staged**
    *   **Description:** Adversaries may stage data to a location where it can be collected and exfiltrated. Staging areas may be a local directory, network share, or cloud instance where data is temporarily placed prior to exfiltration.
*   **T1003.008 - OS Credential Dumping: /etc/shadow**
    *   **Description:** Adversaries may attempt to dump credentials from the `/etc/shadow` file on Linux and macOS systems to obtain password hashes for offline cracking or reuse.
*   **T1087.001 - Local Account Discovery**
    *   **Description:** Adversaries may attempt to get a listing of local system accounts to discover those that may be a target for exploitation.

---

### 4. Attack Timeline

The following is a chronological breakdown of the commands executed by the adversary and their assessed intent:

*   **2026-05-12T20:55:18.512856 - Command: `ls`**
    *   **TTP:** T1083 - File and Directory Discovery
    *   **Intent:** To discover files and directories on the compromised system to understand its structure and identify interesting targets for further enumeration or access.
*   **2026-05-12T20:55:21.609223 - Command: `ls`**
    *   **TTP:** T1083 - File and Directory Discovery
    *   **Intent:** To discover files and directories within the current working directory to understand the system's layout and identify potential targets or interesting information.
*   **2026-05-12T20:55:27.519509 - Command: `pwd`**
    *   **TTP:** T1083 - File and Directory Discovery
    *   **Intent:** Determine current working directory for environmental reconnaissance and to inform subsequent actions.
*   **2026-05-12T20:56:05.763251 - Command: `ls`**
    *   **TTP:** T1083 - File and Directory Discovery
    *   **Intent:** To enumerate files and directories in the current working directory as part of initial reconnaissance to understand the file system and identify points of interest.
*   **2026-05-12T20:56:08.190207 - Command: `mkdir hacker`**
    *   **TTP:** T1074 - Data Staged
    *   **Intent:** To establish a dedicated staging directory for collected data, tools, or further operations, thereby organizing the adversary's presence on the compromised system.
*   **2026-05-12T20:56:12.279220 - Command: `cd hacker`**
    *   **TTP:** T1083 - File and Directory Discovery
    *   **Intent:** To navigate to a specific directory (named 'hacker') within the filesystem, likely as part of an exploration or search for tools, data, or areas of interest.
*   **2026-05-12T20:57:00.736770 - Command: `touch root.txt`**
    *   **TTP:** T1083 - File and Directory Discovery
    *   **Intent:** Test write permissions in the current directory as part of reconnaissance or to prepare for dropping files.
*   **2026-05-12T20:57:03.285096 - Command: `cat /etc/shadow`**
    *   **TTP:** T1003.008 - OS Credential Dumping: /etc/shadow
    *   **Intent:** Attempt to collect hashed user passwords for offline cracking or to enumerate existing user accounts on the system.
*   **2026-05-12T20:57:20.837262 - Command: `cat /etc/passwd`**
    *   **TTP:** T1087.001 - Local Account Discovery
    *   **Intent:** To identify local user accounts on the compromised system for further reconnaissance or potential credential access.

---

### 5. Adversary Behavioral Profile

*   **Skill Level Assessment:** **Novice / Script Kiddie**. The adversary utilized very basic Linux commands (`ls`, `pwd`, `cd`, `cat`, `mkdir`, `touch`) primarily for reconnaissance and credential harvesting. The choice of the directory name `hacker` is a strong indicator of a less sophisticated, possibly experimental, human actor rather than a skilled or automated professional adversary. There was no attempt at obfuscation, privilege escalation beyond initial `root` access, or deployment of custom tooling.
*   **Likely Motivation:** **Opportunistic / Data Collection (Credentials)**. The primary intent observed was "Enumeration", focusing on understanding the system layout and, critically, attempting to extract `root` and other user credentials from `/etc/shadow` and `/etc/passwd`. This suggests an opportunistic attacker seeking to gain further access, potentially for broader system control, data theft, or future monetization through credential reuse.
*   **Tool Signatures and Tradecraft Indicators:**
    *   **Common Linux Utilities:** Exclusive use of standard system commands, indicating either a lack of advanced tools or an attempt to remain stealthy by using built-in binaries (though the `mkdir hacker` contradicts stealth).
    *   **Explicit Naming Convention:** Creation of a directory named `hacker` for staging (T1074) is a notable tradecraft indicator of a novice operator.
    *   **Direct Credential Access:** Immediate and direct attempts to `cat /etc/shadow` and `/etc/passwd` after basic reconnaissance, without prior privilege escalation attempts (as they were already `root`).
    *   **Public Key Authentication:** Successful authentication via public key implies either a compromised key, a weak key, or a misconfigured honeypot/system allowing weak public key authentication for `root`.
    *   **No Obfuscation:** Commands were executed directly without any apparent attempts to evade detection or hide activity.

---

### 6. Strategic Recommendations

Based on the observed adversary behavior and attack patterns, the following strategic recommendations are provided to enhance system security:

1.  **Strengthen SSH Access Control:**
    *   **Eliminate Root SSH Login:** Configure SSH to explicitly deny direct `root` login. Users should log in with non-privileged accounts and use `sudo` for administrative tasks.
    *   **Review and Revoke SSH Keys:** Immediately identify and revoke the public key with fingerprint `c966e332a1784d4f6e84e05ce47ee32b` from all critical systems. Investigate how this key came to be associated with a `root` account.
    *   **Implement Strong SSH Key Management:** Ensure all authorized keys are regularly reviewed, rotated, and protected. Consider multi-factor authentication for SSH access where feasible.
    *   **Limit Public Key Usage:** If possible, limit which public keys can access which accounts or apply additional restrictions via `authorized_keys` options.

2.  **Restrict Access to Sensitive Files:**
    *   **Harden `/etc/shadow` and `/etc/passwd` Permissions:** While generally restricted by default, ensure that these files have the most stringent permissions possible (`/etc/shadow` typically readable only by root, `/etc/passwd` readable by all but writable only by root). Regularly audit these permissions.
    *   **Implement File Integrity Monitoring (FIM):** Deploy FIM solutions to detect unauthorized changes to critical system files like `/etc/shadow`, `/etc/passwd`, and `/etc/ssh/authorized_keys`.

3.  **Enhance Log Monitoring and Alerting:**
    *   **Monitor for Common Reconnaissance Commands:** Implement alerts for repeated or suspicious executions of commands like `ls`, `pwd`, `cat /etc/passwd`, `cat /etc/shadow`, especially from new or unusual user sessions or after successful authentication with previously unseen keys.
    *   **Monitor for Account Creation/Modification:** Alert on any attempts to `mkdir` in unusual locations or with suspicious names (e.g., "hacker").

4.  **Security Awareness Training:**
    *   Given the "Script Kiddie" nature, it's a reminder that even basic attacks can succeed against vulnerable systems. Continuous training for administrators on secure configurations and threat awareness is crucial.

5.  **Review Honeypot Placement and Configuration:**
    *   The `127.0.0.1` source IP suggests internal access. Review the network configuration of the honeypot to ensure it accurately reflects expected external attack vectors or, if intended for internal monitoring, ensure its purpose is clearly defined and separated from production assets.

This incident highlights the importance of robust SSH security practices and proactive monitoring to detect even unsophisticated attempts at system compromise and data exfiltration.