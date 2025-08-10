# app.py
import os, json
import pandas as pd
import streamlit as st

from agents.schedule_agent import (
    build_schedule_agent,
    score_node, allocate_node, retrieve_node, tips_node,
)

# (optional import guard; works even if faiss not installed yet)
try:
    from tools.rag_store import build_ephemeral_index
except Exception:
    build_ephemeral_index = None

st.set_page_config(
    page_title="Study Schedule Generator (LangGraph + Gemini + RAG)",
    page_icon="📚",
    layout="wide",
)
st.title(" Study Schedule Generator")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Plan Settings")
    days_left = st.number_input("Days left", min_value=1, max_value=60, value=7)
    hours_per_day = st.slider("Available hours per day", 1.0, 12.0, 4.0, 0.5)
    explain = st.checkbox("Explain mode (show raw agent states)", value=False)
    st.caption("LangGraph orchestrates: scoring → allocation → retrieval (RAG) → tips.")

    st.divider()
    st.header("RAG (paste notes)")
    st.caption("Paste any study notes / formulas / summaries. Built in-memory for this session.")
    notes = st.text_area(
        "Notes to index:",
        height=160,
        placeholder="e.g.\nKinematics: v = u + at, s = ut + 1/2 a t^2 ...\nEssay: claim → evidence → reasoning ...",
    )
    if st.button(" Build RAG from pasted notes"):
        if not build_ephemeral_index:
            st.error("RAG builder unavailable (install faiss-cpu).")
        else:
            try:
                chunks, dim = build_ephemeral_index([notes] if notes.strip() else [])
                if chunks > 0:
                    st.success(f"Built ephemeral index: {chunks} chunks (dim={dim}).")
                else:
                    st.info("Cleared RAG (no notes).")
            except Exception as e:
                st.error(f"RAG build failed: {e}")

# ---------------- Subjects form ----------------
if "subjects" not in st.session_state:
    st.session_state.subjects = []

st.subheader("Add Subjects")
with st.form("add_subject", clear_on_submit=True):
    c1, c2, c3 = st.columns([2, 1, 1])
    name = c1.text_input("Subject", value="Math")
    difficulty = c2.slider("Difficulty (1=easy, 5=hard)", 1, 5, 3)
    target_hours = c3.number_input(
        "Target hours (optional)", min_value=0.0, step=0.5, value=0.0,
        help="Leave 0 to auto-estimate by difficulty."
    )
    submitted = st.form_submit_button("Add")
    if submitted and name:
        st.session_state.subjects.append({
            "name": name,
            "difficulty": difficulty,
            "target_hours": target_hours if target_hours > 0 else None
        })
        st.toast(f"Added: {name}")

if st.session_state.subjects:
    st.write("**Current Subjects:**")
    st.dataframe(pd.DataFrame(st.session_state.subjects), use_container_width=True)
else:
    st.info("Add a few subjects to begin.")

go = st.button(" Generate Study Plan", use_container_width=True)

# ---------------- Run agent steps ----------------
if go and st.session_state.subjects:
    _ = build_schedule_agent()  # compile once (we call node funcs directly)

    base_state = {
        "days_left": int(days_left),
        "hours_per_day": float(hours_per_day),
        "subjects": st.session_state.subjects
    }

    # 1) score/priorities
    s1 = {**base_state, **score_node(base_state)}

    # 2) allocate time
    s2 = {**s1, **allocate_node(s1)}

    # 3) retrieve (RAG) — searches the ephemeral index if you built it
    sR = {**s2, **retrieve_node(s2)}

    # 4) tips (Gemini)
    try:
        s3 = {**sR, **tips_node(sR)}
    except Exception as e:
        s3 = {**sR, "tips": {}}
        st.error("Gemini call failed (tips disabled). Check GOOGLE_API_KEY in your .env.")
        st.exception(e)

    # ---------------- Pretty render ----------------
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Required Hours", f"{s1['total_required_hours']:.1f}h")
    c2.metric("Total Available Hours", f"{s2['total_available_hours']:.1f}h")
    gap = s1['total_required_hours'] - s2['total_available_hours']
    c3.metric("Gap (req - avail)", f"{gap:+.1f}h")

    st.subheader("Subjects & Priorities")
    st.dataframe(pd.DataFrame(s1["subjects_enriched"]), use_container_width=True)

    st.subheader("Timetable")
    rows = []
    for d in s2["timetable"]:
        for b in d["blocks"]:
            rows.append({"Day": d["day"], "Subject": b["subject"], "Hours": b["hours"]})
    if rows:
        tt_df = pd.DataFrame(rows)
        st.dataframe(tt_df, use_container_width=True)
        st.bar_chart(tt_df.groupby("Subject")["Hours"].sum())
    else:
        st.warning("No time allocated yet—try increasing hours/day or days_left.")

    st.subheader("Study Tips & Checklist")
    tips = s3.get("tips", {}) or {}
    if tips:
        principles = tips.get("study_principles", [])
        focus_order = tips.get("focus_order", [])
        breaks = tips.get("breaks", {})
        checklist = tips.get("daily_checklist", [])
        over = tips.get("if_overbooked")
        cites = tips.get("citations", [])
        rag_sugs = tips.get("rag_suggestions", [])

        if principles:
            st.markdown("**Principles:** " + ", ".join(principles))
        if focus_order:
            st.markdown("**Daily Focus Order:** " + " → ".join(focus_order))
        if breaks:
            st.markdown(f"**Work/Break:** {breaks.get('work', 50)} / {breaks.get('break', 10)} minutes")
        if checklist:
            st.markdown("**Checklist:**")
            for item in checklist:
                st.write(f"• {item}")
        if over:
            st.warning(f"Overbooked — Strategy: **{over.get('strategy','')}**")
            for action in over.get("actions", []):
                st.write(f"• {action}")
        if rag_sugs:
            st.markdown("**RAG Suggestions (from your pasted notes):**")
            for x in rag_sugs:
                st.write(f"• {x}")
        if cites:
            st.markdown("**Sources:** " + ", ".join(cites))
    else:
        st.info("No tips returned.")

    # Downloads
    st.divider()
    final_report = {
        "inputs": base_state,
        "subjects_enriched": s1["subjects_enriched"],
        "timetable": s2["timetable"],
        "per_subject_allocation": s2["per_subject_allocation"],
        "overbooked": s2["overbooked"],
        "hours_gap": s2["hours_gap"],
        "contexts": sR.get("contexts", {}),
        "tips": tips
    }
    st.download_button(
        "Download JSON Plan",
        data=json.dumps(final_report, indent=2),
        file_name="study_plan.json",
        mime="application/json",
        use_container_width=True,
    )

    if explain:
        with st.expander("Raw States (for debugging)"):
            st.json({"score": s1, "allocate": s2, "retrieve": sR, "tips": s3})

elif go and not st.session_state.subjects:
    st.error("Add at least one subject first.")
