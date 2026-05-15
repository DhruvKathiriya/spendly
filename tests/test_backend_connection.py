import sqlite3

import pytest

import database.db as db_module
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)
from app import app as flask_app

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    description TEXT,
    created_at  TEXT    DEFAULT (datetime('now'))
);
"""

SEED_EXPENSES = [
    (450.00,  "Food",          "2026-04-01", "Groceries from D-Mart"),
    (120.00,  "Transport",     "2026-04-02", "Metro card recharge"),
    (1200.00, "Bills",         "2026-04-03", "Electricity bill"),
    (350.00,  "Health",        "2026-04-05", "Pharmacy — vitamins"),
    (500.00,  "Entertainment", "2026-04-06", "Movie tickets"),
    (800.00,  "Shopping",      "2026-04-07", "New earphones"),
    (200.00,  "Other",         "2026-04-08", "Miscellaneous"),
    (180.00,  "Food",          "2026-04-08", "Lunch with colleagues"),
]


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return db_path


def _add_user(db_path, name, email, created_at="2026-01-15 10:00:00"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.execute(
        "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (name, email, "fakehash", created_at),
    )
    uid = cur.lastrowid
    conn.commit()
    conn.close()
    return uid


def _add_expenses(db_path, user_id):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [(user_id, amt, cat, dt, desc) for amt, cat, dt, desc in SEED_EXPENSES],
    )
    conn.commit()
    conn.close()


# ------------------------------------------------------------------ #
# get_user_by_id                                                       #
# ------------------------------------------------------------------ #

def test_get_user_by_id_valid(temp_db):
    uid = _add_user(temp_db, "Demo User", "demo@spendly.com", "2026-01-15 10:00:00")
    result = get_user_by_id(uid)
    assert result is not None
    assert result["name"] == "Demo User"
    assert result["email"] == "demo@spendly.com"
    assert result["member_since"] == "January 2026"
    assert result["initials"] == "DU"


def test_get_user_by_id_nonexistent(temp_db):
    assert get_user_by_id(9999) is None


# ------------------------------------------------------------------ #
# get_summary_stats                                                    #
# ------------------------------------------------------------------ #

def test_get_summary_stats_with_expenses(temp_db):
    uid = _add_user(temp_db, "Demo User", "demo@spendly.com")
    _add_expenses(temp_db, uid)
    result = get_summary_stats(uid)
    assert result["total_spent"] == "₹3,800.00"
    assert result["transaction_count"] == 8
    assert result["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(temp_db):
    uid = _add_user(temp_db, "Empty User", "empty@example.com")
    assert get_summary_stats(uid) == {
        "total_spent": "₹0.00",
        "transaction_count": 0,
        "top_category": "—",
    }


# ------------------------------------------------------------------ #
# get_recent_transactions                                              #
# ------------------------------------------------------------------ #

def test_get_recent_transactions_with_expenses(temp_db):
    uid = _add_user(temp_db, "Demo User", "demo@spendly.com")
    _add_expenses(temp_db, uid)
    result = get_recent_transactions(uid)
    assert len(result) == 8
    dates = [txn["date"] for txn in result]
    assert dates == sorted(dates, reverse=True)
    for txn in result:
        assert "date" in txn
        assert "description" in txn
        assert "category" in txn
        assert txn["amount"].startswith("₹")


def test_get_recent_transactions_no_expenses(temp_db):
    uid = _add_user(temp_db, "Empty User", "empty@example.com")
    assert get_recent_transactions(uid) == []


# ------------------------------------------------------------------ #
# get_category_breakdown                                               #
# ------------------------------------------------------------------ #

def test_get_category_breakdown_with_expenses(temp_db):
    uid = _add_user(temp_db, "Demo User", "demo@spendly.com")
    _add_expenses(temp_db, uid)
    result = get_category_breakdown(uid)
    assert len(result) == 7
    assert result[0]["name"] == "Bills"
    assert result[0]["amount"] == "₹1,200.00"
    for cat in result:
        assert "name" in cat
        assert "amount" in cat
        assert isinstance(cat["percent"], int)
    assert sum(cat["percent"] for cat in result) == 100


def test_get_category_breakdown_no_expenses(temp_db):
    uid = _add_user(temp_db, "Empty User", "empty@example.com")
    assert get_category_breakdown(uid) == []


# ------------------------------------------------------------------ #
# Route: GET /profile                                                  #
# ------------------------------------------------------------------ #

@pytest.fixture()
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def test_profile_unauthenticated(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    response = client.get("/profile")
    assert response.status_code == 200
    html = response.data.decode()
    assert "Demo User" in html
    assert "demo@spendly.com" in html
    assert "₹" in html
    assert "₹3,800.00" in html
    assert "Bills" in html


def test_profile_transaction_order(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    response = client.get("/profile")
    html = response.data.decode()
    pos_apr8 = html.index("2026-04-08")
    pos_apr1 = html.index("2026-04-01")
    assert pos_apr8 < pos_apr1


def test_profile_category_breakdown_count(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    response = client.get("/profile")
    html = response.data.decode()
    assert html.count("cat-row") == 7
