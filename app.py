from flask import Flask, jsonify

app = Flask(__name__)

if __name__ == '__main__':
    app.run(debug=True, port=8080)  # Runs on http://localhost:5000