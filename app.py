from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os

app = Flask(__name__, static_folder="static")
CORS(app)

BASE_URL = os.environ.get("N8N_URL", "")
HEADERS = {"Content-Type": "application/json", "ngrok-skip-browser-warning": "true"}

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

if __name__ == "__main__":
    app.run(debug=False)
