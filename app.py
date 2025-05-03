from flask import Flask, render_template, request, session, redirect, url_for, flash
from urllib.parse import quote
import json
import pandas as pd
import sqlite3
from datetime import datetime
from auth import bp as auth_bp, init_db, DB_PATH

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.register_blueprint(auth_bp)

# Initialize the database
init_db()

# Load card data
card_df = pd.read_csv("./card_info/card_price.csv")

def load_cards():
    price_columns = [col for col in card_df.columns if col.startswith("p_")]
    latest_col = price_columns[-1]

    cards = []
    for i, row in card_df.iterrows():
        raw_price = row[latest_col]
        try:
            clean_price = int(raw_price)
        except (ValueError, TypeError):
            clean_price = 0  # default for bad/missing values

        cards.append({
            "id": quote(str(i)),
            "name": row["card_name"],
            "image": row["img_src"],
            "rarity": row["rarity"],
            "price": clean_price
        })
    return cards

@app.route("/")
def index():
    rarity_filter = request.args.get("rarity")
    name_filter = request.args.get("name")
    sort_order = request.args.get("sort")

    raw_cards = load_cards()
    cards = raw_cards[:]  # clone before filtering

    if rarity_filter:
        cards = [c for c in cards if c["rarity"] == rarity_filter]
    if name_filter:
        cards = [c for c in cards if name_filter.lower() in c["name"].lower()]

    if sort_order == "asc":
        cards.sort(key=lambda c: c["price"] or 0)
    elif sort_order == "desc":
        cards.sort(key=lambda c: -(c["price"] or 0))

    all_rarities = sorted(set(str(c["rarity"]) for c in raw_cards if pd.notnull(c["rarity"])))
    return render_template("index.html", cards=cards, rarities=all_rarities)


@app.route("/card/<int:card_id>", methods=["GET", "POST"])
def card_detail(card_id):
    row = card_df.iloc[card_id]
    price_cols = [col for col in card_df.columns if col.startswith("p_")]
    latest_price_col = price_cols[-1]
    latest_price = row[latest_price_col]

    price_data = {
        "labels": [col.replace("p_", "") for col in price_cols],
        "prices": [row[col] for col in price_cols]
    }

    if request.method == "POST":
        if "user_id" not in session:
            flash("You must be logged in to save cards.", "error")
            return redirect(url_for("auth.login"))

        purchase_price = float(request.form["purchase_price"])
        purchase_date = datetime.now().strftime('%Y-%m-%d')

        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO user_cards (user_id, card_id, purchase_price, purchase_date)
                VALUES (?, ?, ?, ?)
            """, (session["user_id"], card_id, purchase_price, purchase_date))
            conn.commit()

        flash("Card saved to your collection!", "success")
        return redirect(url_for("card_detail", card_id=card_id))

    return render_template("card_detail.html",
                           card=row.to_dict(),
                           price_data=json.dumps(price_data),
                           latest_price=int(latest_price) if pd.notnull(latest_price) else None)

@app.route("/save-card", methods=["POST"])
def save_card():
    if "user_id" not in session:
        flash("You must be logged in to save cards.", "error")
        return redirect(url_for("auth.login"))

    card_id = int(request.form["card_id"])
    purchase_price = float(request.form["purchase_price"])
    purchase_date = datetime.now().strftime('%Y-%m-%d')

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO user_cards (user_id, card_id, purchase_price, purchase_date)
            VALUES (?, ?, ?, ?)
        """, (session["user_id"], card_id, purchase_price, purchase_date))
        conn.commit()

    flash("Card saved to your collection!", "success")
    return redirect(url_for("index"))

@app.route("/my-collection")
def my_collection():
    if "user_id" not in session:
        flash("Please log in to view your collection.", "error")
        return redirect(url_for("auth.login"))

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, card_id, purchase_price, purchase_date FROM user_cards WHERE user_id = ?", (session["user_id"],))
        saved_cards = c.fetchall()

    grouped_by_card = {}

    for entry_id, card_id, purchase_price, purchase_date in saved_cards:
        row = card_df.iloc[card_id]
        price_cols = [col for col in card_df.columns if col.startswith("p_")]
        latest_price = row[price_cols[-1]]
        profit = latest_price - purchase_price if pd.notnull(latest_price) else None

        if card_id not in grouped_by_card:
            grouped_by_card[card_id] = {
                "card_id": card_id,
                "name": row["card_name"],
                "image": row["img_src"],
                "rarity": row["rarity"],
                "latest_price": latest_price,
                "purchases": []
            }

        # check if there's already a group with same purchase_price
        found = False
        for group in grouped_by_card[card_id]["purchases"]:
            if group["purchase_price"] == purchase_price:
                group["quantity"] += 1
                found = True
                break

        if not found:
            grouped_by_card[card_id]["purchases"].append({
                "entry_id": entry_id,
                "purchase_price": purchase_price,
                "quantity": 1,
                "profit": profit,
                "purchase_date": purchase_date
            })

    return render_template("my_collection.html", cards=list(grouped_by_card.values()))

@app.route("/delete-card/<int:entry_id>", methods=["POST"])
def delete_card(entry_id):
    if "user_id" not in session:
        flash("You must be logged in to delete cards.", "error")
        return redirect(url_for("auth.login"))

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM user_cards WHERE id = ? AND user_id = ?", (entry_id, session["user_id"]))
        conn.commit()

    flash("Card removed from your collection.", "info")
    return redirect(url_for("my_collection"))

if __name__ == "__main__":
    app.run(debug=True)
