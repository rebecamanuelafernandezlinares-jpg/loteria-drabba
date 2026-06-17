from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import json

app = Flask(__name__, static_folder="static")
CORS(app)

BASE_URL = os.environ.get("N8N_URL", "")
HEADERS = {"Content-Type": "application/json", "ngrok-skip-browser-warning": "true"}

DATA_FILE = "loteria_data.json"
RESET_PASSWORD = os.environ.get("RESET_PASSWORD", "0000")

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/webhook/consulta-cliente-loteria")
def buscar_cliente():
    customer_id = request.args.get("customer_id", "")
    r = requests.get(
        f"{BASE_URL}/webhook/consulta-cliente-loteria",
        params={"customer_id": customer_id},
        headers=HEADERS
    )
    try:
        return jsonify(r.json()), r.status_code
    except Exception:
        return jsonify({"error": "Respuesta inválida", "raw": r.text[:300]}), 502

@app.route("/api/loteria", methods=["GET"])
def get_loteria():
    return jsonify(load_data())

@app.route("/api/loteria", methods=["POST"])
def save_loteria():
    data = request.json
    save_data(data)
    return jsonify({"ok": True})

@app.route("/api/loteria/reset", methods=["POST"])
def reset_loteria():
    password = request.json.get("password", "")
    if password != RESET_PASSWORD:
        return jsonify({"ok": False, "error": "Contraseña incorrecta"}), 403
    save_data({})
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(debug=False)
