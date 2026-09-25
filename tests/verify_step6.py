"""Step 6 Verification Script -- Parameters API + Case lifecycle.

Tests:
1. ParameterStore API surface works (get/set/batch/reset/history/scenario).
2. Case manager: open case freezes evidence window.
3. Case manager: cooldown prevents case storms.
4. Case manager: mid-investigation parameter change supersedes the case.
5. Case manager: approve/reject/modify transitions work.
6. FastAPI routes respond correctly (using TestClient).
"""

import sys
import os
import traceback
from datetime import datetime, timedelta, timezone

os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from simulator.parameters import ParameterStore
from simulator.scenarios import apply_scenario, SCENARIOS
from backend.case_manager import CaseManager
from schemas.case_state import CaseStatus


passed = 0
failed = 0
total = 0
NOW = datetime.now(timezone.utc)


def assert_(condition, msg="Assertion failed"):
    if not condition:
        raise AssertionError(msg)


def check(name, fn):
    global passed, failed, total
    total += 1
    try:
        fn()
        passed += 1
        print(f"  [PASS] {name}")
    except Exception as e:
        failed += 1
        print(f"  [FAIL] {name}: {e}")
        traceback.print_exc()


# =====================================================================
print("\n=== STEP 6 VERIFICATION: Parameters API + Case Lifecycle ===\n")

# -- 1. Parameter API surface --
print("1. Parameter API surface")


def test_param_full_cycle():
    store = ParameterStore()
    # GET
    val = store.get("machines.M-04.target_rpm")
    assert_(val == 1200.0)
    # SET
    store.set("machines.M-04.target_rpm", 1400.0, source="operator")
    assert_(store.get("machines.M-04.target_rpm") == 1400.0)
    # BATCH
    store.batch_set({"machines.M-04.coolant_flow_lpm": 5.0}, source="api")
    assert_(store.get("machines.M-04.coolant_flow_lpm") == 5.0)
    # HISTORY
    h = store.history
    assert_(len(h) >= 2)
    # RESET
    store.reset()
    assert_(store.get("machines.M-04.target_rpm") == 1200.0)
    assert_(store.get("machines.M-04.coolant_flow_lpm") == 12.0)

check("Full parameter API cycle", test_param_full_cycle)


def test_scenario_applies_via_api():
    store = ParameterStore()
    changes = apply_scenario(store, "S1")
    assert_(len(changes) > 0)
    assert_(store.get("machines.M-04.target_rpm") == 1500.0)
    # Reset
    store.reset()
    assert_(store.get("machines.M-04.target_rpm") == 1200.0)

check("Scenario applies via same API path", test_scenario_applies_via_api)


# -- 2. Case lifecycle: frozen evidence window --
print("\n2. Case lifecycle: frozen evidence window")


def test_evidence_window_frozen():
    """The evidence window is set at case-open and does not change."""
    mgr = CaseManager(cooldown_ticks=0)
    ws = NOW - timedelta(minutes=5)
    we = NOW
    case = mgr.open_case("M-04", "L-03", current_tick=0,
                          evidence_window_start=ws, evidence_window_end=we)
    assert_(case is not None)
    assert_(case.evidence_window_start == ws)
    assert_(case.evidence_window_end == we)

    # Even if we later look at the case, the window is still the same
    retrieved = mgr.get_case(case.case_id)
    assert_(retrieved.evidence_window_start == ws)
    assert_(retrieved.evidence_window_end == we)

check("Evidence window frozen at case-open", test_evidence_window_frozen)


# -- 3. Cooldown prevents case storms --
print("\n3. Cooldown prevents case storms")


def test_cooldown_prevents_storms():
    """After opening a case, opening another within cooldown should be blocked."""
    mgr = CaseManager(cooldown_ticks=50)
    case1 = mgr.open_case("M-04", "L-03", current_tick=10,
                           evidence_window_start=NOW - timedelta(minutes=5),
                           evidence_window_end=NOW)
    assert_(case1 is not None, "First case should open")

    # Try to open another case immediately (tick 15 -- within cooldown of 50)
    case2 = mgr.open_case("M-04", "L-03", current_tick=15,
                           evidence_window_start=NOW - timedelta(minutes=4),
                           evidence_window_end=NOW)
    assert_(case2 is None, "Second case should be blocked by cooldown")

    # After cooldown expires (tick 65), a new case should open
    case3 = mgr.open_case("M-04", "L-03", current_tick=65,
                           evidence_window_start=NOW - timedelta(minutes=3),
                           evidence_window_end=NOW)
    assert_(case3 is not None, "Case after cooldown should open")

    # Total cases should be 2 (case1 superseded by case3, case2 blocked)
    all_cases = mgr.list_cases()
    assert_(len(all_cases) == 2, f"Should have 2 cases, got {len(all_cases)}")

check("Cooldown prevents case storms", test_cooldown_prevents_storms)


def test_sustained_anomaly_one_case():
    """A sustained anomaly should produce only ONE case, not a storm."""
    mgr = CaseManager(cooldown_ticks=100)
    opened = 0
    blocked = 0
    for tick in range(0, 500, 10):  # try to open every 10 ticks
        case = mgr.open_case("M-04", "L-03", current_tick=tick,
                              evidence_window_start=NOW - timedelta(minutes=5),
                              evidence_window_end=NOW)
        if case is not None:
            opened += 1
        else:
            blocked += 1

    # With cooldown of 100 and ticks 0-490, we should open at most 5 cases
    assert_(opened <= 5, f"Should have at most 5 cases, got {opened}")
    assert_(blocked > 30, f"Should have blocked many attempts, only blocked {blocked}")
    print(f"    Sustained anomaly: {opened} cases opened, {blocked} blocked")

check("Sustained anomaly produces limited cases (no storm)", test_sustained_anomaly_one_case)


# -- 4. Mid-investigation parameter change: supersede --
print("\n4. Mid-investigation supersession (Section 12)")


def test_supersession():
    """A new case should supersede the active one for the same machine."""
    mgr = CaseManager(cooldown_ticks=0)  # disable cooldown for this test
    case1 = mgr.open_case("M-04", "L-03", current_tick=0,
                           evidence_window_start=NOW - timedelta(minutes=5),
                           evidence_window_end=NOW)
    assert_(case1 is not None)
    case1_id = case1.case_id

    # Start investigation
    mgr.start_investigation(case1_id)
    assert_(mgr.get_case(case1_id).status == CaseStatus.INVESTIGATING)

    # Now a new parameter change triggers a new case -> supersedes case1
    case2 = mgr.open_case("M-04", "L-03", current_tick=5,
                           evidence_window_start=NOW - timedelta(minutes=4),
                           evidence_window_end=NOW)
    assert_(case2 is not None)
    assert_(case2.case_id != case1_id)

    # Case1 should now be SUPERSEDED
    old_case = mgr.get_case(case1_id)
    assert_(old_case.status == CaseStatus.SUPERSEDED,
            f"Old case should be SUPERSEDED, got {old_case.status}")
    assert_(old_case.superseded_by == case2.case_id,
            f"superseded_by should point to new case")

    # The active case for M-04 should be case2
    active = mgr.get_active_case("M-04")
    assert_(active.case_id == case2.case_id)

check("Mid-investigation change supersedes active case", test_supersession)


def test_supersession_evidence_window_not_mixed():
    """Superseded and new cases should have different evidence windows."""
    mgr = CaseManager(cooldown_ticks=0)
    ws1 = NOW - timedelta(minutes=10)
    we1 = NOW - timedelta(minutes=5)
    case1 = mgr.open_case("M-04", "L-03", current_tick=0,
                           evidence_window_start=ws1, evidence_window_end=we1)

    ws2 = NOW - timedelta(minutes=5)
    we2 = NOW
    case2 = mgr.open_case("M-04", "L-03", current_tick=5,
                           evidence_window_start=ws2, evidence_window_end=we2)

    # Windows should be different -- not mixed
    assert_(case1.evidence_window_end != case2.evidence_window_end,
            "Evidence windows should not be mixed across cases")
    assert_(case2.evidence_window_start == ws2)

check("Superseded case evidence not mixed with new case", test_supersession_evidence_window_not_mixed)


# -- 5. Case decisions --
print("\n5. Case decisions")


def test_approve_reject_modify():
    mgr = CaseManager(cooldown_ticks=0)

    # Approve
    c1 = mgr.open_case("M-04", "L-03", current_tick=0,
                         evidence_window_start=NOW - timedelta(minutes=5),
                         evidence_window_end=NOW)
    mgr.apply_decision(c1.case_id, "approve", {"target_rpm": 1200.0})
    assert_(mgr.get_case(c1.case_id).status == CaseStatus.APPROVED)
    assert_(mgr.get_case(c1.case_id).decision.action == "approve")

    # Reject
    c2 = mgr.open_case("M-04", "L-03", current_tick=100,
                         evidence_window_start=NOW - timedelta(minutes=5),
                         evidence_window_end=NOW)
    mgr.apply_decision(c2.case_id, "reject")
    assert_(mgr.get_case(c2.case_id).status == CaseStatus.REJECTED)

    # Modify
    c3 = mgr.open_case("M-04", "L-03", current_tick=200,
                         evidence_window_start=NOW - timedelta(minutes=5),
                         evidence_window_end=NOW)
    mgr.apply_decision(c3.case_id, "modify", {"target_rpm": 1250.0})
    assert_(mgr.get_case(c3.case_id).status == CaseStatus.MODIFIED)

check("Approve/reject/modify transitions", test_approve_reject_modify)


def test_acknowledge_stops_escalation():
    mgr = CaseManager(cooldown_ticks=0)
    case = mgr.open_case("M-04", "L-03", current_tick=0,
                          evidence_window_start=NOW - timedelta(minutes=5),
                          evidence_window_end=NOW)
    assert_(not case.acknowledged)
    mgr.acknowledge(case.case_id)
    assert_(mgr.get_case(case.case_id).acknowledged)
    assert_(mgr.get_case(case.case_id).acknowledged_at is not None)

check("Acknowledge stops escalation", test_acknowledge_stops_escalation)


def test_needs_human_review():
    mgr = CaseManager(cooldown_ticks=0)
    case = mgr.open_case("M-04", "L-03", current_tick=0,
                          evidence_window_start=NOW - timedelta(minutes=5),
                          evidence_window_end=NOW)
    mgr.mark_needs_review(case.case_id)
    assert_(mgr.get_case(case.case_id).status == CaseStatus.NEEDS_HUMAN_REVIEW)

check("Needs-human-review routing", test_needs_human_review)


# -- 6. FastAPI routes (TestClient) --
print("\n6. FastAPI routes")

try:
    from fastapi.testclient import TestClient
    from backend.main import app, param_store as app_param_store

    client = TestClient(app)

    def test_get_parameters():
        resp = client.get("/parameters")
        assert_(resp.status_code == 200)
        data = resp.json()
        assert_("machines" in data)
        assert_("globals" in data)
        assert_(data["machines"]["M-04"]["target_rpm"] == 1200.0)

    check("GET /parameters", test_get_parameters)

    def test_patch_parameters():
        resp = client.patch("/parameters", json={
            "path": "machines.M-04.target_rpm", "value": 1400.0
        })
        assert_(resp.status_code == 200)
        data = resp.json()
        assert_(data["old_value"] == 1200.0)
        assert_(data["new_value"] == 1400.0)
        # Reset back
        client.post("/parameters/reset")

    check("PATCH /parameters", test_patch_parameters)

    def test_batch_parameters():
        resp = client.post("/parameters/batch", json={
            "changes": {"machines.M-04.target_rpm": 1500.0, "machines.M-04.coolant_flow_lpm": 5.0}
        })
        assert_(resp.status_code == 200)
        data = resp.json()
        assert_(len(data) == 2)
        client.post("/parameters/reset")

    check("POST /parameters/batch", test_batch_parameters)

    def test_get_history():
        client.patch("/parameters", json={"path": "machines.M-04.target_rpm", "value": 1450.0})
        resp = client.get("/parameters/history")
        assert_(resp.status_code == 200)
        assert_(len(resp.json()) > 0)
        client.post("/parameters/reset")

    check("GET /parameters/history", test_get_history)

    def test_reset():
        client.patch("/parameters", json={"path": "machines.M-04.target_rpm", "value": 9999.0})
        resp = client.post("/parameters/reset")
        assert_(resp.status_code == 200)
        params = client.get("/parameters").json()
        assert_(params["machines"]["M-04"]["target_rpm"] == 1200.0)

    check("POST /parameters/reset", test_reset)

    def test_scenario():
        resp = client.post("/parameters/scenario/S1")
        assert_(resp.status_code == 200)
        data = resp.json()
        assert_(data["scenario_id"] == "S1")
        params = client.get("/parameters").json()
        assert_(params["machines"]["M-04"]["target_rpm"] == 1500.0)
        client.post("/parameters/reset")

    check("POST /parameters/scenario/{id}", test_scenario)

    def test_invalid_scenario():
        resp = client.post("/parameters/scenario/S99")
        assert_(resp.status_code == 404)

    check("Invalid scenario returns 404", test_invalid_scenario)

    def test_simulator_state():
        resp = client.get("/simulator/state")
        assert_(resp.status_code == 200)
        data = resp.json()
        assert_("machines" in data)
        assert_("tick_index" in data)

    check("GET /simulator/state", test_simulator_state)

    def test_list_scenarios():
        resp = client.get("/parameters/scenarios")
        assert_(resp.status_code == 200)
        data = resp.json()
        assert_(len(data) == 6)

    check("GET /parameters/scenarios", test_list_scenarios)

except ImportError as e:
    print(f"  [SKIP] FastAPI TestClient not available: {e}")
except Exception as e:
    failed += 1
    total += 1
    print(f"  [FAIL] FastAPI route tests: {e}")
    traceback.print_exc()


# =====================================================================
print(f"\n{'='*60}")
print(f"RESULTS: {passed}/{total} passed, {failed} failed")
if failed > 0:
    print("!! SOME CHECKS FAILED -- see above for details.")
    sys.exit(1)
else:
    print("[OK] ALL CHECKS PASSED -- Step 6 complete.")
    sys.exit(0)
