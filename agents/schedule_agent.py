# agents/schedule_agent.py
from typing import List, Dict, Any
from typing_extensions import TypedDict, NotRequired
from langgraph.graph import StateGraph, START, END

from tools.priority_score import build_priorities
from tools.allocate_time import allocate_time
from tools.tips_writer import write_tips
from tools.rag_store import search as rag_search  # RAG search

# ----- State schema -----
class ScheduleState(TypedDict, total=False):
    # inputs
    days_left: int
    hours_per_day: float
    subjects: List[Dict[str, Any]]  # {name, difficulty (1-5), target_hours?}

    # derived
    subjects_enriched: NotRequired[List[Dict[str, Any]]]  # +score, weight, required_hours
    total_required_hours: NotRequired[float]
    total_available_hours: NotRequired[float]
    timetable: NotRequired[List[Dict[str, Any]]]          # per-day plan
    per_subject_allocation: NotRequired[Dict[str, float]]
    overbooked: NotRequired[bool]
    hours_gap: NotRequired[float]

    # RAG
    contexts: NotRequired[Dict[str, List[Dict[str, str]]]]  # subject -> [{id,path,text}]

    # LLM output
    tips: NotRequired[Dict[str, Any]]

# ----- Nodes -----
def score_node(state: ScheduleState) -> ScheduleState:
    out = build_priorities(state["subjects"], state["days_left"])
    return {
        "subjects_enriched": out["subjects"],
        "total_required_hours": out["total_required_hours"],
    }

def allocate_node(state: ScheduleState) -> ScheduleState:
    alloc = allocate_time(
        subjects=state["subjects_enriched"],
        days_left=state["days_left"],
        hours_per_day=state["hours_per_day"],
    )
    return {
        "timetable": alloc["timetable"],
        "per_subject_allocation": alloc["per_subject_allocation"],
        "total_available_hours": alloc["total_available_hours"],
        "overbooked": alloc["total_available_hours"] < state["total_required_hours"],
        "hours_gap": round(state["total_required_hours"] - alloc["total_available_hours"], 1),
    }

def retrieve_node(state: ScheduleState) -> ScheduleState:
    """
    For each subject, run a simple RAG query. If no index is built yet, hits=[]
    and contexts will just be empty (tips will still work, just without citations).
    """
    contexts: Dict[str, List[Dict[str, str]]] = {}
    for s in state.get("subjects_enriched", []):
        name = s["name"]
        q = f"{name} key formulas concepts summaries"
        hits = rag_search(q, k=4) or []
        contexts[name] = [{"id": h["id"], "path": h["path"], "text": h["text"]} for h in hits]
    return {"contexts": contexts}

def tips_node(state: ScheduleState) -> ScheduleState:
    t = write_tips(
        subjects=state["subjects_enriched"],
        timetable=state["timetable"],
        overbooked=state["overbooked"],
        hours_gap=state["hours_gap"],
        contexts=state.get("contexts", {}),  # pass RAG contexts
    )
    return {"tips": t}

# ----- Graph -----
def build_schedule_agent():
    graph = StateGraph(ScheduleState)

    graph.add_node("score", score_node)
    graph.add_node("allocate", allocate_node)
    graph.add_node("retrieve", retrieve_node)  # NEW
    graph.add_node("tips", tips_node)

    graph.add_edge(START, "score")
    graph.add_edge("score", "allocate")
    graph.add_edge("allocate", "retrieve")     # allocate → retrieve
    graph.add_edge("retrieve", "tips")         # retrieve → tips
    graph.add_edge("tips", END)

    return graph.compile()
