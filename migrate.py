"""
migrate.py — Run this ONCE to update your existing database.
Adds new columns without deleting any existing data.

Usage:
    python migrate.py
"""

import sqlite3
import os

DB_PATH = "salesai.db"

if not os.path.exists(DB_PATH):
    print("No salesai.db found — it will be created fresh when you run app.py")
    exit(0)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()


def add_column(table, column, definition):
    """Add a column only if it doesn't already exist."""
    cursor.execute(f"PRAGMA table_info({table})")
    existing = [row[1] for row in cursor.fetchall()]
    if column not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"  ✅ Added {table}.{column}")
    else:
        print(f"  ⏭  {table}.{column} already exists")


print("=== Migrating users table ===")
add_column("users", "oauth_provider", "VARCHAR(30)")
add_column("users", "oauth_id",       "VARCHAR(120)")
add_column("users", "avatar_url",     "VARCHAR(300)")

print()
print("=== Migrating campaigns table ===")
add_column("campaigns", "user_id",          "INTEGER REFERENCES users(id)")
add_column("campaigns", "execution_status", "VARCHAR(30) DEFAULT 'draft'")

conn.commit()
conn.close()

print()
print("✅ Migration complete — run: python app.py")
