# ALLIGENT System Boundaries, Assumptions & Known Limitations

**Product:** ALLIGENT — AI-Powered Industrial Investigation & Decision Support  
**Document:** Operational Constraints & Engineering Boundaries  
**Version:** 1.0.0  

---

## 1. Physical Simulation Assumptions & Approximations

While the ALLIGENT digital twin utilizes rigorous differential equations, the simulation includes deliberate engineering simplifications:

1. **Lumped Thermal Network:**
   * *Assumption:* The thermal model treats the front spindle bearing housing as a lumped capacitance node with uniform surface temperature.
   * *Boundary:* In physical machines with high-pressure internal cooling jackets, steep localized thermal gradients ($>15^\circ\text{C}$ across $20\text{mm}$) can occur that are not fully captured by a single-node ODE.
2. **Fluid Dynamics Simplification:**
   * *Assumption:* Coolant heat transfer assumes incompressible single-phase fluid flow.
   * *Boundary:* Under extreme localized cutting temperatures ($>120^\circ\text{C}$), localized film boiling and cavitation can occur, reducing coolant effectiveness below theoretical predictions.
3. **Modal Degrees of Freedom:**
   * *Assumption:* Vibration dynamics model 2-DOF radial/axial displacement.
   * *Boundary:* Complex tool-holder assemblies exhibit torsional-axial coupled chatter modes that require multi-body finite element (FEA) solvers to model fully.

---

## 2. Artificial Intelligence & Multi-Agent Constraints

1. **LLM Hallucination & Consistency:**
   * Large Language Models may generate plausible-sounding but physically improbable failure mechanisms when exposed to ambiguous sensor evidence.
   * *Mitigation:* ALLIGENT enforces strict **Pydantic v2 schema validation**, **Bayesian evidence thresholding**, and **Digital Twin Counterfactual Replay** before any diagnosis is escalated.
2. **Inference Latency on CPU Hardware:**
   * When running local Ollama (`llama3:latest`) on workstations lacking discrete NVIDIA CUDA GPUs, multi-agent fan-out latency increases from $\approx 2.1\text{s}$ to $12 - 25\text{s}$.
   * *Mitigation:* The system includes calibrated **deterministic engineering heuristics** that execute in $< 400\text{ms}$ when GPU hardware is unavailable.
3. **Out-of-Distribution (OOD) Operational Envelopes:**
   * The XGBoost RUL model is trained on standard milling cycles ($8,000 - 18,000\text{ RPM}$). Operating machines outside this validated envelope reduces RUL forecasting confidence.

---

## 3. Strict Industrial Safety Boundary

> [!CAUTION]
> **NO DIRECT PHYSICAL ACTUATION:**  
> ALLIGENT is strictly an **advisory decision-support platform**. The platform does NOT connect to PLC safety interlocks, high-voltage contactors, or emergency stop (E-Stop) relays.

* **Safety Compliance (ISO 13849 / IEC 61508):** Industrial safety regulations prohibit automated software systems from altering physical machinery without validated Category 4 / PLe hardware interlocks.
* **Mandatory Human-in-the-Loop:** All prescriptive maintenance work orders, operational speed derates, and parts orders require explicit physical or cryptographic sign-off by a certified plant engineer.

---

## 4. External Integration Constraints

1. **Procurement Data Disclaimer:**
   * Supplier catalogs, lead times, pricing, and distributor stock levels represent **seeded demonstration data (`DEMO PROCUREMENT DATA`)**. Live enterprise ERP integration requires configuring production SAP or Oracle connectors.
2. **Network Streaming & Jitter:**
   * High-frequency 10Hz WebSocket streaming across congested wireless networks may experience packet jitter. ALLIGENT prioritizes current machine state over lossless playback, dropping delayed frames to guarantee zero operator display lag.
