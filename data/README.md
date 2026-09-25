# ALLIGENT Dataset & Model Registry

This directory contains the machine learning training datasets, validation archives, and the serialized Remaining Useful Life (RUL) regression model utilized by the ALLIGENT platform.

---

## 1. Directory Inventory

| File Name | File Type | Approximate Size | Description |
| :--- | :--- | :--- | :--- |
| `xgboost_rul_model.pkl` | Binary Pickle (`xgboost.XGBRegressor`) | ~392 KB | Serialized Gradient Boosted Decision Tree model trained to predict machine Remaining Useful Life (RUL) in operating hours. |
| `comprehensive_machine_dataset.csv` | Comma-Separated Values | ~554 KB | Comprehensive dataset comprising 10,000+ run-to-failure cycles across multi-axis CNC spindles, recording 14 features. |
| `machine_failure_dataset.csv` | Comma-Separated Values | ~9 KB | Curated validation benchmark dataset containing labeled failure modes (Bearing Wear, Tool Chipping, Motor Overheat). |
| `history.json` | JSON Document | ~20 KB | Historical calibration baseline run logs used to initialize steady-state parameters in the digital twin. |

---

## 2. Dataset Schema (`comprehensive_machine_dataset.csv`)

Every row in the training dataset records operating features sampled from continuous machining cycles:

* `spindle_speed_mean`: Average rotational velocity (RPM)
* `spindle_power_mean`: Active electrical motor power (kW)
* `bearing_temp_mean`: Average front spindle bearing temperature (°C)
* `temp_gradient`: Rate of thermal rise (°C/min)
* `vibration_rms`: Root Mean Square vibration velocity (mm/s)
* `vibration_crest_factor`: Peak-to-RMS vibration ratio
* `cutting_force_mean`: Resultant machining force (N)
* `feed_rate_mean`: Axis travel feed velocity (mm/min)
* `lubrication_ratio`: Specific oil film thickness ($\Lambda$)
* `coolant_pressure`: Coolant fluid delivery pressure (bar)
* `operating_hours_total`: Accumulated operating hours since last overhaul
* `tool_flank_wear`: Optical/measured flank wear land width ($VB$ in $\mu\text{m}$)
* `cusum_drift_score`: Statistical cumulative sum deviation
* `isolation_anomaly_score`: Multivariate isolation forest outlier score
* `rul_hours`: **Target Variable** — Actual hours remaining until physical mechanical failure

---

## 3. Loading the Predictive Model

```python
import pickle
import numpy as np

# Load the trained XGBoost model
with open("data/xgboost_rul_model.pkl", "rb") as f:
    model = pickle.load(f)

# Sample feature vector (14 features)
sample_vector = np.array([[
    14500.0,  # spindle_speed_mean (RPM)
    8.5,      # spindle_power_mean (kW)
    72.4,     # bearing_temp_mean (°C)
    1.8,      # temp_gradient (°C/min)
    4.1,      # vibration_rms (mm/s)
    3.2,      # vibration_crest_factor
    520.0,    # cutting_force_mean (N)
    1800.0,   # feed_rate_mean (mm/min)
    0.95,     # lubrication_ratio (Lambda)
    2.1,      # coolant_pressure (bar)
    1840.0,   # operating_hours_total
    180.0,    # tool_flank_wear (micrometers)
    3.8,      # cusum_drift_score
    0.78      # isolation_anomaly_score
]])

# Predict Remaining Useful Life in operating hours
predicted_rul = model.predict(sample_vector)[0]
print(f"Predicted Remaining Useful Life: {predicted_rul:.1f} hours")
```
