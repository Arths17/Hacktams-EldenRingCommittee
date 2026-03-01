"""
HealthOS — RAG Engine  (Retrieval-Augmented Generation)

Replaces the full 3,000-token nutrition dump with targeted semantic retrieval.
  • First run  : embeds 8,789 foods via all-MiniLM-L6-v2 (chromadb/onnx) ~60s
  • Subsequent : loads persisted index from model/chroma_db/ in <1s
  • Fallback   : tag-based lookup if chromadb is not installed

Usage
-----
  rag.build(nutrition_index_path)  → bool (True = semantic ready)
  rag.query(user_message, active_protocols, n=12) → str  (inject into prompt)
"""

import os
import json
from typing import Any

_MODULE_DIR  = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH  = os.path.join(_MODULE_DIR, "chroma_db")
COLL_NAME    = "health_foods"

_collection:     Any  = None   # chromadb Collection
_fallback_index: dict   = {}     # raw nutrition_index.json
_chroma_ready:   bool   = False


# ──────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────

def build(nutrition_index_path: str) -> bool:
    """
    Load nutrition_index.json and build / reuse the chromadb vector store.
    Returns True  → semantic search ready.
    Returns False → chromadb unavailable; tag-based fallback active.
    """
    global _collection, _fallback_index, _chroma_ready

    # Always load raw index (needed for fallback too)
    try:
        with open(nutrition_index_path) as fh:
            _fallback_index = json.load(fh)
    except Exception:
        return False

    # Try chromadb import
    try:
        import chromadb
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    except ImportError:
        return False

    total_foods = _fallback_index.get("meta", {}).get("total_foods", 0)
    os.makedirs(CHROMA_PATH, exist_ok=True)

    try:
        client = chromadb.PersistentClient(path=CHROMA_PATH)
    except Exception:
        return False

    # Reuse existing collection if food count matches (no rebuild needed)
    try:
        col = client.get_collection(COLL_NAME)
        if col.count() >= total_foods:
            _collection   = col
            _chroma_ready = True
            return True
        client.delete_collection(COLL_NAME)
    except Exception:
        pass

    # Build fresh vector store
    try:
        ef  = DefaultEmbeddingFunction()
        col = client.create_collection(COLL_NAME, embedding_function=ef)  # type: ignore[arg-type]
    except Exception:
        return False

    foods     = _fallback_index.get("foods", {})
    all_items = list(foods.items())
    total     = len(all_items)
    BATCH     = 250

    for start in range(0, total, BATCH):
        batch            = all_items[start : start + BATCH]
        ids, docs, metas = [], [], []

        for local_idx, (name, rec) in enumerate(batch):
            tags = " ".join(rec.get("tags") or [])
            cal  = rec.get("calories",  0) or 0
            p    = rec.get("protein_g", 0) or 0
            c    = rec.get("carbs_g",   0) or 0
            f    = rec.get("fat_g",     0) or 0
            fb   = rec.get("fiber_g",   0) or 0
            doc  = (
                f"{name}: {cal:.0f}kcal protein={p:.1f}g carbs={c:.1f}g "
                f"fat={f:.1f}g fiber={fb:.1f}g tags=[{tags}]"
            )
            ids.append(str(start + local_idx))
            docs.append(doc)
            metas.append({"name": name, "tags": tags})

        try:
            col.add(ids=ids, documents=docs, metadatas=metas)
        except Exception:
            pass

        done = min(start + BATCH, total)
        print(f"\r  🔍  Embedding foods {done}/{total}…", end="", flush=True)

    print()   # newline after progress

    _collection   = col
    _chroma_ready = True
    return True


def query(user_message: str, active_protocols: list, n: int = 12,
          constraint_graph=None) -> str:
    """
    Return a compact nutrition context string for prompt injection.
    Semantic search when chromadb is ready; tag-based fallback otherwise.
    constraint_graph: optional ConstraintGraph — filters forbidden foods before injection.
    Returns empty string if no index is loaded.
    """
    if not _fallback_index:
        return ""
    if _chroma_ready and _collection is not None:
        return _semantic_query(user_message, active_protocols, n, constraint_graph)
    return _tag_fallback(active_protocols, n, constraint_graph)


def is_ready() -> bool:
    return _chroma_ready


def is_loaded() -> bool:
    return bool(_fallback_index)


# ──────────────────────────────────────────────
# INTERNAL HELPERS
# ──────────────────────────────────────────────

def _semantic_query(user_message: str, active_protocols: list, n: int,
                    constraint_graph=None) -> str:
    q = user_message
    if active_protocols:
        q += " " + " ".join(p.replace("_protocol", "") for p in active_protocols[:5])

    try:
        count   = _collection.count()
        # Fetch extra results so we have headroom after constraint filtering
        fetch_n = min(n * 3, count)
        results = _collection.query(query_texts=[q], n_results=fetch_n)
    except Exception:
        return _tag_fallback(active_protocols, n, constraint_graph)

    foods = _fallback_index.get("foods", {})
    lines = ["\n🥗  RELEVANT FOODS (semantic search):"]
    shown = 0

    for meta in (results.get("metadatas") or [[]])[0]:
        if shown >= n:
            break
        name = meta.get("name", "")
        rec  = foods.get(name, {})
        if not rec:
            continue
        # ── Constraint graph filter ──────────────────────────────
        if constraint_graph is not None and not constraint_graph.allows_food(rec):
            continue
        cal = rec.get("calories",  0) or 0
        p   = rec.get("protein_g", 0) or 0
        c   = rec.get("carbs_g",   0) or 0
        f   = rec.get("fat_g",     0) or 0
        fb  = rec.get("fiber_g",   0) or 0
        tgs = ", ".join((rec.get("tags") or [])[:3])
        lines.append(
            f"  • {name}: {cal:.0f}kcal | P{p:.1f}g C{c:.1f}g F{f:.1f}g Fb{fb:.1f}g"
            + (f"  [{tgs}]" if tgs else "")
        )
        shown += 1

    return "\n".join(lines) if len(lines) > 1 else ""


def _tag_fallback(active_protocols: list, n: int, constraint_graph=None) -> str:
    tag_index = _fallback_index.get("tag_index", {})
    foods     = _fallback_index.get("foods", {})
    seen: set = set()
    lines     = ["\n🥗  RELEVANT FOODS (by protocol):"]
    per_proto = max(2, n // max(len(active_protocols or []), 1))

    for proto in (active_protocols or [])[:5]:
        added = 0
        for name in (tag_index.get(proto) or []):
            if added >= per_proto:
                break
            if name in seen:
                continue
            rec = foods.get(name, {})
            if not rec:
                continue
            # ── Constraint graph filter ──────────────────────────
            if constraint_graph is not None and not constraint_graph.allows_food(rec):
                continue
            seen.add(name)
            cal   = rec.get("calories",  0) or 0
            p     = rec.get("protein_g", 0) or 0
            c     = rec.get("carbs_g",   0) or 0
            label = proto.replace("_protocol", "")
            lines.append(f"  • {name}: {cal:.0f}kcal | P{p:.1f}g C{c:.1f}g  [{label}]")
            added += 1

    return "\n".join(lines) if len(lines) > 1 else ""
