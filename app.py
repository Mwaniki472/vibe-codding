import os, requests, json, re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from db import get_db
from intasend import APIService
from flask import render_template
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return render_template("index.html")

# === IntaSend Config ===
INTASEND_SECRET_KEY = os.getenv("INTASEND_SECRET_KEY")
INTASEND_PUBLISHABLE_KEY = os.getenv("INTASEND_PUBLISHABLE_KEY")
INTASEND_ENV = os.getenv("INTASEND_ENV", "sandbox")

# Initialize IntaSend APIService
service = APIService(
    token=INTASEND_SECRET_KEY,
    publishable_key=INTASEND_PUBLISHABLE_KEY,
    test=(INTASEND_ENV == "sandbox")
)

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

# FIXED: Improved AI-powered flashcard generation
@app.route("/api/generate", methods=["POST"])
def generate_flashcards():
    notes = request.json.get("notes")

    if not notes:
        return jsonify({"error": "No notes provided"}), 400

    # Hugging Face API configuration
    api_key = os.environ.get("HUGGINGFACE_API_KEY")
    
    if not api_key or api_key == os.getenv("HUGGINGFACE_API_KEY"):
        return jsonify({"error": "Invalid or missing Hugging Face API key. Please check your .env file"}), 500

    # Use a reliable model - Mistral works better for instruction following
    api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-v0.1"
    headers = {"Authorization": f"Bearer {api_key}"}

    # Improved prompt for better JSON generation
    prompt = f"""From the following text, create exactly 3 high-quality flashcards with a clear question and detailed answer. 
    Return ONLY a valid JSON array in this exact format: 
    [{{"question": "question text", "answer": "answer text"}}]
    
    Text: {notes[:1500]}"""  # Limit input length

    try:
        print(f"Sending request to Hugging Face API...")
        
        # Add retry logic for model loading
        max_retries = 2
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    api_url, 
                    headers=headers, 
                    json={
                        "inputs": prompt, 
                        "parameters": {
                            "max_new_tokens": 500, 
                            "temperature": 0.3,
                            "return_full_text": False
                        }
                    },
                    timeout=45
                )
                
                # Handle model loading (503 error)
                if response.status_code == 503:
                    error_data = response.json()
                    if 'estimated_time' in error_data:
                        wait_time = error_data['estimated_time'] + 10
                        print(f"Model loading. Waiting {wait_time} seconds...")
                        time.sleep(wait_time)
                        continue
                
                response.raise_for_status()
                break
                
            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    raise
                print(f"Timeout, retrying... ({attempt + 1}/{max_retries})")
                time.sleep(10)
        
        # Parse response
        result = response.json()
        
        if not result or not isinstance(result, list):
            return jsonify({"error": "Invalid response format from AI API"}), 500
        
        # Extract generated text safely
        generated_text = result[0].get("generated_text", "")
        if not generated_text:
            return jsonify({"error": "Empty response from AI"}), 500
        
        print(f"Raw AI response: {generated_text[:200]}...")  # Log first 200 chars
        
        # Robust JSON extraction using regex
        json_match = re.search(r'\[.*\]', generated_text, re.DOTALL)
        if not json_match:
            # Fallback: try to find any JSON structure
            json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
            if not json_match:
                # Ultimate fallback: manual parsing
                return jsonify({
                    "error": "Could not extract JSON from AI response", 
                    "suggestion": "Try simpler notes or check API key",
                    "debug": generated_text[:500]
                }), 500
        
        json_str = json_match.group(0)
        
        # Parse JSON safely (NEVER use eval!)
        try:
            flashcards = json.loads(json_str)
            
            # Validate flashcards structure
            if not isinstance(flashcards, list):
                flashcards = [flashcards]
                
            validated_flashcards = []
            for card in flashcards:
                if isinstance(card, dict) and 'question' in card and 'answer' in card:
                    validated_flashcards.append({
                        'question': str(card['question']),
                        'answer': str(card['answer'])
                    })
            
            if not validated_flashcards:
                return jsonify({"error": "No valid flashcards generated", "raw_response": generated_text[:500]}), 500
                
            return jsonify({"flashcards": validated_flashcards[:3]})
            
        except json.JSONDecodeError as e:
            return jsonify({"error": f"Failed to parse JSON: {str(e)}", "raw_response": generated_text[:500]}), 500

    except requests.exceptions.HTTPError as http_err:
        error_msg = f"Hugging Face API error: {http_err}"
        if http_err.response.status_code == 401:
            error_msg = "Invalid Hugging Face API key. Please check your .env file"
        elif http_err.response.status_code == 503:
            error_msg = "Model is currently loading. Please try again in 30-60 seconds"
        return jsonify({"error": error_msg}), 502
        
    except requests.exceptions.Timeout:
        return jsonify({"error": "AI API timeout. Please try again with shorter notes"}), 504
        
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

# === UPDATED PAYMENT ROUTE ===
@app.route("/api/pay", methods=["POST"])
def pay():
    payload = request.json
    phone_number = payload.get("phone_number")
    email = payload.get("email")
    amount = payload.get("amount")
    plan = payload.get("plan")

    if not phone_number or not amount:
        return jsonify({"success": False, "error": "Missing phone number or amount"}), 400

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