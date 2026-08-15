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

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS monitored_hosts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL UNIQUE,
            network TEXT,
            enabled INTEGER NOT NULL DEFAULT 1,
            last_status TEXT,
            last_latency_ms INTEGER,
            last_checked_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_monitored_enabled
        ON monitored_hosts(enabled)
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
            SUM(
                CASE
                    WHEN status = 'ACTIVE'
                    THEN 1
                    ELSE 0
                END
            ),
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


def get_top_hostnames(limit: int = 10):
    conn = get_connection()

    cursor = conn.execute(
        """
        SELECT
            hostname,
            COUNT(*) AS total_tests,
            SUM(
                CASE
                    WHEN status = 'ACTIVE'
                    THEN 1
                    ELSE 0
                END
            ) AS successful_tests,
            AVG(latency_ms) AS average_latency
        FROM test_results
        GROUP BY hostname
        HAVING COUNT(*) > 0
        ORDER BY
            (successful_tests * 1.0 / total_tests) DESC,
            average_latency ASC
        LIMIT ?
        """,
        (limit,),
    )

    rows = cursor.fetchall()
    conn.close()

    rankings = []

    for hostname, total, successful, average_latency in rows:

        success_rate = (
            (successful / total) * 100
            if total
            else 0
        )

        rankings.append(
            {
                "hostname": hostname,
                "total_tests": total,
                "successful_tests": successful,
                "success_rate": round(success_rate, 1),
                "average_latency": (
                    round(average_latency)
                    if average_latency is not None
                    else None
                ),
            }
        )

    return rankings


def add_monitored_host(
    hostname: str,
    network: Optional[str] = None,
):
    conn = get_connection()

    conn.execute(
        """
        INSERT OR IGNORE INTO monitored_hosts (
            hostname,
            network,
            enabled
        )
        VALUES (?, ?, 1)
        """,
        (
            hostname,
            network,
        ),
    )

    conn.commit()
    conn.close()


def remove_monitored_host(hostname: str):
    conn = get_connection()

    conn.execute(
        """
        DELETE FROM monitored_hosts
        WHERE hostname = ?
        """,
        (hostname,),
    )

    conn.commit()
    conn.close()


def get_monitored_hosts():
    conn = get_connection()

    cursor = conn.execute(
        """
        SELECT
            id,
            hostname,
            network,
            enabled,
            last_status,
            last_latency_ms,
            last_checked_at
        FROM monitored_hosts
        WHERE enabled = 1
        ORDER BY hostname ASC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def update_monitored_host(
    hostname: str,
    status: str,
    latency_ms: Optional[int] = None,
):
    conn = get_connection()

    cursor = conn.execute(
        """
        SELECT last_status
        FROM monitored_hosts
        WHERE hostname = ?
        """,
        (hostname,),
    )

    row = cursor.fetchone()

    previous_status = (
        row[0]
        if row
        else None
    )

    conn.execute(
        """
        UPDATE monitored_hosts
        SET
            last_status = ?,
            last_latency_ms = ?,
            last_checked_at = CURRENT_TIMESTAMP
        WHERE hostname = ?
        """,
        (
            status,
            latency_ms,
            hostname,
        ),
    )

    conn.commit()
    conn.close()

    return previous_status


def get_monitored_host(hostname: str):
    conn = get_connection()

    cursor = conn.execute(
        """
        SELECT
            id,
            hostname,
            network,
            enabled,
            last_status,
            last_latency_ms,
            last_checked_at
        FROM monitored_hosts
        WHERE hostname = ?
        """,
        (hostname,),
    )

    row = cursor.fetchone()
    conn.close()

    return row
