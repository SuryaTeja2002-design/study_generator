# tools/tips_writer.py
from typing import List, Dict, Optional
from utils.llm_client import gemini_json

def write_tips(
    subjects: List[Dict],
    timetable: List[Dict],
    overbooked: bool,
    hours_gap: float,
    contexts: Optional[Dict[str, List[Dict]]] = None,  # <-- new optional arg
) -> Dict:
    """
    contexts: {subject: [{id, path, text}, ...]} from the RAG retrieve step.
    Returns strict-JSON tips with optional citations + RAG suggestions.
    """
    contexts = contexts or {}
    # compact, cite-able context block
    ctx_lines = []
    for subj, chunks in contexts.items():
        for ch in chunks:
            ctx_lines.append(f"[{ch['id']}] ({ch['path']}) {ch['text'][:450]}")
    ctx_block = "\n".join(ctx_lines) if ctx_lines else "NO_CONTEXT"

    system = "You are a precise study coach. Always return strict JSON only."
    user = f"""
Subjects (name, difficulty, required_hours, weight):
{subjects}

Timetable (per day → blocks of subject+hours):
{timetable}

Overbooked: {overbooked}
Hours_gap: {hours_gap}

Context passages (use to ground advice; cite as [chunk_id]):
{ctx_block}

Return JSON exactly in this schema:
{{
  "study_principles": [string],
  "focus_order": [string],
  "breaks": {{"work": 50, "break": 10}},
  "daily_checklist": [string],
  "rag_suggestions": [string],
  "citations": [string],
  "if_overbooked": {{
     "strategy": "scope_cuts" | "extend_days" | "hybrid",
     "actions": [string]
  }}
}}
Include "if_overbooked" only when Overbooked is true.
If NO_CONTEXT, leave rag_suggestions empty and citations [].
"""
    return gemini_json(system, user)
