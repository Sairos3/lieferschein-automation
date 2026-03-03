import sqlite3
from pathlib import Path

db_path = Path("data/app.db")

print("Checking DB at:", db_path.resolve())

con = sqlite3.connect(db_path)

tables = con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
).fetchall()

print("Tables found:")
for t in tables:
    print("-", t[0])