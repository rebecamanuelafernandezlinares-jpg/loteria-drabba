from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import json
import psycopg2
import psycopg2.extras

app = Flask(__name__, static_folder="static")
CORS(app)

BASE_URL = os.environ.get("N8N_URL", "")
HEADERS = {"Content-Type": "application/json", "ngrok-skip-browser-warning": "true"}
DATABASE_URL = os.environ.get("DATABASE_URL", "")
RESET_PASSWORD = os.environ.get("RESET_PASSWORD", "0000")


def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS loteria (
            numero INTEGER PRIMARY KEY,
            data JSONB NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def load_data():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT numero, data FROM loteria")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {str(num): d for num, d in rows}


def save_data(data):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM loteria")
    for num, d in data.items():
        cur.execute(
            "INSERT INTO loteria (numero, data) VALUES (%s, %s)",
            (int(num), psycopg2.extras.Json(d))
        )
    conn.commit()
    cur.close()
    conn.close()


def reset_data():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM loteria")
    conn.commit()
    cur.close()
    conn.close()


try:
    init_db()
except Exception as e:
    print("Error inicializando DB:", e)


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
    try:
        return jsonify(load_data())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/loteria", methods=["POST"])
def save_loteria():
    try:
        data = request.json
        save_data(data)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/loteria/reset", methods=["POST"])
def reset_loteria():
    password = request.json.get("password", "")
    if password != RESET_PASSWORD:
        return jsonify({"ok": False, "error": "Contraseña incorrecta"}), 403
    try:
        reset_data()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False)
