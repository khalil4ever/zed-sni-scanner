import sqlite3
from typing import Optional

DB_PATH = "zed_sni.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL,
            network TEXT,
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

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_test_hostname
        ON test_results(hostname)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_test_created
        ON test_results(created_at)
        """
    )

    conn.commit()
    conn.close()


def save_result(
    hostname: str,
    status: str,
    dns: bool,
    tcp: bool,
    tls: bool,
    https: bool,
    latency_ms: Optional[int] = None,
    network: Optional[str] = None,
):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO test_results (
            hostname,
            network,
            status,
            dns,
            tcp,
            tls,
            https,
            latency_ms
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            hostname,
            network,
            status,
            int(dns),
            int(tcp),
            int(tls),
            int(https),
            latency_ms,
        ),
    )

    conn.commit()
    conn.close()


def get_recent_results(limit: int = 10):
    conn = get_connection()

    cursor = conn.execute(
        """
        SELECT
            hostname,
            network,
            status,
            latency_ms,
            created_at
        FROM test_results
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    )

    results = cursor.fetchall()
    conn.close()

    return results


def get_hostname_stats(hostname: str):
    conn = get_connection()

    cursor = conn.execute(
        """
        SELECT
            COUNT(*),
            SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END),
            AVG(latency_ms)
        FROM test_results
        WHERE hostname = ?
        """,
        (hostname,),
    )

    result = cursor.fetchone()
    conn.close()

    total = result[0] or 0
    active = result[1] or 0
    avg_latency = result[2]

    success_rate = (
        (active / total) * 100
        if total > 0
        else 0
    )

    return {
        "total_tests": total,
        "successful_tests": active,
        "success_rate": round(success_rate, 1),
        "average_latency": (
            round(avg_latency)
            if avg_latency is not None
            else None
        ),
    }
