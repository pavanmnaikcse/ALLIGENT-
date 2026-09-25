# Changelog

All notable changes to the **ALLIGENT** platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0-rc1] - 2026-09-25

### Added
- **Physics Digital Twin:** 10Hz Runge-Kutta 4th order ODE simulator modeling spindle drive kinematics, Stribeck friction, two-node thermal dissipation ($Q_{gen} - Q_{diss}$), and regenerative cutting chatter.
- **Dynamic Parameter Modulation:** Real-time state override persistence (`twin._manual_overrides`) accessible via `POST /parameters/batch` and the Mobile Gateway.
- **Evidence Layer:** Continuous statistical change-point detection via Two-Sided CUSUM ($S_n^+, S_n^-$) and multivariate Scikit-Learn `IsolationForest` scoring.
- **11-Agent Diagnostic Collective:** Asynchronous Directed Acyclic Graph (DAG) coordinating 7 domain specialists (Acoustic, Thermal, Lubrication, Tool Wear, Electrical, Quality, Structural) and 4 reasoning agents.
- **Causal Root Cause Synthesizer:** Multi-hypothesis Bayesian scoring combining empirical likelihood, temporal precedence, and physical causal constraints.
- **Counterfactual Replay Engine:** Virtual Pearlian causal intervention ($do(X = x)$) featuring state snapshot capture, temporal rewind ($T - 60\text{s}$), and delta convergence quantification.
- **What-If Simulation:** Multi-scenario forward projection comparing Run-to-Failure, Operational Derate, and Immediate Controlled Interruption with Monte Carlo uncertainty.
- **Predictive Machine Learning:** Serialized XGBoost Regressor (`data/xgboost_rul_model.pkl`) predicting Remaining Useful Life (RUL) with $R^2 = 0.942$ and $MAE = 3.12\text{ hours}$.
- **Prescriptive Maintenance Work Orders:** Automated generation of component isolation steps, required tooling, and OSHA Lock-Out / Tag-Out (LOTO) energy isolation procedures.
- **21-Section ReportLab PDF Generator:** Automated compilation of publication-grade engineering investigation reports (~230KB) with tables, KPI scorecards, and sign-off blocks.
- **Executive Email Alerting:** High-urgency action-oriented notification dispatch via Resend REST API with the 21-section PDF report attached.
- **Twilio Emergency Voice Escalation:** Automated synthesized voice calls for Critical incidents speaking dynamic briefs to on-call plant supervisors.
- **Industrial Web Console & 3D Twin:** React SPA featuring dark industrial glassmorphism, interactive Three.js spindle visualizer with thermal heatmaps, and sub-millisecond telemetry charts.
- **Mobile Operator Gateway:** Dedicated Next.js/React operator interface (`/mobile`) with real-time sliders and override toggles.
- **Documentation Suite:** 21 specialized markdown specifications under `docs/` covering architecture, mathematics, APIs, and release verification.

### Security
- Decoupled all secret keys (Twilio, Resend, database credentials) from source code into environment variables (`.env`).
- Sanitized `backend/email_alert.py` fallback tokens.
- Enforced strict `.gitignore` filters across all secret and environment configurations.
- Purged accidental 101MB unreferenced temporary development file.
