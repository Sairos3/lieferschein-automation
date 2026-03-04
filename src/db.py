import sqlite3
from pathlib import Path
from typing import Optional, Any, Dict, List


def get_con(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    return con


def upsert_supplier(con: sqlite3.Connection, name: str, tax_no: str | None) -> int:
    name = (name or "UNKNOWN").strip()
    tax_no = (tax_no or "").strip()

    con.execute(
        "INSERT OR IGNORE INTO suppliers(name, tax_no) VALUES (?, ?)",
        (name, tax_no),
    )
    row = con.execute(
        "SELECT id FROM suppliers WHERE name = ? AND COALESCE(tax_no,'') = ?",
        (name, tax_no),
    ).fetchone()
    return int(row["id"])


def delivery_note_exists(con: sqlite3.Connection, supplier_id: int, delivery_date: str | None,
                         customer_no: str | None, order_no: str | None, tax_no: str | None) -> bool:
    row = con.execute(
        """
        SELECT 1
        FROM delivery_notes
        WHERE supplier_id = ?
          AND delivery_date = ?
          AND COALESCE(customer_no, '') = COALESCE(?, '')
          AND COALESCE(order_no, '') = COALESCE(?, '')
          AND COALESCE(tax_no, '') = COALESCE(?, '')
        LIMIT 1
        """,
        (supplier_id, delivery_date, customer_no, order_no, tax_no),
    ).fetchone()
    return row is not None


def insert_delivery_note(con, data, source_pdf: str, force: bool = False) -> int:
    supplier_id = upsert_supplier(con, data.get("supplier"), data.get("tax_no"))

    # Duplicate protection using business keys (only if not forced)
    if not force:
        if delivery_note_exists(
            con,
            supplier_id,
            data.get("delivery_date"),
            data.get("customer_no"),
            data.get("order_no"),
            data.get("tax_no"),
        ):
            raise ValueError(
                "Duplicate delivery note detected (same supplier + date + customer + order + tax_no)."
            )

    cur = con.execute(
        """
        INSERT INTO delivery_notes (
          supplier_id, delivery_note_no, delivery_date, customer_no, order_no,
          tax_no, subtotal, vat, total, source_pdf
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            supplier_id,
            data.get("delivery_note_no"),
            data.get("delivery_date"),
            data.get("customer_no"),
            data.get("order_no"),
            data.get("tax_no") or "",
            data.get("subtotal"),
            data.get("vat"),
            data.get("total"),
            source_pdf,
        ),
    )
    delivery_note_id = int(cur.lastrowid)

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