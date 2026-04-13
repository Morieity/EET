import sqlite3
import os
import threading

DB_PATH = os.path.join("db", "files.sqlite3")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL
);
"""

_CREATE_CONVERSATIONS_SQL = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

_CREATE_CHAT_ROUNDS_SQL = """
CREATE TABLE IF NOT EXISTS chat_rounds (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    question TEXT NOT NULL,
    prompt TEXT NOT NULL,
    answer TEXT NOT NULL,
    sources TEXT,
    fault_tree_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
"""

_CREATE_FAULT_TREES_SQL = """
CREATE TABLE IF NOT EXISTS fault_trees (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    conversation_id TEXT,
    created_at TEXT NOT NULL
);
"""

_CREATE_FAULT_TREE_NODES_SQL = """
CREATE TABLE IF NOT EXISTS fault_tree_nodes (
    id TEXT NOT NULL,
    tree_id TEXT NOT NULL,
    label TEXT NOT NULL,
    node_type TEXT NOT NULL,
    gate_type TEXT,
    remark TEXT DEFAULT '',
    PRIMARY KEY (id, tree_id),
    FOREIGN KEY (tree_id) REFERENCES fault_trees(id)
);
"""

_CREATE_FAULT_TREE_EDGES_SQL = """
CREATE TABLE IF NOT EXISTS fault_tree_edges (
    id TEXT NOT NULL,
    tree_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    PRIMARY KEY (id, tree_id),
    FOREIGN KEY (tree_id) REFERENCES fault_trees(id)
);
"""

_lock = threading.Lock()


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    # WAL 模式允许多个读操作并发执行，且读写不会互相阻塞
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _ensure_column_exists(conn: sqlite3.Connection, table_name: str, column_name: str, column_def: str) -> None:
    existing_columns = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in existing_columns:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


def init_db() -> None:
    conn = get_connection()
    try:
        with _lock:
            conn.execute(_CREATE_TABLE_SQL)
            conn.execute(_CREATE_CONVERSATIONS_SQL)
            conn.execute(_CREATE_CHAT_ROUNDS_SQL)
            conn.execute(_CREATE_FAULT_TREES_SQL)
            conn.execute(_CREATE_FAULT_TREE_NODES_SQL)
            conn.execute(_CREATE_FAULT_TREE_EDGES_SQL)
            _ensure_column_exists(conn, "chat_rounds", "fault_tree_id", "TEXT")
            conn.commit()
    finally:
        conn.close()
