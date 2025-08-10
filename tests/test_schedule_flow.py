# tests/test_schedule_flow.py
import math
import types

# ---- Unit tests for deterministic tools ----
from tools.priority_score import build_priorities
from tools.allocate_time import allocate_time

def almost_equal(a, b, eps=1e-6):
    return abs(a - b) <= eps

def test_build_priorities_basic():
    subjects = [
        {"name": "Math", "difficulty": 5},          # -> required_hours = 5*4 = 20
        {"name": "History", "difficulty": 2},       # -> required_hours = 2*4 = 8
        {"name": "Chem", "difficulty": 3, "target_hours": 6.5},  # explicit
    ]
    out = build_priorities(subjects, days_left=7)
    # required hours computed
    req = {s["name"]: s["required_hours"] for s in out["subjects"]}
    assert almost_equal(req["Math"], 20.0)
    assert almost_equal(req["History"], 8.0)
    assert almost_equal(req["Chem"], 6.5)

    # weights sum to ~1
    wsum = sum(s["weight"] for s in out["subjects"])
    assert almost_equal(wsum, 1.0, 1e-6)

    # total_required_hours accurate
    assert almost_equal(out["total_required_hours"], 20.0 + 8.0 + 6.5)

def test_allocate_time_caps_and_totals():
    subjects = [
        {"name": "Math", "difficulty": 5, "required_hours": 12.0, "weight": 0.6},
        {"name": "History", "difficulty": 2, "required_hours": 8.0,  "weight": 0.4},
    ]
    out = allocate_time(subjects, days_left=5, hours_per_day=4.0)

    # total available = 20h
    assert almost_equal(out["total_available_hours"], 20.0)

    # per-subject allocation never exceeds required
    per = out["per_subject_allocation"]
    assert per["Math"] <= 12.0 + 1e-6
    assert per["History"] <= 8.0 + 1e-6

    # if total required (20) equals available (20), we should fully meet or nearly meet both
    assert almost_equal(per["Math"] + per["History"], 20.0, 1e-6)

    # timetable length equals days_left; no negative hours
    assert len(out["timetable"]) == 5
    for day in out["timetable"]:
        for blk in day["blocks"]:
            assert blk["hours"] >= 0

# ---- End-to-end agent test with Gemini mocked ----
def test_end_to_end_schedule_agent(monkeypatch):
    # Patch the agent's write_tips so no real API call is made
    import agents.schedule_agent as sa

    def fake_write_tips(*, subjects, timetable, overbooked, hours_gap):
        return {
            "study_principles": ["Pomodoro", "Active recall"],
            "focus_order": [s["name"] for s in subjects],
            "breaks": {"work": 50, "break": 10},
            "daily_checklist": ["Plan tomorrow’s first block", "Review flashcards 10 min"],
            **(
                {"if_overbooked": {"strategy": "extend_days", "actions": ["Add 2 days", "Cut lowest-priority topic"]}}
                if overbooked else {}
            ),
        }

    # schedule_agent imports write_tips at module scope; patch that symbol
    monkeypatch.setattr(sa, "write_tips", fake_write_tips, raising=True)

    agent = sa.build_schedule_agent()
    state = {
        "days_left": 3,
        "hours_per_day": 3.0,
        "subjects": [
            {"name": "Math", "difficulty": 5},           # ~20h required by default
            {"name": "History", "difficulty": 2},        # ~8h
        ],
    }

    result = agent.invoke(state)

    # Graph should produce keys from all nodes
    assert "timetable" in result
    assert "subjects_enriched" in result or "subjects" in result  # compiled graph may return merged state
    assert "tips" in result

    # Check overbooked condition is detected (required ~28h vs available 9h)
    assert result.get("overbooked", True) is True
    assert result.get("hours_gap", 0) > 0

    # Tips structure present from fake LLM
    tips = result["tips"]
    assert "study_principles" in tips
    assert "daily_checklist" in tips
    if "if_overbooked" in tips:
        assert "actions" in tips["if_overbooked"]
