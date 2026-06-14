"""
services/history_service.py

Simple in-memory history store.
Stores a list of dicts — no database needed.

Each entry looks like:
{
    "id":        "abc123",
    "timestamp": "2025-05-04 14:32",
    "product":   "Python Bootcamp",
    "persona":   "Student",
    "data":      { ...full strategy JSON... }
}
"""

import uuid
from datetime import datetime

#Module-level list — lives as long as Flask server is running
_history: list[dict] = []

#Maximum entries to keep (prevents unbounded memory growth)
MAX_ENTRIES = 50


def save_result(product: str, persona: str, data: dict) -> str:
    """Save a generated strategy. Returns the new entry's ID."""
    entry = {
        "id":        str(uuid.uuid4())[:8],          
        "timestamp": datetime.now().strftime("%d %b %Y, %H:%M"),
        "product":   product,
        "persona":   persona,
        "data":      data,
    }
    _history.insert(0, entry)          
    if len(_history) > MAX_ENTRIES:    
        _history.pop()
    return entry["id"]


def get_all() -> list[dict]:
    """Return all history entries (newest first)."""
    return _history


def get_by_id(entry_id: str) -> dict | None:
    """Find a single entry by its short ID."""
    for entry in _history:
        if entry["id"] == entry_id:
            return entry
    return None


def clear_all() -> None:
    """Wipe the entire history."""
    _history.clear()
