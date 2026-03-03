import sqlite3
from pathlib import Path
from typing import Optional, Any, Dict, List


def get_con(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def upsert_supplier(con: sqlite3.Connection, name: str) -> int:
    con.execute("INSERT OR IGNORE INTO suppliers(name) VALUES (?)", (name,))
    row = con.execute("SELECT id FROM suppliers WHERE name = ?", (name,)).fetchone()
    return int(row["id"])


def delivery_note_exists(con, supplier_id: int, delivery_note_no: str, delivery_date: str) -> bool:
    row = con.execute(
        """
        SELECT 1
        FROM delivery_notes
        WHERE supplier_id = ? AND delivery_note_no = ? AND delivery_date = ?
        """,
        (supplier_id, delivery_note_no, delivery_date),
    ).fetchone()
    return row is not None


def insert_delivery_note(con: sqlite3.Connection, data: Dict[str, Any], source_pdf: str) -> int:
    supplier_id = upsert_supplier(con, data["supplier"] or "UNKNOWN")

    # duplicate protection
    dn_no = data.get("delivery_note_no")
    dn_date = data.get("delivery_date")

    if dn_no and dn_date:
        if delivery_note_exists(con, supplier_id, dn_no, dn_date):
            raise ValueError("Duplicate delivery note detected (same supplier + number + date).")

    cur = con.execute(
        """
        INSERT INTO delivery_notes (
          supplier_id, delivery_note_no, delivery_date, customer_no, order_no,
          subtotal, vat, total, source_pdf
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            supplier_id,
            data.get("delivery_note_no"),
            data.get("delivery_date"),
            data.get("customer_no"),
            data.get("order_no"),
            data.get("subtotal"),
            data.get("vat"),
            data.get("total"),
            source_pdf,
        ),
    )
    delivery_note_id = int(cur.lastrowid)

    # items
    for item in data.get("items", []):
        con.execute(
            """
            INSERT INTO delivery_note_items (
              delivery_note_id, line_no, article_no, description, quantity, unit_price, line_total
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                delivery_note_id,
                item.line_no,
                item.article_no,
                item.description,
                item.quantity,
                item.unit_price,
                item.line_total,
            ),
        )

    return delivery_note_id