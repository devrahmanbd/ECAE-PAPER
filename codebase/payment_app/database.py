"""Database models for the payment system."""

from typing import Dict, List, Optional
import time
import sqlite3


class Database:
    """Simple SQLite-based database for the payment system."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id TEXT PRIMARY KEY,
                order_id TEXT,
                amount REAL,
                status TEXT,
                created_at REAL,
                updated_at REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id TEXT,
                status TEXT,
                total_amount REAL,
                created_at REAL,
                updated_at REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                email TEXT,
                password_hash TEXT,
                created_at REAL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                entity_type TEXT,
                entity_id TEXT,
                details TEXT,
                timestamp REAL
            )
        """)
        self.conn.commit()

    def insert_transaction(self, tx_id: str, order_id: str, amount: float, status: str) -> None:
        """Insert a transaction record."""
        cursor = self.conn.cursor()
        now = time.time()
        cursor.execute("""
            INSERT OR REPLACE INTO transactions
            (tx_id, order_id, amount, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tx_id, order_id, amount, status, now, now))
        self.conn.commit()
        self._log_event("insert", "transaction", tx_id, {"amount": amount, "status": status})

    def get_transaction(self, tx_id: str) -> Optional[Dict]:
        """Retrieve a transaction by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE tx_id = ?", (tx_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "tx_id": row[0], "order_id": row[1], "amount": row[2],
            "status": row[3], "created_at": row[4], "updated_at": row[5],
        }

    def insert_order(self, order_id: str, user_id: str, status: str, total_amount: float) -> None:
        """Insert an order record."""
        cursor = self.conn.cursor()
        now = time.time()
        cursor.execute("""
            INSERT OR REPLACE INTO orders
            (order_id, user_id, status, total_amount, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (order_id, user_id, status, total_amount, now, now))
        self.conn.commit()
        self._log_event("insert", "order", order_id, {"user_id": user_id, "status": status})

    def get_order(self, order_id: str) -> Optional[Dict]:
        """Retrieve an order by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "order_id": row[0], "user_id": row[1], "status": row[2],
            "total_amount": row[3], "created_at": row[4], "updated_at": row[5],
        }

    def update_order_status(self, order_id: str, status: str) -> None:
        """Update order status."""
        cursor = self.conn.cursor()
        now = time.time()
        cursor.execute("""
            UPDATE orders SET status = ?, updated_at = ? WHERE order_id = ?
        """, (status, now, order_id))
        self.conn.commit()
        self._log_event("update", "order", order_id, {"status": status})

    def get_audit_log(self, entity_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Retrieve audit log entries."""
        cursor = self.conn.cursor()
        if entity_type:
            cursor.execute("""
                SELECT * FROM audit_log
                WHERE entity_type = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (entity_type, limit))
        else:
            cursor.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [
            {"id": r[0], "event_type": r[1], "entity_type": r[2],
             "entity_id": r[3], "details": r[4], "timestamp": r[5]}
            for r in rows
        ]

    def _log_event(self, event_type: str, entity_type: str, entity_id: str, details: dict) -> None:
        """Log an event to the audit log."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (event_type, entity_type, entity_id, details, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (event_type, entity_type, entity_id, str(details), time.time()))
        self.conn.commit()

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()