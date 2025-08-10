# tools/rag_store.py
import os
from typing import List, Dict, Tuple

# ephemeral index stored in memory for the current Streamlit session
_EPHEMERAL = {"index": None, "meta": []}

def _embed_texts(texts: List[str]) -> List[List[float]]:
    import google.generativeai as genai
    api = os.getenv("GOOGLE_API_KEY")
    if not api:
        raise RuntimeError("GOOGLE_API_KEY not set for embeddings.")
    genai.configure(api_key=api)
    model = os.getenv("EMBED_MODEL", "text-embedding-004")
    out = []
    for t in texts:
        emb = genai.embed_content(model=model, content=t)
        out.append(emb["embedding"])
    return out

def _chunk(text: str, max_chars=900, overlap=120) -> List[str]:
    text = " ".join(text.split())
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i+max_chars])
        i += max_chars - overlap
    return [c for c in chunks if c.strip()]

def build_ephemeral_index(snippets: List[str], source_name: str = "Pasted") -> Tuple[int, int]:
    """
    Build an in-memory FAISS index from pasted notes.
    snippets: list of long strings (you can paste a whole page per item).
    Returns (num_chunks, dim).
    """
    import faiss, numpy as np
    texts, meta = [], []
    for i, s in enumerate(snippets):
        for j, ch in enumerate(_chunk(s)):
            texts.append(ch)
            meta.append({"id": f"{source_name}#{i+1}.{j+1}", "path": source_name, "text": ch})

    if not texts:
        _EPHEMERAL["index"], _EPHEMERAL["meta"] = None, []
        return 0, 0

    vecs = _embed_texts(texts)
    xb = np.array(vecs, dtype="float32")
    faiss.normalize_L2(xb)
    index = faiss.IndexFlatIP(xb.shape[1])
    index.add(xb)

    _EPHEMERAL["index"] = index
    _EPHEMERAL["meta"] = meta
    return len(meta), xb.shape[1]

def search(query: str, k: int = 5) -> List[Dict]:
    """
    Search the ephemeral index. If it's empty, returns [].
    """
    import faiss, numpy as np
    if _EPHEMERAL["index"] is None:
        return []
    qv = _embed_texts([query])[0]
    xq = np.array([qv], dtype="float32")
    faiss.normalize_L2(xq)
    D, I = _EPHEMERAL["index"].search(xq, k)
    meta = _EPHEMERAL["meta"]
    out = []
    for idx, score in zip(I[0], D[0]):
        if int(idx) < 0:
            continue
        m = meta[int(idx)]
        out.append({"id": m["id"], "path": m["path"], "score": float(score), "text": m["text"]})
    return out
