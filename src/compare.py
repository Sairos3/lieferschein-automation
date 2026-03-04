import sqlite3
from typing import Dict, List, Any

def compute_stock_overview(con: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Returns rows per (supplier, order_no, article/description):
    expected, delivered, open.
    """
    # Expected from invoices
    expected = con.execute("""
        SELECT
          s.name AS supplier,
          s.tax_no AS supplier_tax_no,
          COALESCE(i.order_no,'') AS order_no,
          COALESCE(ii.article_no,'') AS article_no,
          COALESCE(ii.description,'') AS description,
          SUM(ii.qty_expected) AS qty_expected
        FROM invoice_items ii
        JOIN invoices i ON i.id = ii.invoice_id
        JOIN suppliers s ON s.id = i.supplier_id
        GROUP BY s.id, order_no, article_no, description
    """).fetchall()

    # Delivered from delivery notes
    delivered = con.execute("""
        SELECT
          s.name AS supplier,
          s.tax_no AS supplier_tax_no,
          COALESCE(d.order_no,'') AS order_no,
          COALESCE(di.article_no,'') AS article_no,
          COALESCE(di.description,'') AS description,
          SUM(di.quantity) AS qty_delivered
        FROM delivery_note_items di
        JOIN delivery_notes d ON d.id = di.delivery_note_id
        JOIN suppliers s ON s.id = d.supplier_id
        GROUP BY s.id, order_no, article_no, description
    """).fetchall()

    # Index delivered by key
    del_map = {}
    for r in delivered:
        key = (r["supplier"], r["supplier_tax_no"], r["order_no"], r["article_no"], r["description"])
        del_map[key] = float(r["qty_delivered"] or 0)

    out: List[Dict[str, Any]] = []
    for r in expected:
        key = (r["supplier"], r["supplier_tax_no"], r["order_no"], r["article_no"], r["description"])
        exp = float(r["qty_expected"] or 0)
        dlv = float(del_map.get(key, 0))
        open_qty = exp - dlv
        out.append({
            "supplier": r["supplier"],
            "supplier_tax_no": r["supplier_tax_no"],
            "order_no": r["order_no"],
            "article_no": r["article_no"],
            "description": r["description"],
            "expected": round(exp, 2),
            "delivered": round(dlv, 2),
            "open": round(open_qty, 2),
            "status": "OPEN" if open_qty > 0.0001 else "COMPLETE",
        })
    return out


def compute_invoice_statuses(con: sqlite3.Connection) -> Dict[int, str]:
    """
    Invoice is OPEN if any item still open.
    """
    # Build delivered per supplier/order/article/desc
    delivered = con.execute("""
        SELECT
          d.supplier_id,
          COALESCE(d.order_no,'') AS order_no,
          COALESCE(di.article_no,'') AS article_no,
          COALESCE(di.description,'') AS description,
          SUM(di.quantity) AS qty_delivered
        FROM delivery_note_items di
        JOIN delivery_notes d ON d.id = di.delivery_note_id
        GROUP BY d.supplier_id, order_no, article_no, description
    """).fetchall()

    del_map = {}
    for r in delivered:
        del_map[(r["supplier_id"], r["order_no"], r["article_no"], r["description"])] = float(r["qty_delivered"] or 0)

    invoices = con.execute("""
        SELECT i.id AS invoice_id, i.supplier_id, COALESCE(i.order_no,'') AS order_no
        FROM invoices i
    """).fetchall()

    status = {int(r["invoice_id"]): "COMPLETE" for r in invoices}

    items = con.execute("""
        SELECT ii.invoice_id, i.supplier_id, COALESCE(i.order_no,'') AS order_no,
               COALESCE(ii.article_no,'') AS article_no,
               COALESCE(ii.description,'') AS description,
               ii.qty_expected
        FROM invoice_items ii
        JOIN invoices i ON i.id = ii.invoice_id
    """).fetchall()

    for it in items:
        key = (it["supplier_id"], it["order_no"], it["article_no"], it["description"])
        dlv = float(del_map.get(key, 0))
        exp = float(it["qty_expected"] or 0)
        if exp - dlv > 0.0001:
            status[int(it["invoice_id"])] = "OPEN"

    return status