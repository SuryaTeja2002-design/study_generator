awesome—here’s a polished, copy-paste **README.md** tailored to your repo **`SuryaTeja2002-design/study_generator`**. it’s boss-proof: explains agentic AI, why LangGraph, where RAG fits (optional), how to run, and what each node does.

---

# Study Schedule Generator (Agentic AI · LangGraph + Gemini)

Turn subjects + time constraints into a **weighted study timetable** and **coaching tips**.
Deterministic planning runs locally; a single **LLM** call (Gemini) writes structured guidance.

> 🎥 Demo video: *add your link here (YouTube / Drive / GitHub Release)*
> 📦 Repo: `SuryaTeja2002-design/study_generator`

---

## ✨ Why this matters

* **Agentic AI**: not a one-shot prompt. We orchestrate tools with **LangGraph**:

  1. **Score priorities** (deterministic math)
  2. **Allocate time** (deterministic scheduling)
  3. **Tips writer** (LLM → strict JSON)
* **Reliable + cheap**: only **one** LLM call; everything else is local + testable.
* **Optional RAG**: paste notes → build an in-memory index → the tips can include **citations**.

---

## 🧱 Architecture

```
START ─→ score ─→ allocate ─→ [retrieve]* ─→ tips ─→ END
                     (optional RAG)
```

* **State**: `ScheduleState` (TypedDict) carries inputs, derived metrics, and outputs.
* **Deterministic nodes**: `score`, `allocate`
* **LLM node**: `tips` (Gemini with `response_mime_type="application/json"`)
* **Optional**: `retrieve` pulls relevant chunks from an ephemeral vector index built from pasted notes.

---

## 📂 Project structure

```
study_generator/
├─ app.py
├─ agents/
│  └─ schedule_agent.py            # LangGraph nodes & compiled graph
├─ tools/
│  ├─ priority_score.py            # difficulty→required_hours & weights
│  ├─ allocate_time.py             # proportional daily scheduling with caps
│  └─ tips_writer.py               # Gemini prompt -> strict JSON tips
├─ utils/
│  └─ llm_client.py                # Google Generative AI helper
├─ requirements.txt
└─ README.md
```

> ⚠️ Do **not** commit `.env` (your API key). Add it to `.gitignore`.

---

## 🚀 Quickstart

### 1) Create a virtual env & install

```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2) Set up environment

Create a file named `.env` in the project root:

```ini
GOOGLE_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash
```

> Tip: never commit `.env`.

### 3) Run

```bash
python -m streamlit run app.py
```

Open the local URL (usually `http://localhost:8501`).

---

## 🧩 How it works (node-by-node)

### 1) `score` (deterministic)

* Computes `required_hours` per subject. If no custom target is provided:
  `required_hours = difficulty × 4`
* Computes normalized **weight** (heavier = more time earlier).
* Outputs: `subjects_enriched`, `total_required_hours`.

### 2) `allocate` (deterministic)

* Distributes `days_left × hours_per_day` by weight across days.
* **Caps** a subject when it hits `required_hours`.
* Outputs: `timetable`, `per_subject_allocation`, `total_available_hours`, `overbooked`, `hours_gap`.

### 3) `retrieve` (optional RAG)

* If you paste notes and click **Build RAG**, we embed and index them **in memory** (FAISS).
* For each subject, we search the index and store top chunks in `contexts`.

### 4) `tips` (LLM)

* One Gemini call with `response_mime_type="application/json"`.
* Returns:

  ```json
  {
    "study_principles": [],
    "focus_order": [],
    "breaks": {"work": 50, "break": 10},
    "daily_checklist": [],
    "if_overbooked": {"strategy": "...", "actions": [...]},
    "rag_suggestions": [],
    "citations": []
  }
  ```
* If the API fails, the app **keeps the timetable** and skips tips gracefully.

---

## 🖥️ Using the app

1. Enter **Days left** and **Hours per day**.
2. Add subjects with **difficulty** (1–5). Optional: custom **target hours**.
3. (Optional) Paste notes in the sidebar → **Build RAG** (creates an in-memory index).
4. Click **Generate Study Plan**.
5. Review:

   * KPIs (Required vs Available Hours, Gap)
   * **Subjects & Priorities**
   * **Timetable** (table + chart)
   * **Study Tips & Checklist** (LLM JSON; shows Overbooked strategy if needed)
   * If RAG was built: **RAG Suggestions** + **Citations**
6. Click **Download JSON Plan** to export the full plan.

---

## 🔒 Security & privacy

* `.env` is ignored; API key never committed.
* Optional RAG index is **ephemeral** (in RAM for the session).
* Only the **tips** call hits the LLM provider; deterministic steps are local.

---

## 🧪 Testing (suggested)

Deterministic nodes are unit-testable:

```bash
pytest -q
```

* Mock Gemini in tests for the `tips` node.
* Edge cases: zero days, large gaps, custom target hours, overbooked scenarios.

---

## 🛠️ Troubleshooting

* **“Gemini call failed”** → Check `.env` has a valid `GOOGLE_API_KEY`.
* **No tips shown** → LLM failure is handled; plan still renders.
* **RAG not building** → Ensure `faiss-cpu` is installed; otherwise use without RAG.
* **Nothing happens on Generate** → Ensure you added at least one subject.

---

## 📜 License

MIT (suggested). Add a `LICENSE` file or choose another open source license.

---

## 🙏 Acknowledgements

* [LangGraph](https://github.com/langchain-ai/langgraph) for the state-machine agent framework
* Google **Gemini** for the structured JSON tips

---

