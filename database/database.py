import sqlite3
import os

# Database file path (default to local)
# IMPORTANT: If you set up a Railway Volume later, change this to /data/zed_sni.db
DB_PATH = "zed_sni.db"

def init_db():
    """Initializes the SQLite database and creates tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table for real-time test results
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hostname TEXT NOT NULL,
        network TEXT,
        status TEXT NOT NULL,
        dns INTEGER,
        tcp INTEGER,
        tls INTEGER,
        https INTEGER,
        latency_ms INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Table for monitored hosts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS monitored_hosts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hostname TEXT NOT NULL UNIQUE,
        network TEXT,
        enabled INTEGER DEFAULT 1,
        last_status TEXT,
        last_latency_ms INTEGER,
        last_checked_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def save_result(hostname, status, dns, tcp, tls, https, latency_ms, network="Global"):
    """Saves a single test result to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO test_results (hostname, network, status, dns, tcp, tls, https, latency_ms)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (hostname, network, status, 1 if dns else 0, 1 if tcp else 0, 1 if tls else 0, 1 if https else 0, latency_ms))
    conn.commit()
    conn.close()

def get_recent_results(hostname, limit=10):
    """Retrieves the most recent test results for a hostname."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
    SELECT status, latency_ms, timestamp FROM test_results
    WHERE hostname = ? ORDER BY timestamp DESC LIMIT ?
    """, (hostname, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- NEW FUNCTION FOR UPGRADE #1 ---
def get_hostname_stats(hostname):
    """
    Calculates detailed historical stats for a single hostname.
    Returns a dictionary with total tests, uptime %, average latency, etc.
    Returns None if the hostname has never been tested.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Total tests
    cursor.execute("SELECT COUNT(*) as total FROM test_results WHERE hostname = ?", (hostname,))
    total_tests = cursor.fetchone()["total"]
    
    if total_tests == 0:
        conn.close()
        return None

    # 2. Active tests
    cursor.execute("SELECT COUNT(*) as active FROM test_results WHERE hostname = ? AND status = 'ACTIVE'", (hostname,))
    active_tests = cursor.fetchone()["active"]

    # 3. Latency stats (ignore NULL latency values)
    cursor.execute("SELECT AVG(latency_ms) as avg_latency FROM test_results WHERE hostname = ? AND latency_ms IS NOT NULL", (hostname,))
    avg_latency = cursor.fetchone()["avg_latency"]
    cursor.execute("SELECT MIN(latency_ms) as best_latency FROM test_results WHERE hostname = ? AND latency_ms IS NOT NULL", (hostname,))
    best_latency = cursor.fetchone()["best_latency"]
    cursor.execute("SELECT MAX(latency_ms) as worst_latency FROM test_results WHERE hostname = ? AND latency_ms IS NOT NULL", (hostname,))
    worst_latency = cursor.fetchone()["worst_latency"]

    # 4. Last checked timestamp
    cursor.execute("SELECT timestamp FROM test_results WHERE hostname = ? ORDER BY timestamp DESC LIMIT 1", (hostname,))
    last_check_row = cursor.fetchone()
    last_check = last_check_row["timestamp"] if last_check_row else None

    conn.close()

    return {
        "hostname": hostname,
        "total_tests": total_tests,
        "active_tests": active_tests,
        "uptime_percent": round((active_tests / total_tests) * 100, 2),
        "avg_latency": round(avg_latency, 2) if avg_latency else None,
        "best_latency": round(best_latency, 2) if best_latency else None,
        "worst_latency": round(worst_latency, 2) if worst_latency else None,
        "last_check": last_check
    }

def get_top_hostnames(limit=5):
    """Retrieves the most tested hostnames with their success rate and average latency."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        hostname,
        COUNT(*) as total_tests,
        AVG(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) * 100 as success_rate,
        AVG(latency_ms) as average_latency
    FROM test_results
    GROUP BY hostname
    ORDER BY total_tests DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_monitored_host(hostname, network="Global"):
    """Adds a hostname to the monitoring table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO monitored_hosts (hostname, network)
        VALUES (?, ?)
        """, (hostname, network))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Hostname already exists in monitoring
        return False
    finally:
        conn.close()

def remove_monitored_host(hostname):
    """Removes a hostname from the monitoring table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM monitored_hosts WHERE hostname = ?", (hostname,))
    conn.commit()
    conn.close()

def get_monitored_hosts():
    """Retrieves all monitored hosts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monitored_hosts ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [tuple(row) for row in rows]

def update_monitored_host_status(hostname, status, latency_ms):
    """Updates the last status and latency of a monitored host."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE monitored_hosts 
    SET last_status = ?, last_latency_ms = ?, last_checked_at = CURRENT_TIMESTAMP
    WHERE hostname = ?
    """, (status, latency_ms, hostname))
    conn.commit()
    conn.close()

def get_monitored_host(hostname):
    """Retrieves a single monitored host's details."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monitored_hosts WHERE hostname = ?", (hostname,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
