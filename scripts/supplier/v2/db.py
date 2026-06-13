"""SQLite persistence for V2 pipeline state."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from ..config import DATA_DIR, V2_DB_FILE


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class CatalogDB:
    def __init__(self, path: Path = V2_DB_FILE) -> None:
        self.path = path
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS discovered_products (
                    cj_pid TEXT PRIMARY KEY,
                    cj_sku TEXT,
                    title_raw TEXT,
                    raw_json TEXT,
                    search_query TEXT,
                    discovered_at TEXT
                );
                CREATE TABLE IF NOT EXISTS scored_products (
                    cj_pid TEXT PRIMARY KEY,
                    opportunity_score REAL,
                    category_key TEXT,
                    rejected INTEGER DEFAULT 0,
                    rejection_reasons TEXT,
                    score_json TEXT,
                    scored_at TEXT
                );
                CREATE TABLE IF NOT EXISTS imported_products (
                    cj_pid TEXT PRIMARY KEY,
                    shopify_id TEXT,
                    shopify_handle TEXT,
                    collection_id TEXT,
                    collection_title TEXT,
                    opportunity_score REAL,
                    imported_at TEXT
                );
                CREATE TABLE IF NOT EXISTS collections_cache (
                    shopify_id TEXT PRIMARY KEY,
                    title TEXT,
                    handle TEXT,
                    tag TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT,
                    finished_at TEXT,
                    stats_json TEXT
                );
                """
            )

    def upsert_discovered(self, row: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO discovered_products (cj_pid, cj_sku, title_raw, raw_json, search_query, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cj_pid) DO UPDATE SET
                    raw_json=excluded.raw_json,
                    search_query=excluded.search_query,
                    discovered_at=excluded.discovered_at
                """,
                (
                    row["cj_pid"],
                    row.get("cj_sku"),
                    row.get("title_raw"),
                    json.dumps(row.get("raw") or {}),
                    row.get("search_query"),
                    _utcnow(),
                ),
            )

    def upsert_scored(self, row: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO scored_products
                (cj_pid, opportunity_score, category_key, rejected, rejection_reasons, score_json, scored_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cj_pid) DO UPDATE SET
                    opportunity_score=excluded.opportunity_score,
                    category_key=excluded.category_key,
                    rejected=excluded.rejected,
                    rejection_reasons=excluded.rejection_reasons,
                    score_json=excluded.score_json,
                    scored_at=excluded.scored_at
                """,
                (
                    row["cj_pid"],
                    row["opportunity_score"],
                    row.get("category_key"),
                    1 if row.get("rejected") else 0,
                    json.dumps(row.get("rejection_reasons") or []),
                    json.dumps(row.get("score_breakdown") or {}),
                    _utcnow(),
                ),
            )

    def record_import(self, row: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO imported_products
                (cj_pid, shopify_id, shopify_handle, collection_id, collection_title, opportunity_score, imported_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cj_pid) DO UPDATE SET
                    shopify_id=excluded.shopify_id,
                    shopify_handle=excluded.shopify_handle,
                    collection_id=excluded.collection_id,
                    collection_title=excluded.collection_title,
                    opportunity_score=excluded.opportunity_score,
                    imported_at=excluded.imported_at
                """,
                (
                    row["cj_pid"],
                    row.get("shopify_id"),
                    row.get("shopify_handle"),
                    row.get("collection_id"),
                    row.get("collection_title"),
                    row.get("opportunity_score"),
                    _utcnow(),
                ),
            )

    def is_imported(self, cj_pid: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM imported_products WHERE cj_pid = ?", (cj_pid,)
            ).fetchone()
            return row is not None

    def sync_collections_cache(self, collections: list[dict[str, Any]]) -> None:
        with self._conn() as conn:
            for col in collections:
                conn.execute(
                    """
                    INSERT INTO collections_cache (shopify_id, title, handle, tag, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(shopify_id) DO UPDATE SET
                        title=excluded.title,
                        handle=excluded.handle,
                        tag=excluded.tag,
                        updated_at=excluded.updated_at
                    """,
                    (
                        col["id"],
                        col["title"],
                        col.get("handle"),
                        col.get("tag"),
                        _utcnow(),
                    ),
                )

    def get_collections_cache(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM collections_cache").fetchall()
            return [dict(r) for r in rows]

    def start_pipeline_run(self) -> int:
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO pipeline_runs (started_at, stats_json) VALUES (?, ?)",
                (_utcnow(), "{}"),
            )
            return int(cur.lastrowid)

    def finish_pipeline_run(self, run_id: int, stats: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE pipeline_runs SET finished_at = ?, stats_json = ? WHERE id = ?",
                (_utcnow(), json.dumps(stats), run_id),
            )

    def get_imported_pids(self) -> set[str]:
        with self._conn() as conn:
            rows = conn.execute("SELECT cj_pid FROM imported_products").fetchall()
            return {r["cj_pid"] for r in rows}
