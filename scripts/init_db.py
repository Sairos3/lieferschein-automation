import sqlite3
from pathlib import Path

DB_PATH = Path("data/app.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

schema = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS suppliers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS delivery_notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  supplier_id INTEGER NOT NULL,
  delivery_note_no TEXT NOT NULL,
  delivery_date TEXT NOT NULL,
  customer_no TEXT,
  order_no TEXT,
  subtotal REAL,
  vat REAL,
  total REAL,
  source_pdf TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(supplier_id, delivery_note_no, delivery_date),
  FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE IF NOT EXISTS delivery_note_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  delivery_note_id INTEGER NOT NULL,
  line_no INTEGER NOT NULL,
  article_no TEXT,
  description TEXT,
  quantity REAL NOT NULL,
  unit_price REAL,
  line_total REAL,
  FOREIGN KEY (delivery_note_id) REFERENCES delivery_notes(id)
);
"""

def main():
    with sqlite3.connect(DB_PATH) as con:
        con.executescript(schema)
    print(f"DB initialized at: {DB_PATH.resolve()}")

if __name__ == "__main__":
    main()