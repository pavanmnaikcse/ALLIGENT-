"""generate_history.py -- Step 14 Historical Synthetic Dataset Generation."""

import json
import random
import uuid
import os
from collections import Counter
from datetime import datetime, timezone, timedelta

from simulator.factory_sim import FactoryTwin
from simulator.scenarios import SCENARIOS, apply_scenario

def generate_dataset(num_cases=200, output_path="data/history.json"):
    cases = []
    
    # We want to uniformly sample from S1-S5 and NOISE_ONLY
    scenario_keys = list(SCENARIOS.keys())
    
    print(f"Generating {num_cases} historical cases...")
    for i in range(num_cases):
        scenario_id = random.choice(scenario_keys)
        
        twin = FactoryTwin(snapshot_interval=9999)
        # Run baseline
        for _ in range(30):
            twin.tick()
            
        # Apply anomaly
        apply_scenario(twin.params, scenario_id)
        
        # Run anomalous and track peaks
        peak_temp = 0.0
        peak_vib = 0.0
        peak_defect = 0.0
        
        for _ in range(50):
            state = twin.tick()
            m = state["machines"].get("M-04", {})
            l = state["lines"].get("L-03", {})
            
            peak_temp = max(peak_temp, m.get("temperature_c", 0.0))
            peak_vib = max(peak_vib, m.get("vibration_mm_s", 0.0))
            peak_defect = max(peak_defect, l.get("defect_rate", 0.0))
            
        # True Hypothesis map based on Section 7.2 descriptions
        hypothesis_map = {
            "S1": "H1", # Speed out of range
            "S2": "H5", # Sensor drift / spoofed
            "S3": "H3", # Coolant flow drops
            "S4": "H2", # Bearing wear
            "S5": "H4", # Bad material batch
            "NOISE_ONLY": "NONE"
        }
            
        case_id = f"HIST-{uuid.uuid4().hex[:8].upper()}"
        hist_case = {
            "case_id": case_id,
            "machine_id": "M-04",
            "scenario_id": scenario_id,
            "true_root_cause": hypothesis_map.get(scenario_id, "UNKNOWN"),
            "peak_temperature": peak_temp,
            "peak_vibration": peak_vib,
            "peak_defect_rate": peak_defect,
            "resolution_notes": f"Historical resolution for {scenario_id} ({hypothesis_map.get(scenario_id)}). Fixed by operator.",
            "timestamp": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))).isoformat()
        }
        cases.append(hist_case)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=2)
        
    print(f"Dataset generated at {output_path}")
    
    # Class balance check
    counts = Counter(c["scenario_id"] for c in cases)
    print("Class Balance:")
    for k, v in counts.items():
        print(f"  {k}: {v} ({(v/num_cases)*100:.1f}%)")
        
    return cases

if __name__ == "__main__":
    generate_dataset()
