import os, requests, json, re
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from db import get_db
from intasend import APIService
import time

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return render_template("index.html")

# === IntaSend Config ===
INTASEND_SECRET_KEY = os.environ.get("INTASEND_SECRET_KEY")
INTASEND_PUBLISHABLE_KEY = os.environ.get("INTASEND_PUBLISHABLE_KEY")
INTASEND_ENV = os.environ.get("INTASEND_ENV", "sandbox")

service = APIService(
    token=INTASEND_SECRET_KEY,
    publishable_key=INTASEND_PUBLISHABLE_KEY,
    test=(INTASEND_ENV == "sandbox")
)

@app.route("/api/ping")
def ping():
    return jsonify({"ok": True})

# === Flashcard Routes ===
@app.route("/api/flashcards", methods=["GET"])
def get_flashcards():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM flashcards ORDER BY created_at DESC")
    data = cur.fetchall()
    db.close()
    return jsonify(data)

@app.route("/api/flashcards", methods=["POST"])
def save_flashcard():
    payload = request.json
    question = payload.get("question")
    answer = payload.get("answer")

    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO flashcards (question, answer) VALUES (%s, %s)", (question, answer))
    db.commit()
    db.close()
    return jsonify({"ok": True})

# === AI Flashcard Generation ===
@app.route("/api/generate", methods=["POST"])
def generate_flashcards():
    notes = request.json.get("notes")
    if not notes:
        return jsonify({"error": "No notes provided"}), 400

    api_key = os.environ.get("HUGGINGFACE_API_KEY")
    if not api_key:
        return jsonify({"error": "Missing Hugging Face API key"}), 500

    api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-v0.1"
    headers = {"Authorization": f"Bearer {api_key}"}
    prompt = f"""From the following text, create exactly 3 flashcards as JSON: 
    [{{"question": "...", "answer": "..."}}]
    Text: {notes[:1500]}"""

    try:
        response = requests.post(api_url, headers=headers, json={"inputs": prompt}, timeout=45)
        response.raise_for_status()
        result = response.json()
        generated_text = result[0].get("generated_text", "")
        json_match = re.search(r'\[.*\]', generated_text, re.DOTALL)
        if not json_match:
            return jsonify({"error": "Could not extract JSON", "debug": generated_text[:500]}), 500
        flashcards = json.loads(json_match.group(0))
        return jsonify({"flashcards": flashcards[:3]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Payment Route ===
@app.route("/api/pay", methods=["POST"])
def pay():
    payload = request.json
    phone_number = payload.get("phone_number")
    email = payload.get("email")
    amount = payload.get("amount")

    if not phone_number or not amount:
        return jsonify({"success": False, "error": "Missing phone or amount"}), 400

    try:
        resp = service.collection.charge(
            phone_number=phone_number,
            email=email,
            amount=amount,
            currency="KES"
        )
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO payments (amount, status, transaction_id, user_id) VALUES (%s,%s,%s,%s)",
            (amount, resp.get("state"), resp.get("invoice_id"), 1)
        )
        db.commit()
        db.close()
        return jsonify({"success": True, "checkout": {"invoice": resp.get("invoice_id")}}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
