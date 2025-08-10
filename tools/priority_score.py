# tools/priority_score.py
from typing import List, Dict

def build_priorities(subjects: List[Dict], days_left: int) -> Dict:
    """
    subjects: [{"name": "Math", "difficulty": 1..5, "target_hours": optional}, ...]
    Estimate required_hours (target_hours or difficulty*4),
    compute priority score (difficulty * urgency), and normalized weight.
    """
    prepared = []
    for s in subjects:
        name = (s.get("name") or "").strip() or "Untitled"
        diff = int(s.get("difficulty", 3))
        diff = max(1, min(5, diff))
        target = s.get("target_hours")
        req = float(target) if target not in (None, "",) else diff * 4.0

        # urgency: fewer days => higher (caps at ~2x around 0 days)
        urgency = 1.0 + max(0.0, (14.0 - float(days_left))) / 14.0
        score = diff * urgency
        prepared.append({
            "name": name,
            "difficulty": diff,
            "required_hours": round(req, 1),
            "score": round(score, 3),
        })

    total_score = sum(x["score"] for x in prepared) or 1.0
    for x in prepared:
        x["weight"] = round(x["score"] / total_score, 4)

    total_req = round(sum(x["required_hours"] for x in prepared), 1)
    return {"subjects": prepared, "total_required_hours": total_req}
