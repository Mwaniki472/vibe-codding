Flashcards + IntaSend Payment App

This project is a Flask + JavaScript web application that allows users to:

Generate flashcards from notes using Hugging Face API

Save and load flashcards from a database

Make payments using IntaSend (Sandbox or Live)

🚀 Features

Flashcards

Enter notes and generate Q&A flashcards with Hugging Face models.

Save generated flashcards in a MySQL database.

View saved flashcards in a flip-card style.

Payments

Integrates with IntaSend API (M-Pesa & Card Payments).

Users can subscribe to Basic or Premium plans.

Transactions are stored in the database.

⚙️ Installation
1. Clone the repository
git clone https://github.com/your-username/flashcards-intasend.git
cd flashcards-intasend

2. Create a virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

3. Install dependencies
pip install -r requirements.txt

4. Set up .env file

Create a .env file in the root folder with the following values:

FLASK_ENV=development
INTASEND_SECRET_KEY=your_sandbox_secret_key
INTASEND_PUBLISHABLE_KEY=your_sandbox_publishable_key
INTASEND_ENV=sandbox

DATABASE_HOST=localhost
DATABASE_USER=root
DATABASE_PASSWORD=yourpassword
DATABASE_NAME=flashcards_db

HF_API_KEY=your_huggingface_api_key

▶️ Running the App

Start the Flask backend:

python app.py


The backend runs at: http://127.0.0.1:5000

Open the frontend (index.html) in your browser.

📂 Project Structure
project/
│── app.py              # Flask backend
│── db.py               # Database connection helper
│── requirements.txt    # Dependencies
│── .env                # Environment variables
│── static/
│   └── app.js          # Frontend logic (Flashcards + Payments)
│── templates/
│   └── index.html      # Frontend UI
│── README.md           # Documentation

🛠️ Technologies Used

Flask (Python backend)

MySQL (Database)

Hugging Face API (AI flashcards generation)

IntaSend API (Payments)

JavaScript, HTML, CSS (Frontend)

📌 Notes

Replace all API keys with your own from IntaSend
 and Hugging Face
.

Start in sandbox mode for safe testing before going live.

👨‍💻 Author

Developed by Cynthia Mwaniki 🚀

