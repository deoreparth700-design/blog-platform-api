from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
app.json.sort_keys = False


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "message": "Blog Platform API is running",
        }
    ), 200
