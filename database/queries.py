from database.db import get_db


def get_user_by_id(user_id):
    from datetime import datetime
    db = get_db()
    row = db.execute(
        "SELECT id, name, email, password_hash, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    db.close()
    if row is None:
        return None
    created_at = datetime.strptime(row["created_at"][:10], "%Y-%m-%d")
    member_since = created_at.strftime("%B %Y")
    words = row["name"].split()
    initials = "".join(w[0].upper() for w in words)[:2]
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": member_since,
        "initials": initials,
    }


def get_summary_stats(user_id):
    db = get_db()
    try:
        row = db.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        total = row["total"]
        count = row["cnt"]

        top_row = db.execute(
            "SELECT category FROM expenses WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        top_category = top_row["category"] if top_row else "—"
    finally:
        db.close()

    return {
        "total_spent": f"₹{total:,.2f}",
        "transaction_count": count,
        "top_category": top_category,
    }


def get_recent_transactions(user_id, limit=10):
    db = get_db()
    rows = db.execute(
        "SELECT id, amount, category, date, description "
        "FROM expenses "
        "WHERE user_id = ? "
        "ORDER BY date DESC, id DESC "
        "LIMIT ?",
        (user_id, limit),
    ).fetchall()
    db.close()
    return [
        {
            "date": row["date"],
            "description": row["description"] if row["description"] is not None else "",
            "category": row["category"],
            "amount": f"₹{row['amount']:,.2f}",
        }
        for row in rows
    ]


def get_category_breakdown(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC",
        (user_id,),
    ).fetchall()
    db.close()
    if not rows:
        return []
    grand_total = sum(row["total"] for row in rows)
    raw = [row["total"] / grand_total * 100 for row in rows]
    int_pcts = [int(p) for p in raw]
    remainder = 100 - sum(int_pcts)
    int_pcts[0] += remainder
    return [
        {
            "name": rows[i]["category"],
            "amount": f"₹{rows[i]['total']:,.2f}",
            "percent": int_pcts[i],
        }
        for i in range(len(rows))
    ]
