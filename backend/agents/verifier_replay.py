"""verifier_replay.py -- Step 9 Counterfactual Replay Logic.

Implements R5 (Adversarial verification): The Verifier runs a physics check on the
digital twin, removing the suspected root cause and verifying the anomaly resolves.
"""

from schemas.agent_output import CounterfactualReplayResult
from simulator.factory_sim import FactoryTwin

# Map Hypothesis to the parameter that would resolve it if reverted
HYPOTHESIS_PARAM_MAP = {
    "H1": ("machines.{machine_id}.target_rpm", 1000.0),
    "H2": ("machines.{machine_id}.unauthorized_write_probability", 0.0),
    "H3": ("machines.{machine_id}.coolant_flow_lpm", 15.0),
    "H4": ("machines.{machine_id}.bearing_wear_rate", 0.0001),
    "H5": ("lines.{line_id}.active_material_batch_id", "BATCH-001"),
}

def run_counterfactual(
    twin: FactoryTwin,
    machine_id: str,
    line_id: str,
    hypothesis_id: str,
    replay_ticks: int = 50,
) -> CounterfactualReplayResult:
    """Run a counterfactual replay to test if resolving the hypothesis fixes the issue."""
    
    # 1. Take a temporary snapshot of the current (anomalous) state
    snap_id = twin.take_snapshot("temp_replay")
    
    # 2. Determine what parameter to revert
    if hypothesis_id not in HYPOTHESIS_PARAM_MAP:
        return CounterfactualReplayResult(
            hypothesis_id=hypothesis_id,
            snapshot_tick=twin.get_state()["tick_index"],
            parameter_reverted="none",
            reverted_value=0.0,
            original_value=0.0,
            replay_ticks=0,
            anomaly_resolved=False,
            explanation=f"Cannot replay unknown hypothesis {hypothesis_id}",
        )
        
    param_path_template, safe_val = HYPOTHESIS_PARAM_MAP[hypothesis_id]
    param_path = param_path_template.format(machine_id=machine_id, line_id=line_id)
    
    original_val = twin.params.get(param_path)
    
    # 3. Apply the fix
    twin.params.set(param_path, safe_val)
    
    # 4. Step forward
    peak_temp = 0.0
    peak_vib = 0.0
    
    for _ in range(replay_ticks):
        state = twin.tick()
        machine_state = state["machines"].get(machine_id, {})
        peak_temp = max(peak_temp, machine_state.get("temperature_c", 0.0))
        peak_vib = max(peak_vib, machine_state.get("vibration_mm_s", 0.0))
        
    # 5. Check if resolved (heuristic: did it stay safe during the replay window?)
    # E.g. temp < 85 is safe, vibration < 5.0 is safe
    resolved = peak_temp < 85.0 and peak_vib < 5.0
    
    result = CounterfactualReplayResult(
        hypothesis_id=hypothesis_id,
        snapshot_tick=twin.get_state()["tick_index"],
        parameter_reverted=param_path,
        reverted_value=float(safe_val) if isinstance(safe_val, (int, float)) else 0.0,
        original_value=float(original_val) if isinstance(original_val, (int, float)) else 0.0,
        replay_ticks=replay_ticks,
        anomaly_resolved=resolved,
        peak_temperature_replay=peak_temp,
        peak_vibration_replay=peak_vib,
        explanation=f"Reverting {param_path} to {safe_val} resulted in resolution={resolved}",
    )
    
    # 6. Restore the original state so we don't mess up the actual twin state
    twin.restore_from_snapshot(snap_id)
    
    return result
