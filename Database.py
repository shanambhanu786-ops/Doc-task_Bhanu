import sqlite3
import json

DB_FILE = "state_store.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_state (
                job_id TEXT PRIMARY KEY,
                stage TEXT,
                state_data TEXT,
                human_approval_status TEXT DEFAULT 'PENDING'
            )
        """)
        conn.commit()

def save_job_state(job_id: str, stage: str, state_data: dict):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO job_state (job_id, stage, state_data) VALUES (?, ?, ?)",
            (job_id, stage, json.dumps(state_data))
        )
        conn.commit()

def load_job_state(job_id: str):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT stage, state_data, human_approval_status FROM job_state WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if row:
            return {"stage": row[0], "state_data": json.loads(row[1]), "approval_status": row[2]}
    return None
