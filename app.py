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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rifas (
            id SERIAL PRIMARY KEY,
            titulo TEXT NOT NULL,
            creada TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    cur.execute("ALTER TABLE loteria ADD COLUMN IF NOT EXISTS rifa_id INTEGER")
    # Migración: los números que ya existían pasan a "Rifa 1"
    cur.execute("SELECT COUNT(*) FROM rifas")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO rifas (titulo) VALUES ('Rifa 1') RETURNING id")
        primera = cur.fetchone()[0]
    else:
        cur.execute("SELECT MIN(id) FROM rifas")
        primera = cur.fetchone()[0]
    cur.execute("UPDATE loteria SET rifa_id = %s WHERE rifa_id IS NULL", (primera,))
    cur.execute("ALTER TABLE loteria ALTER COLUMN rifa_id SET NOT NULL")
    # La llave primaria pasa de (numero) a (rifa_id, numero)
    cur.execute("""
        SELECT COUNT(*) FROM information_schema.key_column_usage
        WHERE table_name = 'loteria' AND constraint_name = 'loteria_pkey'
          AND column_name = 'rifa_id'
    """)
    if cur.fetchone()[0] == 0:
        cur.execute("ALTER TABLE loteria DROP CONSTRAINT IF EXISTS loteria_pkey")
        cur.execute("ALTER TABLE loteria ADD PRIMARY KEY (rifa_id, numero)")
    conn.commit()
    cur.close()
    conn.close()


def listar_rifas():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.id, r.titulo, r.creada, COUNT(l.numero)
        FROM rifas r LEFT JOIN loteria l ON l.rifa_id = r.id
        GROUP BY r.id ORDER BY r.id DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {"id": i, "titulo": t, "creada": c.isoformat(), "apartados": n}
        for i, t, c, n in rows
    ]


def load_data(rifa_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT numero, data FROM loteria WHERE rifa_id = %s", (rifa_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {str(num): d for num, d in rows}


def asignar_numero(rifa_id, numero, d):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO loteria (rifa_id, numero, data) VALUES (%s, %s, %s)
           ON CONFLICT (rifa_id, numero) DO UPDATE SET data = EXCLUDED.data""",
        (rifa_id, int(numero), psycopg2.extras.Json(d))
    )
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


def check_pass(body):
    return (body or {}).get("password", "") == RESET_PASSWORD


@app.route("/api/rifas", methods=["GET"])
def get_rifas():
    try:
        return jsonify(listar_rifas())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/rifas", methods=["POST"])
def crear_rifa():
    titulo = ((request.json or {}).get("titulo") or "").strip()
    if not titulo:
        return jsonify({"ok": False, "error": "El título es obligatorio"}), 400
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO rifas (titulo) VALUES (%s) RETURNING id", (titulo[:80],))
        nuevo = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True, "id": nuevo})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/rifas/<int:rifa_id>", methods=["PATCH"])
def renombrar_rifa(rifa_id):
    titulo = ((request.json or {}).get("titulo") or "").strip()
    if not titulo:
        return jsonify({"ok": False, "error": "El título es obligatorio"}), 400
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE rifas SET titulo = %s WHERE id = %s", (titulo[:80], rifa_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/rifas/<int:rifa_id>/loteria", methods=["GET"])
def get_loteria(rifa_id):
    try:
        return jsonify(load_data(rifa_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/rifas/<int:rifa_id>/loteria/<int:numero>", methods=["PUT"])
def apartar_numero(rifa_id, numero):
    if not 1 <= numero <= 99:
        return jsonify({"ok": False, "error": "Número fuera de rango"}), 400
    try:
        asignar_numero(rifa_id, numero, request.json)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/rifas/<int:rifa_id>/loteria/<int:numero>/liberar", methods=["POST"])
def liberar_numero(rifa_id, numero):
    if not check_pass(request.json):
        return jsonify({"ok": False, "error": "Contraseña incorrecta"}), 403
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM loteria WHERE rifa_id = %s AND numero = %s", (rifa_id, numero))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/rifas/<int:rifa_id>/loteria/reset", methods=["POST"])
def reset_loteria(rifa_id):
    if not check_pass(request.json):
        return jsonify({"ok": False, "error": "Contraseña incorrecta"}), 403
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM loteria WHERE rifa_id = %s", (rifa_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=False)
