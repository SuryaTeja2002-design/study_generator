# tools/allocate_time.py
from typing import List, Dict

def allocate_time(subjects: List[Dict], days_left: int, hours_per_day: float) -> Dict:
    """
    Allocate hours across days using subject weights until each subject's required_hours is met
    or we run out of available time.
    """
    total_available = round(days_left * hours_per_day, 1)
    remaining = {s["name"]: float(s["required_hours"]) for s in subjects}
    weights   = {s["name"]: float(s["weight"]) for s in subjects}

    timetable = []
    for day in range(1, days_left + 1):
        day_hours = hours_per_day
        slots = []
        # proportional fill respecting remaining caps
        while day_hours > 0.0001:
            # find subjects that still need time
            active = [n for n, rem in remaining.items() if rem > 0.0001]
            if not active:
                break
            # distribute in one pass
            total_w = sum(weights[n] for n in active) or 1.0
            allocated_any = False
            for n in active:
                share = (weights[n] / total_w) * day_hours
                give = min(share, remaining[n])
                if give > 0.0001:
                    slots.append({"subject": n, "hours": round(give, 1)})
                    remaining[n] -= give
                    allocated_any = True
            if not allocated_any:
                break
            # recompute remaining day hours
            used = sum(s["hours"] for s in slots)
            day_hours = max(0.0, round(hours_per_day - used, 1))
            if day_hours <= 0.0:
                break

        timetable.append({"day": day, "blocks": slots})

    per_subject_allocation = {
        n: round(s["required_hours"] - remaining[n], 1) for s in subjects for n2 in [s["name"]] if (n := n2) is not None
    }

    return {
        "timetable": timetable,
        "per_subject_allocation": per_subject_allocation,
        "total_available_hours": total_available,
    }
