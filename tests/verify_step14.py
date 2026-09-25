"""verify_step14.py -- Verification for Step 14 (Historical Dataset)."""

import sys
import os
from collections import Counter
from scripts.generate_history import generate_dataset

def test_dataset_generation():
    # 1. Generate dataset
    output_file = "data/test_history.json"
    cases = generate_dataset(num_cases=300, output_path=output_file)
    
    assert len(cases) == 300, f"Expected 300 cases, got {len(cases)}"
    
    # 2. Check class balance
    counts = Counter(c["scenario_id"] for c in cases)
    # With 300 cases and 6 scenarios, we expect ~50 of each. Assert each has at least 20.
    for scenario in ["S1", "S2", "S3", "S4", "S5", "NOISE_ONLY"]:
        assert counts[scenario] >= 20, f"Class imbalance: {scenario} only has {counts[scenario]} cases"
        
    # 3. Spot-check incident metrics against labels
    for c in cases:
        if c["scenario_id"] == "S1":
            # High speed -> High heat/vibration
            assert c["peak_temperature"] > 41.0, f"S1 expected high temp, got {c['peak_temperature']}"
            assert c["peak_vibration"] > 5.0, f"S1 expected high vibration, got {c['peak_vibration']}"
        elif c["scenario_id"] == "S5":
            # Bad material batch -> defect rate spikes
            assert c["peak_defect_rate"] > 0.05, f"S5 expected high defect rate, got {c['peak_defect_rate']}"
            
    # Cleanup
    if os.path.exists(output_file):
        os.remove(output_file)

def main():
    print("\n=== STEP 14 VERIFICATION: Historical Dataset ===")
    
    passes = 0
    total = 1
    
    try:
        test_dataset_generation()
        print("  [PASS] Dataset generated, classes balanced, and physics signatures match labels")
        passes += 1
    except Exception as e:
        print(f"  [FAIL] Dataset verification: {e}")
        
    print("\n============================================================")
    print(f"RESULTS: {passes}/{total} passed, {total - passes} failed")
    if passes == total:
        print("[OK] ALL CHECKS PASSED -- Step 14 complete.")
        sys.exit(0)
    else:
        print("!! SOME CHECKS FAILED -- see above for details.")
        sys.exit(1)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
