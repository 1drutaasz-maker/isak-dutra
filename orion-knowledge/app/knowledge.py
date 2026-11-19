"""Local source-of-truth storage and TF-IDF retrieval; no fake generated answers."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from uuid import uuid4

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

DB_PATH = Path(os.getenv("ORION_DB", "var/knowledge.db"))


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript("""
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS chunks (
        id TEXT PRIMARY KEY, doc_id TEXT NOT NULL, position INTEGER NOT NULL,
        body TEXT NOT NULL, FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(doc_id);
    """)
    return con


def chunk_text(content: str, length: int = 115, overlap: int = 25) -> list[str]:
    words = content.split()
    if not words:
        return []
    if not 0 <= overlap < length:
        raise ValueError("Overlap precisa ser menor que o comprimento.")
    step = length - overlap
    return [" ".join(words[i:i + length]) for i in range(0, len(words), step)
            if len(words[i:i + length]) >= 3 or i == 0]


def add_document(title: str, content: str) -> dict:
    parts = chunk_text(content)
    if not parts:
        raise ValueError("Documento sem texto.")
    doc_id = uuid4().hex
    conn = connect()
    try:
        with conn:
            conn.execute("INSERT INTO documents (id,title,content) VALUES (?,?,?)",
                         (doc_id, title, content))
            conn.executemany(
                "INSERT INTO chunks (id,doc_id,position,body) VALUES (?,?,?,?)",
                [(uuid4().hex, doc_id, idx + 1, part) for idx, part in enumerate(parts)]
            )
    finally:
        conn.close()
    return {"id": doc_id, "title": title, "chunks": len(parts)}


def list_documents() -> list[dict]:
    conn = connect()
    try:
        rows = conn.execute("""
            SELECT d.id,d.title,COUNT(c.id) AS chunks
            FROM documents d LEFT JOIN chunks c ON c.doc_id=d.id
            GROUP BY d.id ORDER BY d.rowid DESC
        """).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def remove_document(doc_id: str) -> bool:
    conn = connect()
    try:
        with conn:
            deleted = conn.execute("DELETE FROM documents WHERE id=?", (doc_id,)).rowcount
        return deleted > 0
    finally:
        conn.close()


def retrieve(query: str, k: int = 4) -> list[dict]:
    conn = connect()
    try:
        data = conn.execute("""
            SELECT c.id,c.doc_id,c.position,c.body,d.title
            FROM chunks c JOIN documents d ON c.doc_id=d.id ORDER BY d.rowid,c.position
        """).fetchall()
    finally:
        conn.close()
    if not data:
        return []
    corpus = [row["body"] for row in data]
    try:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1,
                                     sublinear_tf=True, strip_accents="unicode")
        matrix = vectorizer.fit_transform(corpus)
        query_vector = vectorizer.transform([query])
        scores = (matrix @ query_vector.T).toarray().ravel()
    except ValueError:  # e.g. corpus consists only of punctuation
        return []
    relevant = np.argsort(scores)[::-1][:k]
    return [
        {"chunk_id": data[int(i)]["id"], "document_id": data[int(i)]["doc_id"],
         "document": data[int(i)]["title"], "section": data[int(i)]["position"],
         "excerpt": data[int(i)]["body"], "score": round(float(scores[i]), 4)}
        for i in relevant if float(scores[i]) > 0.015
    ]
