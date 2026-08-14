import sqlite3

DB_PATH = "zed_sni.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL,
            status TEXT NOT NULL,
            dns INTEGER NOT NULL,
            tcp INTEGER NOT NULL,
            tls INTEGER NOT NULL,
            https INTEGER NOT NULL,
            latency_ms INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()
