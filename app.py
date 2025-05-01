# app.py
from flask import Flask, render_template, request, session, redirect, url_for
from urllib.parse import quote
import json
import pandas as pd
from auth import bp as auth_bp, init_db

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.register_blueprint(auth_bp)

# Initialize the database (users.db)
init_db()

# Load card data from CSV
card_df = pd.read_csv("./card_info/card_price.csv")

# Prepare card list for homepage
def load_cards():
    price_columns = [col for col in card_df.columns if col.startswith("p_")]
    latest_col = price_columns[-1]  # last date column (most recent)

    cards = []
    for i, row in card_df.iterrows():
        cards.append({
            "id": quote(str(i)),  # use row number as unique ID
            "name": row['card_name'],
            "image": row['img_src'],
            "rarity": row['rarity'],
            "price": row[latest_col]
        })
    return cards

@app.route("/")
def index():
    rarity_filter = request.args.get("rarity")
    name_filter = request.args.get("name")

    cards = load_cards()
    if rarity_filter:
        cards = [c for c in cards if c["rarity"] == rarity_filter]
    if name_filter:
        cards = [c for c in cards if name_filter.lower() in c["name"].lower()]

    all_rarities = sorted(set(str(c["rarity"]) for c in load_cards() if pd.notnull(c["rarity"])))

    return render_template("index.html", cards=cards, rarities=all_rarities)

@app.route("/card/<int:card_id>")
def card_detail(card_id):
    row = card_df.iloc[card_id]
    price_cols = [col for col in card_df.columns if col.startswith("p_")]
    latest_price_col = price_cols[-1]
    latest_price = row[latest_price_col]

    price_data = {
        "labels": [col.replace("p_", "") for col in price_cols],
        "prices": [row[col] for col in price_cols]
    }

    return render_template("card_detail.html",
                           card=row.to_dict(),
                           price_data=json.dumps(price_data),
                           latest_price=int(latest_price) if pd.notnull(latest_price) else None)

if __name__ == "__main__":
    app.run(debug=True)
