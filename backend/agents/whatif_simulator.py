"""whatif_simulator.py -- Step 10 What-If Prediction Engine.

Implements R6 (Physics-grounded projections): The Recommendation agent
must not hallucinate KPI impacts. It runs a what-if simulation to generate
predicted metrics (temperature, vibration) for the proposed actions.
"""

from typing import Any

from simulator.factory_sim import FactoryTwin

def run_whatif_prediction(
    twin: FactoryTwin,
    machine_id: str,
    parameter_changes: dict[str, float],
    sim_ticks: int = 100,
) -> dict[str, Any]:
    """Run a forward simulation with the proposed changes and measure the impact."""
    
    # Take a temporary snapshot
    snap_id = twin.take_snapshot("temp_whatif")
    
    # Apply proposed changes
    for path, value in parameter_changes.items():
        try:
            twin.params.set(path, value)
        except KeyError:
            pass
            
    # Measure metrics over the simulation window
    peak_temp = 0.0
    peak_vib = 0.0
    defect_sum = 0.0
    
    for _ in range(sim_ticks):
        state = twin.tick()
        machine_state = state["machines"].get(machine_id, {})
        
        peak_temp = max(peak_temp, machine_state.get("temperature_c", 0.0))
        peak_vib = max(peak_vib, machine_state.get("vibration_mm_s", 0.0))
        
        line_state = state["lines"].get("L1", {})  # Assume L1 for now
        defect_sum += line_state.get("defect_rate", 0.0)
        
    avg_defect_rate = defect_sum / sim_ticks if sim_ticks > 0 else 0.0
    
    # Restore original state
    twin.restore_from_snapshot(snap_id)
    
    return {
        "predicted_peak_temperature": peak_temp,
        "predicted_peak_vibration": peak_vib,
        "predicted_defect_rate": avg_defect_rate,
        # Rough heuristics for power/co2
        "predicted_kwh_per_unit": 2.5 + (peak_vib * 0.1),
        "predicted_co2_per_unit": 1.2 + (peak_temp * 0.01),
    }
