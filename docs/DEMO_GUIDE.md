# ALLIGENT Step-by-Step Demonstration & Evaluation Guide

**Product:** ALLIGENT — AI-Powered Industrial Investigation & Decision Support  
**Document:** Interactive Demonstration Walkthrough  
**Version:** 1.0.0  

---

## 1. Quick Start Demonstration Overview

This guide provides an end-to-end evaluation walkthrough of the **ALLIGENT** platform for engineering review panels, hackathon judges, and industrial reliability teams.

In this demonstration, you will:
1. Observe baseline nominal 10Hz digital twin telemetry on an interactive 3D spindle visualizer.
2. Modulate machine parameters in real time via the **Mobile Gateway**.
3. Trigger an industrial thermal-lubrication failure scenario.
4. Watch the **11-Agent Orchestrator** diagnose the root cause and execute a **Counterfactual Replay**.
5. Inspect the generated **21-Section Engineering PDF Report** and receive an **Executive Email & Twilio Voice Call**.

---

## 2. Environment Setup & Launch

Ensure Docker and Docker Compose are installed and running:

```bash
# Clone the repository
git clone https://github.com/pavanmnaikcse/ALLIGENT-.git
cd ALLIGENT-

# Configure environment variables
cp .env.example .env

# Launch the unified industrial stack
docker compose up -d
```

### Active Service Ports
* **ALLIGENT Desktop Console:** `http://localhost:80`
* **FastAPI Backend & API Docs:** `http://localhost:8000/docs`
* **Mobile Operator Gateway:** `http://localhost:3000` (or `http://localhost/mobile`)
* **Local Ollama Daemon (Optional GPU):** `http://localhost:11434`

---

## 3. Step-by-Step Demonstration Procedure

### Step 1: Open the Industrial Digital Twin
1. Open your browser and navigate to `http://localhost:80`.
2. Upon landing, note that the platform defaults directly to the **Digital Twin** tab.
3. Observe the real-time **10Hz telemetry HUD** streaming bearing temperature ($42.5^\circ\text{C}$), spindle speed ($10,000\text{ RPM}$), vibration ($1.12\text{ mm/s}$), and coolant pressure ($5.8\text{ bar}$).
4. Notice the interactive 3D spindle assembly rendering dynamic thermal heatmaps.

### Step 2: Open the Mobile Operator Gateway
1. Open a second browser window (or access from your mobile phone on the same Wi-Fi network) at `http://localhost:3000`.
2. Notice the dedicated industrial operator interface with real-time slider controls and override toggles.

### Step 3: Inject an Industrial Fault via Mobile Gateway
1. On the Mobile Gateway, adjust the sliders:
   * **Spindle Speed:** Increase to **`16,500 RPM`** (Excessive cutting velocity)
   * **Coolant Pressure:** Throttle down to **`1.8 bar`** (Lubrication starvation)
   * **Cutting Feed Rate:** Push to **`2,800 mm/min`** (Heavy roughing load)
2. Tap **"Apply Parameter Overrides"**.
3. Watch the desktop dashboard immediately update:
   * Spindle casing temperature surges from $42^\circ\text{C} \to 78.4^\circ\text{C}$.
   * Lubrication film ratio $\Lambda$ collapses below $0.8$ (boundary friction).
   * Vibration velocity RMS spikes from $1.1\text{ mm/s} \to 4.82\text{ mm/s}$.

### Step 4: Statistical Anomaly Trigger
1. Observe the **Evidence Layer** trigger:
   * The **CUSUM detector** flags a $+3.8\sigma$ thermal shift.
   * The **Isolation Forest** outputs an outlier contamination score of $0.88$.
2. The HUD displays an alert: `ANOMALY DETECTED: SPINDLE BEARING THERMAL EXPANSION`.
3. An active incident case (`INC-2026-M04`) opens automatically.

### Step 5: Multi-Agent Diagnostic Fan-Out
1. Click **"Investigate Incident"** (or observe automated dispatch).
2. Watch the multi-agent graph execute across the 4 phases:
   * **7 Domain Specialists** concurrently analyze thermal gradients, FFT vibration harmonics, lubrication shear, and electrical power.
   * **Causal Root Cause Engine** prioritizes *Lubrication Starvation & Bearing Spalling* as the primary hypothesis ($P = 0.92$).

### Step 6: Counterfactual Digital Twin Replay
1. Navigate to the **Verification Replay** view.
2. Watch the simulator rewind time to $T - 60\text{s}$ before the temperature spike.
3. The engine simulates the counterfactual intervention ($do(P_{cool} = 5.8\text{ bar})$).
4. Observe the green counterfactual curve: temperature and vibration return to baseline nominal levels, confirming the causal hypothesis with **$\Delta = 0.91$ (VERIFIED)**.

### Step 7: Predictive RUL & What-If Trade-Offs
1. Review the **Prediction Engine** card:
   * XGBoost estimates **Remaining Useful Life: 3.4 Hours**.
   * Run-to-failure risks a $\$48,500$ spindle rebuild.
   * An operational derate to $60\%$ extends RUL by $+18.6\text{ hours}$.

### Step 8: Inspect the 21-Section ReportLab PDF Report
1. Click **"Download Technical Report (PDF)"**.
2. Open the downloaded PDF (~230KB) and inspect:
   * Executive Scorecard and financial risk exposure.
   * 10Hz telemetry time-series charts.
   * Prescriptive maintenance procedure and replacement BOM parts.
   * OSHA Lock-Out / Tag-Out (LOTO) energy isolation checklist.

### Step 9: Executive Email & Twilio Voice Escalation
1. If configured with `.env` credentials:
   * An **Executive Action Email** arrives in your inbox containing the 5-point action briefing and the attached 21-section PDF report.
   * An **automated Twilio phone call** rings your phone, audibly speaking:
     > *"Hello Prajwal. Alligent speaking, this machine is facing an abnormal bearing condition, please look after it."*

### Step 10: Human Authorization & System Reset
1. Review the Maintenance Work Order. Click **"Authorize Maintenance Derate"**.
2. Tap **"Reset All Overrides"** on the Mobile Gateway to restore the twin to nominal closed-loop state.
