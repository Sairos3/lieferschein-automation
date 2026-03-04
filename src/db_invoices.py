import sqlite3
from typing import Any, Dict
from src.db import upsert_supplier

def insert_invoice(con: sqlite3.Connection, data: Dict[str, Any], source_pdf: str) -> int:
    supplier_id = upsert_supplier(con, data.get("supplier"), data.get("tax_no"))

    cur = con.execute(
        """
        INSERT INTO invoices (
          supplier_id, invoice_no, invoice_date, order_no, customer_no, source_pdf
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            supplier_id,
            data.get("invoice_no"),
            data.get("invoice_date"),
            data.get("order_no"),
            data.get("customer_no"),
            source_pdf,
        ),
    )
    invoice_id = int(cur.lastrowid)

    for item in data.get("items", []):
        con.execute(
            """
            INSERT INTO invoice_items (
              invoice_id, line_no, article_no, description, qty_expected
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                invoice_id,
                item["line_no"],
                item.get("article_no"),
                item.get("description"),
                float(item["qty_expected"]),
            ),
        )

    return invoice_id