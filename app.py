import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, get_db, get_user_by_email, init_db, seed_db

app = Flask(__name__)
app.secret_key = "dev-secret-key"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([name, email, password, confirm_password]):
            flash("All fields are required.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        try:
            create_user(name, email, password)
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
            return render_template("register.html")

        flash("Account created! Please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = get_user_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("profile"))

    return render_template("login.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": "Alex Johnson",
        "email": "alex@example.com",
        "member_since": "January 2025",
        "initials": "AJ",
    }
    stats = {
        "total_spent": "₹24,850",
        "transaction_count": 12,
        "top_category": "Food",
    }
    transactions = [
        {"date": "2025-05-10", "description": "Grocery run", "category": "Food", "amount": "₹1,240"},
        {"date": "2025-05-08", "description": "Metro card recharge", "category": "Transport", "amount": "₹500"},
        {"date": "2025-05-06", "description": "Electricity bill", "category": "Bills", "amount": "₹3,200"},
        {"date": "2025-05-03", "description": "Doctor consultation", "category": "Health", "amount": "₹800"},
        {"date": "2025-04-29", "description": "Netflix subscription", "category": "Entertainment", "amount": "₹649"},
        {"date": "2025-04-25", "description": "Shoes", "category": "Shopping", "amount": "₹2,499"},
    ]
    categories = [
        {"name": "Food",          "amount": "₹8,400",  "percent": 34},
        {"name": "Bills",         "amount": "₹6,200",  "percent": 25},
        {"name": "Transport",     "amount": "₹4,100",  "percent": 16},
        {"name": "Health",        "amount": "₹3,800",  "percent": 15},
        {"name": "Entertainment", "amount": "₹2,350",  "percent": 10},
    ]
    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
