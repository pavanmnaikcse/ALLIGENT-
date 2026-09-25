# Security Policy

## 1. Supported Versions

| Version | Supported | Security Patch Policy |
| :--- | :--- | :--- |
| `1.0.x-rc` | :white_check_mark: | Active security monitoring and rapid hotfixes |
| `< 1.0.0` | :x: | Unsupported legacy development builds |

---

## 2. Reporting a Vulnerability

The ALLIGENT team takes security seriously, especially given the sensitivity of industrial automation and operational technology (OT) environments.

If you discover a security vulnerability or credential leak within this repository, **please DO NOT open a public GitHub issue.**

Instead, report vulnerabilities privately by emailing:
* **Security Contact:** `pavanmnaikcse@gmail.com`
* **Subject:** `[SECURITY] ALLIGENT Vulnerability Report`

Please include in your report:
1. Type of issue (e.g., token exposure, buffer overflow, injection, denial of service).
2. Step-by-step instructions to reproduce the vulnerability.
3. Proof-of-concept payload or script where applicable.
4. Impact assessment on industrial control or telemetry privacy.

You will receive an initial response within 48 hours.

---

## 3. Industrial Security Principles

1. **Air-Gap Capability:** ALLIGENT is designed to operate completely air-gapped without external internet access using local Ollama LLM execution on workstation GPUs.
2. **Read-Only Telemetry:** Ingestion adapters are architected for read-only telemetry acquisition and do not expose machine actuation registers.
3. **Secret Isolation:** API keys (Twilio, Resend, database passwords) must never be committed to git and are loaded strictly from environment variables.
