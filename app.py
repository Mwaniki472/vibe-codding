import os
import requests
import json
import re
import time
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
from db import get_db
from intasend import APIService

# Load local .env (ignored in production)
load_dotenv()

app = Flask(__name__)
CORS(app)

# ====== ENVIRONMENT VARIABLES ======
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
INTASEND_SECRET_KEY = os.getenv("INTASEND_SECRET_KEY")
INTASEND_PUBLISHABLE_KEY = os.getenv("INTASEND_PUBLISHABLE_KEY")
INTASEND_ENV = os.getenv("INTASEND_ENV", "sandbox")

# Early check for critical keys
if not HUGGINGFACE_API_KEY:
    raise Exception("Missing Hugging Face API key. Set HUGGINGFACE_API_KEY in your environment variables.")

if not INTASEND_SECRET_KEY:
    raise Exception("Missing IntaSend secret key. Set INTASEND_SECRET_KEY in your environment variables.")

# ====== Initialize IntaSend ======
service = APIService(
    token=INTASEND_SECRET_KEY,
    publishable_key=INTASEND_PUBLISHABLE_KEY,
    test=(INTASEND_ENV == "sandbox")
)

# ====== ROUTES ======
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/ping")
def ping():
    return jsonify({"ok": True})

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

@app.route("/api/generate", methods=["POST"])
def generate_flashcards():
    notes = request.json.get("notes")
    if not notes:
        return jsonify({"error": "No notes provided"}), 400

    api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-v0.1"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

    prompt = f"""From the following text, create exactly 3 high-quality flashcards with a clear question and detailed answer. 
Return ONLY a valid JSON array in this format: [{{"question": "text", "answer": "text"}}]
Text: {notes[:1500]}"""

    try:
        response = requests.post(
            api_url,
            headers=headers,
            json={"inputs": prompt, "parameters": {"max_new_tokens": 500, "temperature": 0.3, "return_full_text": False}},
            timeout=45
        )
        response.raise_for_status()
        result = response.json()

        # Parse JSON safely
        generated_text = result[0].get("generated_text", "")
        json_match = re.search(r'\[.*\]', generated_text, re.DOTALL)
        if not json_match:
            return jsonify({"error": "Failed to extract JSON from AI response"}), 500

        flashcards = json.loads(json_match.group(0))
        validated_flashcards = [{"question": c["question"], "answer": c["answer"]} for c in flashcards if "question" in c and "answer" in c]

        return jsonify({"flashcards": validated_flashcards[:3]})

    except Exception as e:
        return jsonify({"error": f"AI API error: {str(e)}"}), 500

@app.route("/api/pay", methods=["POST"])
def pay():
    payload = request.json
    phone_number = payload.get("phone_number")
    email = payload.get("email")
    amount = payload.get("amount")

    if not phone_number or not amount:
        return jsonify({"success": False, "error": "Missing phone number or amount"}), 400

    try:
        resp = service.collection.charge(phone_number=phone_number, email=email, amount=amount, currency="KES")
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO payments (amount, status, transaction_id, user_id) VALUES (%s, %s, %s, %s)",
            (amount, resp.get("state"), resp.get("invoice_id"), 1)
        )
        db.commit()
        db.close()
        return jsonify({"success": True, "checkout": {"invoice": resp.get("invoice_id")}}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
