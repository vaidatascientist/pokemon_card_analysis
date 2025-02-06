from flask import Flask, request, jsonify, render_template
import pandas as pd

app = Flask(__name__)

# Load the dataset
df = pd.read_csv("./card_info/card_price.csv")

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get("q", "").strip().lower()
    if not query:
        return jsonify([])
    
    # Filter cards by name containing query (case-insensitive)
    matches = df[df["card_name"].str.lower().str.contains(query, na=False)]
    
    # Convert results to JSON format
    results = matches.head(10).to_dict(orient="records")
    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)
