"""
LitigationOS Hybrid Search Engine
Combines keyword (tantivy/FTS5), semantic (LanceDB), and analytical (DuckDB) search.
Each engine excels at different query types — combined they cover all patterns.

v2.0 — Added cross-encoder reranking (ms-marco-MiniLM-L6-v2) and BM25 scoring.
v2.1 — Singleton model caching, ``fast`` mode, per-stage timing, ``warm_up()``.
"""

__all__ = [
    "SearchResult",
    "TantivyIndex",
    "HybridSearchEngine",
    "warm_up",
]

import hashlib
import logging
import os
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tantivy

from .reranker import rerank as rerank_results, get_reranker
from .hybrid import (
    hybrid_search as standalone_hybrid_search,
    fts5_bm25_search,
    get_semantic_engine as _get_standalone_semantic_engine,
    warm_up as warm_up_standalone,
)

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent.parent.parent / "litigation_context.db"
INDEX_DIR = Path(__file__).parent / "indexes"

CHILD_NAME_RE = re.compile(
    r"\b(?:Lincoln\s+(?:Dean\s+)?(?:Watson|Pigors|Watson[- ]Pigors))\b",
    re.IGNORECASE,
)


def _sanitize_child_name(text: str) -> str:
    return CHILD_NAME_RE.sub("L.D.W.", text) if text else ""


def _get_sqlite(db_path: str = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or str(DB_PATH))
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA cache_size = -32000")
    return conn


@dataclass
class SearchResult:
    """A single search result from any engine."""
    id: str
    text: str
    score: float
    source: str  # "keyword", "semantic", "analytical"
    table: str
    metadata: dict = field(default_factory=dict)


class TantivyIndex:
    """Rust-backed full-text search index using tantivy-py."""

    def __init__(self, name: str, index_dir: Path = INDEX_DIR):
        self.name = name
        self.path = index_dir / name
        self.path.mkdir(parents=True, exist_ok=True)
        self._index: Optional[tantivy.Index] = None
        self._schema: Optional[tantivy.SchemaBuilder] = None

    def build_from_sqlite(
        self,
        db_path: str,
        table: str,
        text_col: str,
        id_col: str = "id",
        batch_size: int = 5000,
        extra_cols: list[str] = None,
    ) -> int:
        """Build tantivy index from a SQLite table."""
        schema_builder = tantivy.SchemaBuilder()
        schema_builder.add_text_field("id", stored=True)
        schema_builder.add_text_field("text", stored=True, tokenizer_name="en_stem")
        for col in (extra_cols or []):
            schema_builder.add_text_field(col, stored=True)
        schema = schema_builder.build()

        index = tantivy.Index(schema, path=str(self.path))
        writer = index.writer(heap_size=50_000_000)

        conn = _get_sqlite(db_path)
        cols = [id_col, text_col] + (extra_cols or [])
        col_str = ", ".join(cols)

        cursor = conn.execute(f"SELECT {col_str} FROM {table} WHERE {text_col} IS NOT NULL")
        count = 0

        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            for row in rows:
                doc = tantivy.Document()
                doc.add_text("id", str(row[0]))
                doc.add_text("text", _sanitize_child_name(str(row[1])))
                for i, col in enumerate(extra_cols or [], start=2):
                    doc.add_text(col, str(row[i]) if row[i] else "")
                writer.add_document(doc)
                count += 1
            if count % 10000 == 0:
                writer.commit()

        writer.commit()
        conn.close()
        self._index = index
        return count

    def search(self, query: str, top_k: int = 20) -> list[SearchResult]:
        """Search the tantivy index."""
        if self._index is None:
            schema_builder = tantivy.SchemaBuilder()
            schema_builder.add_text_field("id", stored=True)
            schema_builder.add_text_field("text", stored=True, tokenizer_name="en_stem")
            schema = schema_builder.build()
            self._index = tantivy.Index(schema, path=str(self.path))

        self._index.reload()
        searcher = self._index.searcher()

        safe_query = re.sub(r"[^\w\s\"*]", " ", query).strip()
        if not safe_query:
            return []

        parsed = self._index.parse_query(safe_query, ["text"])
        results = searcher.search(parsed, top_k).hits

        output = []
        for score, doc_addr in results:
            doc = searcher.doc(doc_addr)
            output.append(SearchResult(
                id=doc.get_first("id") or "",
                text=doc.get_first("text") or "",
                score=float(score),
                source="keyword",
                table=self.name,
            ))
        return output


class HybridSearchEngine:
    """Unified search across keyword, semantic, and analytical backends."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self._tantivy_indexes: dict[str, TantivyIndex] = {}
        self._semantic_engine = None
        self._legalbert_engine = None

    def get_tantivy_index(self, name: str) -> TantivyIndex:
        if name not in self._tantivy_indexes:
            self._tantivy_indexes[name] = TantivyIndex(name)
        return self._tantivy_indexes[name]

    def _get_legalbert(self):
        """Lazy-load Legal-BERT perception engine (singleton, cached)."""
        if self._legalbert_engine is None:
            try:
                import sys
                perception_dir = str(Path(__file__).parent.parent / "perception")
                if perception_dir not in sys.path:
                    sys.path.insert(0, perception_dir)
                from engine import get_engine as _get_lb
                eng = _get_lb()
                if not eng.is_ready:
                    eng._load_model()
                self._legalbert_engine = eng
                log.info("Legal-BERT loaded for hybrid search")
            except Exception as e:
                log.warning("Legal-BERT unavailable: %s", e)
        return self._legalbert_engine

    def keyword_search(
        self,
        query: str,
        table: str = "evidence_quotes",
        top_k: int = 20,
    ) -> list[SearchResult]:
        """Fast keyword search via tantivy (Rust-backed)."""
        idx = self.get_tantivy_index(table)
        return idx.search(query, top_k)

    def fts5_search(
        self,
        query: str,
        table: str = "evidence_quotes",
        text_col: str = "quote_text",
        fts_table: str = "evidence_fts",
        top_k: int = 20,
    ) -> list[SearchResult]:
        """SQLite FTS5 search with BM25 ranking.

        Uses ``bm25()`` ranking function for relevance-ordered results.
        Falls back to LIKE on any FTS5 error (Rule 15).
        """
        conn = _get_sqlite(self.db_path)
        safe = re.sub(r"[^\w\s*\"]", " ", query).strip()
        try:
            try:
                # BM25-ranked: lower bm25() = better match
                rows = conn.execute(
                    f"SELECT rowid, *, bm25({fts_table}) AS bm25_score "
                    f"FROM {fts_table} "
                    f"WHERE {fts_table} MATCH ? "
                    f"ORDER BY bm25({fts_table}) "
                    f"LIMIT ?",
                    (safe, top_k),
                ).fetchall()
                results = []
                for r in rows:
                    r_dict = dict(zip([d[0] for d in conn.execute(
                        f"SELECT rowid, *, bm25({fts_table}) AS bm25_score "
                        f"FROM {fts_table} LIMIT 0"
                    ).description], r))
                    bm25 = r_dict.get("bm25_score", 0)
                    text_val = ""
                    for key in (text_col, "quote_text", "event_text", "text"):
                        if key in r_dict and r_dict[key]:
                            text_val = str(r_dict[key])
                            break
                    results.append(SearchResult(
                        id=str(r_dict.get("rowid", "")),
                        text=_sanitize_child_name(text_val),
                        score=abs(float(bm25)) if bm25 else 0.0,
                        source="fts5_bm25",
                        table=table,
                    ))
                return results
            except Exception as e:
                log.warning("FTS5 BM25 query failed (%s), falling back to LIKE", e)
                rows = conn.execute(
                    f"SELECT id, {text_col} FROM {table} WHERE {text_col} LIKE '%' || ? || '%' LIMIT ?",
                    (query, top_k),
                ).fetchall()
                return [
                    SearchResult(
                        id=str(r[0]),
                        text=_sanitize_child_name(str(r[1])) if r[1] else "",
                        score=1.0,
                        source="fts5_like",
                        table=table,
                    )
                    for r in rows
                ]
        finally:
            conn.close()

    def semantic_search(
        self,
        query: str,
        table: str = "evidence_quotes",
        top_k: int = 20,
    ) -> list[SearchResult]:
        """Semantic vector search via sentence-transformers + LanceDB."""
        if self._semantic_engine is None:
            try:
                import sys
                sys.path.insert(0, str(Path(__file__).parent.parent / "semantic"))
                from engine import SemanticSearchEngine
                self._semantic_engine = SemanticSearchEngine(self.db_path)
            except ImportError:
                return []

        try:
            raw = self._semantic_engine.search(query, table, top_k)
            return [
                SearchResult(
                    id=str(r.get("id", "")),
                    text=_sanitize_child_name(str(r.get("text", ""))),
                    score=float(r.get("score", 0)),
                    source="semantic",
                    table=table,
                )
                for r in raw
            ]
        except Exception:
            return []

    def hybrid_search(
        self,
        query: str,
        table: str = "evidence_quotes",
        top_k: int = 20,
        weights: dict = None,
        use_reranker: bool = True,
        fast: bool = False,
    ) -> list[SearchResult]:
        """Fused search: keyword + semantic + FTS5/BM25, with cross-encoder reranking.

        Args:
            query: Search query
            table: Table to search
            top_k: Max results
            weights: {"keyword": 0.4, "semantic": 0.4, "fts5": 0.2}
            use_reranker: If True, apply cross-encoder reranking as final stage
            fast: If True, reduce candidate pool for interactive speed
        """
        stages: dict[str, float] = {}
        t_start = time.perf_counter()
        w = weights or {"keyword": 0.4, "semantic": 0.4, "fts5": 0.2}

        t0 = time.perf_counter()
        keyword_results = self.keyword_search(query, table, top_k * 2)
        stages["keyword"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        semantic_results = self.semantic_search(query, table, top_k * 2)
        stages["semantic"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        fts5_results = self.fts5_search(query, table, top_k=top_k * 2)
        stages["fts5"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        scored: dict[str, SearchResult] = {}

        for results, source_weight in [
            (keyword_results, w.get("keyword", 0.4)),
            (semantic_results, w.get("semantic", 0.4)),
            (fts5_results, w.get("fts5", 0.2)),
        ]:
            if not results:
                continue
            max_score = max(r.score for r in results) if results else 1.0
            for r in results:
                norm_score = (r.score / max_score) * source_weight if max_score > 0 else 0
                if r.id in scored:
                    scored[r.id].score += norm_score
                    scored[r.id].source += f"+{r.source}"
                else:
                    r.score = norm_score
                    scored[r.id] = r

        ranked = sorted(scored.values(), key=lambda x: x.score, reverse=True)
        stages["fusion"] = time.perf_counter() - t0

        # Legal-BERT domain scoring (skip in fast mode for interactive speed)
        max_candidates = 15 if fast else top_k * 3
        lb_scores_map: dict[str, float] = {}
        if not fast and len(ranked) > 1:
            legalbert = self._get_legalbert()
            if legalbert is not None and legalbert.is_ready:
                try:
                    t0 = time.perf_counter()
                    candidates = ranked[:max_candidates]
                    doc_texts = [r.text[:2000] for r in candidates]
                    scores = legalbert.score_batch(query, doc_texts)
                    for r, lb_score in zip(candidates, scores):
                        lb_scores_map[r.id] = lb_score
                        r.metadata["legalbert_score"] = lb_score
                    stages["legalbert"] = time.perf_counter() - t0
                except Exception as e:
                    log.warning("Legal-BERT scoring failed: %s", e)

        # Cross-encoder reranking + Legal-BERT blend: precision stage
        if use_reranker and len(ranked) > 1:
            try:
                t0 = time.perf_counter()
                candidate_dicts = [
                    {"id": r.id, "text": r.text, "fusion_score": r.score,
                     "source": r.source, "table": r.table,
                     "legalbert_score": lb_scores_map.get(r.id, 0.0)}
                    for r in ranked[:max_candidates]
                ]
                reranked = rerank_results(query, candidate_dicts, text_key="text", top_k=top_k)
                stages["rerank"] = time.perf_counter() - t0

                # Blend cross-encoder + Legal-BERT for domain-aware ranking
                if lb_scores_map:
                    ce_vals = [d["rerank_score"] for d in reranked]
                    ce_min, ce_max = min(ce_vals), max(ce_vals)
                    ce_range = ce_max - ce_min if ce_max > ce_min else 1.0
                    for d in reranked:
                        norm_ce = (d["rerank_score"] - ce_min) / ce_range
                        norm_lb = (d.get("legalbert_score", 0.0) + 1) / 2
                        d["rerank_score"] = 0.7 * norm_ce + 0.3 * norm_lb
                    reranked.sort(key=lambda d: d["rerank_score"], reverse=True)

                stages["total"] = time.perf_counter() - t_start
                log.debug("HybridSearch stages: %s", stages)
                return [
                    SearchResult(
                        id=d["id"],
                        text=d["text"],
                        score=d["rerank_score"],
                        source=d.get("source", "reranked"),
                        table=d.get("table", table),
                        metadata={"fusion_score": d.get("fusion_score", 0),
                                  "legalbert_score": d.get("legalbert_score", 0),
                                  "stages": stages},
                    )
                    for d in reranked
                ]
            except Exception as e:
                log.warning("Reranker unavailable, returning fusion-ranked: %s", e)

        stages["total"] = time.perf_counter() - t_start
        log.debug("HybridSearch stages (no rerank): %s", stages)
        return ranked[:top_k]

    def build_indexes(self, tables: list[dict] = None) -> dict:
        """Build tantivy indexes for specified tables.

        Args:
            tables: List of {name, text_col, id_col} dicts.
                    Defaults to evidence_quotes + timeline_events.
        """
        default_tables = [
            {"name": "evidence_quotes", "text_col": "quote_text", "id_col": "id"},
            {"name": "timeline_events", "text_col": "event_text", "id_col": "id"},
        ]
        targets = tables or default_tables
        results = {}

        for t in targets:
            idx = self.get_tantivy_index(t["name"])
            count = idx.build_from_sqlite(
                self.db_path,
                t["name"],
                t["text_col"],
                t.get("id_col", "id"),
            )
        return results


# ---------------------------------------------------------------------------
# Module-level warm-up
# ---------------------------------------------------------------------------


def warm_up():
    """Pre-load cross-encoder + semantic models.  Call once at startup."""
    warm_up_standalone()  # reranker + semantic engine from hybrid.py
