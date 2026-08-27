"""Vector index for face similarity search.

Uses FAISS when installed, otherwise brute-force NumPy (fine up to tens of
thousands of records). Rebuilt lazily and invalidated whenever a reference
person is enrolled.
"""

from __future__ import annotations

import logging
import threading

import numpy as np
from sqlalchemy.orm import Session

from ..models import ReferencePerson

log = logging.getLogger(__name__)

_lock = threading.Lock()
_ids: list[int] = []
_matrix: np.ndarray | None = None
_faiss_index = None
_dirty = True


def invalidate() -> None:
    global _dirty
    with _lock:
        _dirty = True


def _build(db: Session) -> None:
    global _ids, _matrix, _faiss_index, _dirty

    rows = (
        db.query(ReferencePerson.id, ReferencePerson.face_embedding)
        .filter(ReferencePerson.face_embedding.isnot(None))
        .all()
    )
    vectors, ids = [], []
    dim = None
    for pid, emb in rows:
        if not emb:
            continue
        if dim is None:
            dim = len(emb)
        if len(emb) != dim:
            continue  # embeddings from a different engine; skip
        ids.append(pid)
        vectors.append(emb)

    if not vectors:
        _ids, _matrix, _faiss_index, _dirty = [], None, None, False
        return

    mat = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat = mat / norms

    _ids = ids
    _matrix = mat
    _faiss_index = None

    try:
        import faiss

        index = faiss.IndexFlatIP(mat.shape[1])
        index.add(mat)
        _faiss_index = index
    except Exception:  # noqa: BLE001
        log.info("FAISS not installed; using NumPy brute-force search.")

    _dirty = False


def engine_name() -> str:
    return "faiss-flat-ip" if _faiss_index is not None else "numpy-bruteforce"


def search(db: Session, embedding: list[float], top_k: int = 50) -> list[tuple[int, float]]:
    """Return [(person_id, cosine_similarity)] sorted best-first."""
    global _dirty
    with _lock:
        if _dirty or _matrix is None:
            _build(db)
        ids, mat, index = _ids, _matrix, _faiss_index

    if mat is None or not ids or not embedding:
        return []

    q = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
    if q.shape[1] != mat.shape[1]:
        return []
    n = np.linalg.norm(q)
    if n == 0:
        return []
    q = q / n

    k = min(top_k, len(ids))
    if index is not None:
        scores, idxs = index.search(q, k)
        return [(ids[i], float(s)) for i, s in zip(idxs[0], scores[0]) if i >= 0]

    sims = (mat @ q.T).ravel()
    order = np.argsort(-sims)[:k]
    return [(ids[i], float(sims[i])) for i in order]