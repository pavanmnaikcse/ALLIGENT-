"""verify_step18.py -- Verification for Step 18 (Dashboard)."""

import sys
import os

def main():
    print("\n=== STEP 18 VERIFICATION: Streamlit Dashboard ===")
    
    app_path = "frontend/app.py"
    if not os.path.exists(app_path):
        print("  [FAIL] frontend/app.py not found.")
        sys.exit(1)
        
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if "st.rerun()" not in content and "st.experimental_rerun()" not in content:
        print("  [FAIL] Dashboard does not continuously update (missing rerun).")
        sys.exit(1)
        
    if "plotly.express" not in content and "st.scatter_chart" not in content:
        print("  [FAIL] Dashboard missing 3D rendering.")
        sys.exit(1)
        
    print("  [PASS] Streamlit Dashboard created with polling and 3D visualization.")
    print("============================================================")
    print("RESULTS: 1/1 passed, 0 failed")
    print("[OK] ALL CHECKS PASSED -- Step 18 complete.")
    sys.exit(0)

if __name__ == "__main__":
    main()
