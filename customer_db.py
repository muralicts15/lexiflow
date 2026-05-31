"""
Local customer-care database utilities for LexiFlow demos.
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional


DB_PATH = Path("data/customer_support.db")


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_customer_db(db_path: Path = DB_PATH) -> None:
    """Create demo support tables and seed sample data."""
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL UNIQUE,
                tier TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                order_id TEXT NOT NULL UNIQUE,
                customer_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                serial_number TEXT NOT NULL,
                purchase_date TEXT NOT NULL,
                delivery_date TEXT NOT NULL,
                order_status TEXT NOT NULL,
                payment_status TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            );

            CREATE TABLE IF NOT EXISTS warranties (
                id INTEGER PRIMARY KEY,
                order_id TEXT NOT NULL UNIQUE,
                warranty_end_date TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY,
                ticket_id TEXT NOT NULL UNIQUE,
                customer_id INTEGER NOT NULL,
                order_id TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                status TEXT NOT NULL,
                priority TEXT NOT NULL,
                created_at TEXT NOT NULL,
                summary TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(id),
                FOREIGN KEY(order_id) REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS email_drafts (
                id INTEGER PRIMARY KEY,
                draft_id TEXT NOT NULL UNIQUE,
                customer_id INTEGER NOT NULL,
                order_id TEXT NOT NULL,
                ticket_id TEXT,
                recipient TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(id),
                FOREIGN KEY(order_id) REFERENCES orders(order_id)
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                order_id TEXT,
                action TEXT NOT NULL,
                reference_id TEXT,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            );

            CREATE TABLE IF NOT EXISTS damage_inspections (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                order_id TEXT,
                image_url TEXT NOT NULL,
                inspection_status TEXT NOT NULL,
                damage_detected INTEGER NOT NULL,
                damage_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                confidence REAL NOT NULL,
                needs_human_review INTEGER NOT NULL,
                recommendation TEXT NOT NULL,
                source TEXT NOT NULL,
                model TEXT NOT NULL,
                notes TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            );
            """
        )

        seed_status = conn.execute(
            "SELECT value FROM app_metadata WHERE key = 'demo_seeded'"
        ).fetchone()
        customer_count = conn.execute("SELECT COUNT(*) AS count FROM customers").fetchone()["count"]
        if seed_status or customer_count > 0:
            conn.execute(
                "INSERT OR REPLACE INTO app_metadata (key, value) VALUES ('demo_seeded', 'true')"
            )
            return

        customers = [
            (1, "Priya Raman", "priya.raman@example.com", "9876543210", "Gold"),
            (2, "Arjun Mehta", "arjun.mehta@example.com", "9123456780", "Standard"),
            (3, "Nisha Kapoor", "nisha.kapoor@example.com", "9988776655", "Platinum"),
        ]
        conn.executemany(
            """
            INSERT OR IGNORE INTO customers (id, name, email, phone, tier)
            VALUES (?, ?, ?, ?, ?)
            """,
            customers,
        )

        orders = [
            (
                1,
                "ORD-1001",
                1,
                "Nova X1 Smart Hub",
                "NX1-77821",
                "2026-05-01",
                "2026-05-10",
                "Delivered",
                "Paid",
            ),
            (
                2,
                "ORD-1002",
                2,
                "Nova X1 Smart Hub",
                "NX1-88109",
                "2026-04-01",
                "2026-04-05",
                "Delivered",
                "Paid",
            ),
            (
                3,
                "ORD-1003",
                3,
                "AeroFit Band",
                "AFB-55290",
                "2026-05-24",
                "2026-05-27",
                "Delivered",
                "Paid",
            ),
        ]
        conn.executemany(
            """
            INSERT OR IGNORE INTO orders (
                id, order_id, customer_id, product_name, serial_number, purchase_date,
                delivery_date, order_status, payment_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            orders,
        )

        warranties = [
            (1, "ORD-1001", "2027-05-01", "Active"),
            (2, "ORD-1002", "2027-04-01", "Active"),
            (3, "ORD-1003", "2027-05-24", "Active"),
        ]
        conn.executemany(
            """
            INSERT OR IGNORE INTO warranties (id, order_id, warranty_end_date, status)
            VALUES (?, ?, ?, ?)
            """,
            warranties,
        )

        tickets = [
            (
                1,
                "TKT-2001",
                1,
                "ORD-1001",
                "technical",
                "Open",
                "Medium",
                "2026-05-29",
                "Customer reported device not turning on after charging.",
            ),
            (
                2,
                "TKT-2002",
                2,
                "ORD-1002",
                "refund",
                "Closed",
                "Low",
                "2026-04-20",
                "Refund request rejected because product was outside refund window.",
            ),
        ]
        conn.executemany(
            """
            INSERT OR IGNORE INTO tickets (
                id, ticket_id, customer_id, order_id, issue_type, status, priority,
                created_at, summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tickets,
        )
        conn.execute(
            "INSERT OR REPLACE INTO app_metadata (key, value) VALUES ('demo_seeded', 'true')"
        )


def lookup_case(identifier: str, db_path: Path = DB_PATH) -> Optional[Dict]:
    """Find one customer case by email, phone, or order ID."""
    identifier = identifier.strip()
    if not identifier:
        return None

    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT
                c.id AS customer_id,
                c.name,
                c.email,
                c.phone,
                c.tier,
                o.order_id,
                o.product_name,
                o.serial_number,
                o.purchase_date,
                o.delivery_date,
                o.order_status,
                o.payment_status,
                w.warranty_end_date,
                w.status AS warranty_status
            FROM customers c
            JOIN orders o ON o.customer_id = c.id
            LEFT JOIN warranties w ON w.order_id = o.order_id
            WHERE lower(c.email) = lower(?)
               OR c.phone = ?
               OR lower(o.order_id) = lower(?)
            ORDER BY o.delivery_date DESC
            LIMIT 1
            """,
            (identifier, identifier, identifier),
        ).fetchone()

        if row is None:
            return None

        case = dict(row)
        case["delivery_days_ago"] = days_since(case["delivery_date"])
        case["refund_window_status"] = (
            "inside_14_day_window" if case["delivery_days_ago"] <= 14 else "outside_14_day_window"
        )
        case["replacement_window_status"] = (
            "inside_30_day_window" if case["delivery_days_ago"] <= 30 else "outside_30_day_window"
        )
        case["tickets"] = get_tickets(case["customer_id"], case["order_id"], conn)
        case["email_drafts"] = get_email_drafts(case["customer_id"], case["order_id"], conn)
        case["audit_logs"] = get_audit_logs(case["customer_id"], case["order_id"], conn)
        return case


def create_ticket(
    customer_id: int,
    order_id: str,
    issue_type: str,
    summary: str,
    priority: str = "Medium",
    db_path: Path = DB_PATH,
) -> Dict:
    """Create a complaint/support ticket and return the inserted ticket."""
    with get_connection(db_path) as conn:
        ticket_id = next_ticket_id(conn)
        created_at = date.today().isoformat()
        conn.execute(
            """
            INSERT INTO tickets (
                ticket_id, customer_id, order_id, issue_type, status, priority,
                created_at, summary
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                customer_id,
                order_id,
                issue_type,
                "Open",
                priority,
                created_at,
                summary,
            ),
        )
        conn.commit()

        row = conn.execute(
            """
            SELECT ticket_id, issue_type, status, priority, created_at, summary
            FROM tickets
            WHERE ticket_id = ?
            """,
            (ticket_id,),
        ).fetchone()
        return dict(row)


def delete_ticket(ticket_id: str, db_path: Path = DB_PATH) -> bool:
    """Delete one ticket by ID. Returns True when a row was removed."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM tickets WHERE ticket_id = ?", (ticket_id,))
        conn.commit()
        return cursor.rowcount > 0


def create_email_draft(
    customer_id: int,
    order_id: str,
    recipient: str,
    subject: str,
    body: str,
    ticket_id: str = None,
    db_path: Path = DB_PATH,
) -> Dict:
    """Create an email draft for a customer/order."""
    with get_connection(db_path) as conn:
        draft_id = next_draft_id(conn)
        created_at = date.today().isoformat()
        conn.execute(
            """
            INSERT INTO email_drafts (
                draft_id, customer_id, order_id, ticket_id, recipient, subject,
                body, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft_id,
                customer_id,
                order_id,
                ticket_id,
                recipient,
                subject,
                body,
                "Draft",
                created_at,
            ),
        )
        conn.commit()

        row = conn.execute(
            """
            SELECT draft_id, ticket_id, recipient, subject, body, status, created_at
            FROM email_drafts
            WHERE draft_id = ?
            """,
            (draft_id,),
        ).fetchone()
        return dict(row)


def ensure_email_draft_for_ticket(
    ticket_id: str,
    customer_id: int,
    order_id: str,
    recipient: str,
    subject: str,
    body: str,
    db_path: Path = DB_PATH,
) -> Dict:
    """Return an existing draft for a ticket or create one."""
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT draft_id, ticket_id, recipient, subject, body, status, created_at
            FROM email_drafts
            WHERE ticket_id = ?
            ORDER BY draft_id DESC
            LIMIT 1
            """,
            (ticket_id,),
        ).fetchone()
        if row:
            return dict(row)

    return create_email_draft(
        customer_id=customer_id,
        order_id=order_id,
        ticket_id=ticket_id,
        recipient=recipient,
        subject=subject,
        body=body,
        db_path=db_path,
    )


def get_email_drafts(customer_id: int, order_id: str, conn: sqlite3.Connection) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT draft_id, ticket_id, recipient, subject, body, status, created_at
        FROM email_drafts
        WHERE customer_id = ? OR order_id = ?
        ORDER BY created_at DESC, draft_id DESC
        """,
        (customer_id, order_id),
    ).fetchall()
    return [dict(row) for row in rows]


def mark_email_draft_sent(draft_id: str, db_path: Path = DB_PATH) -> bool:
    """Mark an email draft as sent."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "UPDATE email_drafts SET status = 'Sent' WHERE draft_id = ?",
            (draft_id,),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_email_draft(draft_id: str, db_path: Path = DB_PATH) -> bool:
    """Delete one email draft."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM email_drafts WHERE draft_id = ?", (draft_id,))
        conn.commit()
        return cursor.rowcount > 0


def clear_support_activity(db_path: Path = DB_PATH) -> Dict:
    """Clear demo-created support activity from tickets, drafts, logs, and inspections."""
    with get_connection(db_path) as conn:
        deleted = {}
        for table in ("email_drafts", "tickets", "audit_logs", "damage_inspections"):
            cursor = conn.execute(f"DELETE FROM {table}")
            deleted[table] = cursor.rowcount
        conn.commit()
        return deleted


def log_action(
    action: str,
    detail: str,
    customer_id: int = None,
    order_id: str = None,
    reference_id: str = None,
    db_path: Path = DB_PATH,
) -> Dict:
    """Append an audit log row."""
    with get_connection(db_path) as conn:
        created_at = datetime.now().isoformat(timespec="seconds")
        cursor = conn.execute(
            """
            INSERT INTO audit_logs (
                customer_id, order_id, action, reference_id, detail, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (customer_id, order_id, action, reference_id, detail, created_at),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT customer_id, order_id, action, reference_id, detail, created_at
            FROM audit_logs
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)


def log_damage_inspection(
    report: Dict,
    customer_id: int = None,
    order_id: str = None,
    db_path: Path = DB_PATH,
) -> Dict:
    """Persist one damage inspection result for dashboard review."""
    with get_connection(db_path) as conn:
        created_at = datetime.now().isoformat(timespec="seconds")
        cursor = conn.execute(
            """
            INSERT INTO damage_inspections (
                customer_id, order_id, image_url, inspection_status, damage_detected,
                damage_type, severity, confidence, needs_human_review, recommendation,
                source, model, notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                customer_id,
                order_id,
                report.get("image_url", ""),
                report.get("inspection_status", "unknown"),
                1 if report.get("damage_detected") else 0,
                report.get("damage_type", "unknown"),
                report.get("severity", "unknown"),
                float(report.get("confidence", 0.0) or 0.0),
                1 if report.get("needs_human_review") else 0,
                report.get("recommendation", ""),
                report.get("source", "unknown"),
                report.get("model", "unknown"),
                report.get("notes", ""),
                created_at,
            ),
        )
        conn.commit()
        row = conn.execute(
            """
            SELECT *
            FROM damage_inspections
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        return dict(row)


def get_audit_logs(customer_id: int, order_id: str, conn: sqlite3.Connection) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT action, reference_id, detail, created_at
        FROM audit_logs
        WHERE customer_id = ? OR order_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 30
        """,
        (customer_id, order_id),
    ).fetchall()
    return [dict(row) for row in rows]


def get_dashboard_tickets(db_path: Path = DB_PATH) -> List[Dict]:
    """Return all support tickets with customer and order context."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                t.ticket_id,
                t.issue_type,
                t.status,
                t.priority,
                t.created_at,
                t.summary,
                c.name AS customer_name,
                c.email,
                o.order_id,
                o.product_name
            FROM tickets t
            JOIN customers c ON c.id = t.customer_id
            JOIN orders o ON o.order_id = t.order_id
            ORDER BY t.created_at DESC, t.ticket_id DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_damage_inspections(limit: int = 50, db_path: Path = DB_PATH) -> List[Dict]:
    """Return recent image inspections for the operations dashboard."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT
                d.id,
                d.customer_id,
                c.name AS customer_name,
                d.order_id,
                o.product_name,
                d.image_url,
                d.inspection_status,
                d.damage_detected,
                d.damage_type,
                d.severity,
                d.confidence,
                d.needs_human_review,
                d.recommendation,
                d.source,
                d.model,
                d.notes,
                d.created_at
            FROM damage_inspections d
            LEFT JOIN customers c ON c.id = d.customer_id
            LEFT JOIN orders o ON o.order_id = d.order_id
            ORDER BY d.created_at DESC, d.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]


def next_ticket_id(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        """
        SELECT ticket_id
        FROM tickets
        WHERE ticket_id LIKE 'TKT-%'
        ORDER BY CAST(substr(ticket_id, 5) AS INTEGER) DESC
        LIMIT 1
        """
    ).fetchone()

    if row is None:
        return "TKT-2001"

    current = int(row["ticket_id"].split("-", 1)[1])
    return f"TKT-{current + 1}"


def next_draft_id(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        """
        SELECT draft_id
        FROM email_drafts
        WHERE draft_id LIKE 'EML-%'
        ORDER BY CAST(substr(draft_id, 5) AS INTEGER) DESC
        LIMIT 1
        """
    ).fetchone()

    if row is None:
        return "EML-3001"

    current = int(row["draft_id"].split("-", 1)[1])
    return f"EML-{current + 1}"


def get_tickets(customer_id: int, order_id: str, conn: sqlite3.Connection) -> List[Dict]:
    rows = conn.execute(
        """
        SELECT ticket_id, issue_type, status, priority, created_at, summary
        FROM tickets
        WHERE customer_id = ? OR order_id = ?
        ORDER BY created_at DESC
        """,
        (customer_id, order_id),
    ).fetchall()
    return [dict(row) for row in rows]


def days_since(date_text: str) -> int:
    parsed = datetime.strptime(date_text, "%Y-%m-%d").date()
    return (date.today() - parsed).days


def format_case_context(case: Optional[Dict]) -> str:
    """Format selected DB fields for the support agent prompt."""
    if not case:
        return "No customer/order database context is selected."

    ticket_lines = []
    for ticket in case.get("tickets", []):
        ticket_lines.append(
            f"- {ticket['ticket_id']}: {ticket['issue_type']} | {ticket['status']} | "
            f"{ticket['priority']} | {ticket['summary']}"
        )
    tickets_text = "\n".join(ticket_lines) if ticket_lines else "No previous tickets."

    return f"""
Customer:
- Name: {case['name']}
- Email: {case['email']}
- Phone: {case['phone']}
- Tier: {case['tier']}

Order:
- Order ID: {case['order_id']}
- Product: {case['product_name']}
- Serial number: {case['serial_number']}
- Purchase date: {case['purchase_date']}
- Delivery date: {case['delivery_date']}
- Delivery age: {case['delivery_days_ago']} days
- Order status: {case['order_status']}
- Payment status: {case['payment_status']}

Warranty and windows:
- Warranty status: {case['warranty_status']}
- Warranty end date: {case['warranty_end_date']}
- Refund window status: {case['refund_window_status']}
- Replacement window status: {case['replacement_window_status']}

Tickets:
{tickets_text}
""".strip()
