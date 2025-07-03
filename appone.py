'''import os
import json
import re
import time
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_login import login_required, current_user
import google.generativeai as genai
from models import db, Assessment
import traceback

assessment_bp = Blueprint('assessment', __name__, template_folder='templates')

# Securely configure API key
genai.configure(api_key="AIzaSyCD8OgtC5WJCfXMjYW-dOHEpt3E6HeAcmI")

@assessment_bp.route('/assessment')
@login_required
def assessment_home():
    return render_template('index.html')

def generate_questions(subject, num_questions, num_choices):
    prompt = (
        f"Generate {num_questions} multiple-choice questions on the subject '{subject}'. "
        f"Each question should have {num_choices} options. "
        "Respond ONLY with valid JSON like this: "
        "{\"questions\": ["
        "{\"question\": \"Question text?\", \"options\": [\"Option1\", \"Option2\"], \"answer\": \"Option1\"}"
        "]}" 
        "No extra text or explanations."
    )

    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        cleaned_text = re.sub(r'^```json|```$', '', response.text.strip()).strip()
        questions_data = json.loads(cleaned_text)
        
        if "questions" in questions_data:
            return questions_data
        return {"error": "Invalid JSON structure."}
    except Exception as e:
        print("Error generating questions:", e)
        return {"error": str(e)}

@assessment_bp.route('/assessment')
@login_required
def assessment_home():
    return render_template('index.html')

@assessment_bp.route('/generate', methods=["POST"])
@login_required
def generate():
    try:
        data = request.json
        subject = data.get("subject")
        num_questions = int(data.get("num_questions", 0))
        num_choices = int(data.get("num_choices", 0))

        if not subject or num_questions <= 0 or num_choices <= 0:
            return jsonify({"error": "Invalid input data."}), 400

        questions = generate_questions(subject, num_questions, num_choices)

        # Check for errors in question generation
        if "error" in questions:
            return jsonify({"error": questions["error"]}), 500  # Server error

        return jsonify(questions)

    except Exception as e:
        print("Server Error:", str(e))
        traceback.print_exc()  # Print full error log
        return jsonify({"error": "Internal Server Error"}), 500



@assessment_bp.route('/result', methods=['GET', 'POST'])
@login_required
def result():
    if request.method == 'POST':
        print("Received POST request to /result")
        try:
            if time.time() > session.get("time_limit", 0):
                print("Time is up! Submitting assessment.")
                session.pop("time_limit", None)
            
            user_answers = json.loads(request.form.get('userAnswers', '[]'))  # Handle missing key
            print("User answers:", user_answers)

            quiz_data = session.get('quiz_data', {'questions': []})
            print("Quiz data:", quiz_data)

            if not quiz_data['questions']:
                return jsonify({"error": "No quiz data found in session"}), 400

            num_questions = len(quiz_data['questions'])
            num_correct = sum(1 for i, q in enumerate(quiz_data['questions']) 
                              if i < len(user_answers) and q['answer'] == user_answers[i])
            subject = session.get('subject', 'Unknown')
            num_choices = len(quiz_data['questions'][0]['options']) if quiz_data['questions'] else 0
            print(f"Calculated: correct={num_correct}, total={num_questions}, subject={subject}, choices={num_choices}")

            try:
                assessment = Assessment(
                    user_id=current_user.id,
                    subject=subject,
                    num_questions=num_questions,
                    num_correct=num_correct,
                    num_choices=num_choices
                )
                db.session.add(assessment)
                db.session.commit()
                print(f"Saved assessment: {num_correct}/{num_questions}")
            except Exception as db_error:
                print(f"Database error: {type(db_error).__name__}: {str(db_error)}")
                db.session.rollback()
                raise

            session.clear()  # Clear all session data at once

            return redirect(url_for('leaderboard'))  # Ensure 'leaderboard' exists in app.py
        except Exception as e:
            print(f"Error in /result: {type(e).__name__}: {str(e)}")
            raise
    return redirect(url_for('assessment.assessment_home'))
'''
'''from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_login import login_required, current_user
import google.generativeai as genai
import json
import re
from models import db, Assessment
import sqlite3
from flask import Flask, session

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a strong random value


# Blueprint for assessment routes
assessment_bp = Blueprint('assessment', __name__, template_folder='templates')

# Configure Gemini API
genai.configure(api_key="AIzaSyCD8OgtC5WJCfXMjYW-dOHEpt3E6HeAcmI")

@assessment_bp.route('/assessment')
@login_required
def assessment_home():
    return render_template('index.html')

def generate_questions(subject, num_questions, num_choices):
    prompt = (
        f"Generate {num_questions} multiple-choice questions on the subject '{subject}'. "
        f"Each question should have {num_choices} options. "
        "Respond ONLY with valid JSON like this: "
        "{\"questions\": ["
        "{\"question\": \"Question text?\", \"options\": [\"Option1\", \"Option2\"], \"answer\": \"Option1\"}"
        "]}" 
        "No extra text or explanations."
    )

    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        cleaned_text = re.sub(r'^```json|```$', '', response.text.strip()).strip()
        questions_data = json.loads(cleaned_text)
        
        if "questions" in questions_data:
            return questions_data
        return {"error": "Invalid JSON structure."}
    except Exception as e:
        print("Error generating questions:", e)
        return {"error": str(e)}

@assessment_bp.route('/generate', methods=["POST"])
def generate():
    data = request.json
    subject = data.get("subject")
    num_questions = int(data.get("num_questions", 0))
    num_choices = int(data.get("num_choices", 0))

    if not subject or num_questions <= 0 or num_choices <= 0:
        return jsonify({"error": "Invalid input data."}), 400

    questions = generate_questions(subject, num_questions, num_choices)
    if "error" in questions:
        return jsonify(questions), 500

    session["quiz_data"] = questions  # Ensure quiz_data is stored
    session["current_index"] = 0
    session["score"] = 0
    session["user_answers"] = []

    return jsonify({"success": True, "questions": questions["questions"]})



@assessment_bp.route('/submit_result', methods=['POST'])
def submit_result():
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid request format. Expected JSON."}), 400

        data = request.get_json()
        if not data or "userAnswers" not in data:
            return jsonify({"error": "No answers provided"}), 400

        session["user_answers"] = data["userAnswers"]

        return jsonify({"message": "Assessment submitted successfully!", "redirect": url_for('assessment.result_page')})
    
    except Exception as e:
        print("Error processing assessment:", str(e))
        return jsonify({"error": "Server error: " + str(e)}), 500

@assessment_bp.route('/result', methods=['GET'])
def result_page():
    if "quiz_data" not in session or "username" not in session:
        return jsonify({"error": "Quiz data or username not found. Please start a new assessment."}), 400

    username = session.get("username")  # Ensure username is stored in session during login
    subject = session["quiz_data"].get("subject", "Unknown")
    num_questions = len(session.get("user_answers", []))
    num_choices = session.get("quiz_data").get("num_choices", 0)
    correct_answers = session.get("score", 0)
    average_score = round((correct_answers / num_questions) * 100, 2) if num_questions > 0 else 0

    # Store data in the database
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            subject TEXT,
            num_questions INTEGER,
            num_choices INTEGER,
            correct_answers INTEGER,
            average_score REAL
        )
    """)
    
    cursor.execute("""
        INSERT INTO assessments (username, subject, num_questions, num_choices, correct_answers, average_score) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (username, subject, num_questions, num_choices, correct_answers, average_score))
    
    conn.commit()
    conn.close()

    return render_template('result.html', 
                           score=correct_answers, 
                           total=num_questions, 
                           user_answers=session.get("user_answers", []),
                           quiz_data=session.get("quiz_data"))
'''
'''from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_login import login_required, current_user
import google.generativeai as genai
import json
import re
from models import db, Assessment
import sqlite3
from flask import Flask

#app = Flask(__name__)
#app.secret_key = "your_secret_key"  # Change this to a strong random value

# Blueprint for assessment routes
assessment_bp = Blueprint('assessment', __name__, template_folder='templates')

# Configure Gemini API
genai.configure(api_key="AIzaSyDIyx1UedMFucvYk05ji1MRpC55W-LCQTw")

@assessment_bp.route('/assessment')
@login_required
def assessment_home():
    return render_template('index.html')

# Function to generate questions
def generate_questions(subject, num_questions, num_choices):
    prompt = (
        f"Generate {num_questions} multiple-choice questions on the subject '{subject}'. "
        f"Each question should have {num_choices} options. "
        "Respond ONLY with valid JSON like this: "
        "{\"questions\": ["
        "{\"question\": \"Question text?\", \"options\": [\"Option1\", \"Option2\"], \"answer\": \"Option1\"}"
        "]}" 
        "No extra text or explanations."
    )
    
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        cleaned_text = re.sub(r'^```json|```$', '', response.text.strip()).strip()
        questions_data = json.loads(cleaned_text)
        
        if "questions" in questions_data:
            return questions_data
        return {"error": "Invalid JSON structure."}
    except Exception as e:
        print("Error generating questions:", e)
        return {"error": str(e)}

@assessment_bp.route('/generate', methods=["POST"])
def generate():
    try:
        data = request.get_json()
        print("Received Data:", data)  # Debugging

        if not data:
            return jsonify({"error": "No data received"}), 400

        subject = data.get("subject")
        num_questions = int(data.get("num_questions", 0))
        num_choices = int(data.get("num_choices", 0))

        if not subject or num_questions <= 0 or num_choices <= 0:
            return jsonify({"error": "Invalid input data."}), 400

        questions = generate_questions(subject, num_questions, num_choices)
        if "error" in questions:
            return jsonify(questions), 500

        # Store quiz details in session
        #session["quiz_data"] = questions
        session["quiz_data"] = {"subject": subject, "questions": questions["questions"]}
        num_questions = len(quiz_data.get("questions", []))  # Ensure we get total questions
        num_choices = len(quiz_data["questions"][0]["options"]) if num_questions > 0 else 0  # Get choices per question
        correct_answers = session.get("score", 0)  # Fetch score
        session["current_index"] = 0
        session["score"] = 0
        session["user_answers"] = []
        #session["subject"] = subject
        session["username"] = current_user.username  # Set the username in the session
        session.modified = True  
        print("Session Data:", session)  

        return jsonify({"success": True, "questions": questions["questions"]})
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": "Server error"}), 500


@assessment_bp.route('/submit_result', methods=['POST'])
def submit_result():
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid request format. Expected JSON."}), 400

        data = request.get_json()
        if not data or "userAnswers" not in data:
            return jsonify({"error": "No answers provided"}), 400
        
        session["user_answers"] = data["userAnswers"]
        session.modified = True
        
        return jsonify({"message": "Assessment submitted successfully!", "redirect": url_for('assessment.result_page')})
    except Exception as e:
        print("Error processing assessment:", str(e))
        return jsonify({"error": "Server error: " + str(e)}), 500




@assessment_bp.route('/result', methods=['GET'])
def result_page():
    print("Session before /result:", session)  # Debugging log
    user_id = session.get("_user_id")  # Get user_id from session

    if not user_id:
        return jsonify({"error": "User not logged in."}), 400

    # Fetch username from users table
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM user WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    username = result[0] if result else "Unknown"  # Extract username or set default

    if "quiz_data" not in session:
        return jsonify({"error": "Quiz data not found. Please start a new assessment."}), 400

    quiz_data = session["quiz_data"]
    subject = quiz_data.get("subject", "Unknown")
    num_questions = len(session.get("user_answers", []))
    num_choices = quiz_data.get("num_choices", 0)
    correct_answers = session.get("score", 0)
    #average_score = round((correct_answers / num_questions) * 100, 2) if num_questions > 0 else 0
    average_score = round((correct_answers / num_questions) * 100, 2) if num_questions else 0


    # Store results in the database (use user_id instead of username)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,  -- Change from username to user_id
            subject TEXT,
            num_questions INTEGER,
            num_choices INTEGER,
            num_correct INTEGER,
            average_score REAL,
            FOREIGN KEY (user_id) REFERENCES users(id)  -- Ensure user_id is linked
        )
    """)

    cursor.execute("""
        INSERT INTO assessments (user_id, subject, num_questions, num_choices, num_correct, average_score) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, subject, num_questions, num_choices, correct_answers, average_score))

    conn.commit()
    conn.close()

    return render_template('result.html', 
                           username=username,
                           subject=subject,  # Pass the username to the template
                           score=correct_answers, 
                           total=num_questions, 
                           user_answers=session.get("user_answers", []),
                           quiz_data=session.get("quiz_data"))'''
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_login import login_required, current_user
import google.generativeai as genai
import json
import re
import sqlite3

# Blueprint for assessment routes
assessment_bp = Blueprint('assessment', __name__, template_folder='templates')

# Configure Gemini API
genai.configure(api_key="AIzaSyDIyx1UedMFucvYk05ji1MRpC55W-LCQTw")

@assessment_bp.route('/assessment')
@login_required
def assessment_home():
    return render_template('index.html')

# Function to generate questions
def generate_questions(subject, num_questions, num_choices):
    prompt = (
        f"Generate {num_questions} multiple-choice questions on the subject '{subject}'. "
        f"Each question should have {num_choices} options. "
        "Respond ONLY with valid JSON like this: "
        "{\"questions\": ["
        "{\"question\": \"Question text?\", \"options\": [\"Option1\", \"Option2\"], \"answer\": \"Option1\"}"
        "]}" 
        "No extra text or explanations."
    )
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)  # ✅ Define response correctly

        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # Remove leading ```json
        if response_text.endswith("```"):
            response_text = response_text[:-3]  # Remove trailing ```
        
        questions_data = json.loads(response_text)
        if "questions" in questions_data:
            return questions_data
        else:
            return {"error": "Invalid JSON format received from API."}
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON response from API."}

    
'''    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(prompt)
        cleaned_text = re.sub(r'^```json|```$', '', response.text.strip()).strip()
        questions_data = json.loads(cleaned_text)
        
        if "questions" in questions_data:
            return questions_data
        return {"error": "Invalid JSON structure."}
    except Exception as e:
        print("Error generating questions:", e)
        return {"error": str(e)}'''

@assessment_bp.route('/generate', methods=["POST"])
def generate():
    try:
        data = request.get_json()
        print("Received Data:", data)  # Debugging

        if not data:
            return jsonify({"error": "No data received"}), 400

        subject = data.get("subject")
        num_questions = int(data.get("num_questions", 0))
        num_choices = int(data.get("num_choices", 0))

        if not subject or num_questions <= 0 or num_choices <= 0:
            return jsonify({"error": "Invalid input data."}), 400

        questions = generate_questions(subject, num_questions, num_choices)
        if "error" in questions:
            return jsonify(questions), 500

        # Store quiz details in session
        session["quiz_data"] = {"subject": subject, "questions": questions["questions"]}
        session["current_index"] = 0
        session["score"] = 0
        session["user_answers"] = []
        session["username"] = current_user.username  # Set the username in the session
        session.modified = True  

        print("Session Data:", session)  # Debugging log

        return jsonify({"success": True, "questions": questions["questions"]})
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": "Server error"}), 500

@assessment_bp.route('/submit_result', methods=['POST'])
def submit_result():
    try:
        data = request.get_json()
        if not data or "userAnswers" not in data:
            return jsonify({"error": "No answers provided"}), 400

        session["user_answers"] = data["userAnswers"]  # Store user answers
        quiz_data = session.get("quiz_data", {})
        correct_answers = [q["answer"] for q in quiz_data.get("questions", [])]

        # ✅ Calculate score
        score = sum(1 for user_ans, correct_ans in zip(data["userAnswers"], correct_answers) if user_ans == correct_ans)
        session["score"] = score  # ✅ Store updated score
        session.modified = True

        print("Stored user answers:", session["user_answers"])
        print("Updated Score:", session["score"])  # ✅ Debugging

        return jsonify({"message": "Assessment submitted successfully!", "redirect": url_for('assessment.result_page')})
    except Exception as e:
        print("Error processing assessment:", str(e))
        return jsonify({"error": "Server error: " + str(e)}), 500


'''@assessment_bp.route('/submit_result', methods=['POST'])
def submit_result():
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid request format. Expected JSON."}), 400

        data = request.get_json()
        if not data or "userAnswers" not in data:
            return jsonify({"error": "No answers provided"}), 400

        print("Received user answers:", data["userAnswers"])  # Debugging log

        session["user_answers"] = data["userAnswers"]  # ✅ Store user answers
        session.modified = True  # ✅ Mark session as modified

        print("Session after storing user answers:", session)  # Debugging log

        return jsonify({"message": "Assessment submitted successfully!", "redirect": url_for('assessment.result_page')})
    except Exception as e:
        print("Error processing assessment:", str(e))
        return jsonify({"error": "Server error: " + str(e)}), 500'''


'''@assessment_bp.route('/submit_result', methods=['POST'])
def submit_result():
    try:
        if not request.is_json:
            return jsonify({"error": "Invalid request format. Expected JSON."}), 400

        data = request.get_json()
        if not data or "userAnswers" not in data:
            return jsonify({"error": "No answers provided"}), 400
        
        session["user_answers"] = data["userAnswers"]
        session.modified = True
        
        return jsonify({"message": "Assessment submitted successfully!", "redirect": url_for('assessment.result_page')})
    except Exception as e:
        print("Error processing assessment:", str(e))
        return jsonify({"error": "Server error: " + str(e)}), 500'''

@assessment_bp.route('/result', methods=['GET'])
def result_page():
    print("Session before /result:", session)  # Debugging log
    user_id = current_user.id  # Get user ID

    if not user_id:
        return jsonify({"error": "User not logged in."}), 400

    if "quiz_data" not in session:
        return jsonify({"error": "Quiz data not found. Please start a new assessment."}), 400

    quiz_data = session["quiz_data"]
    subject = quiz_data.get("subject", "Unknown")
    num_questions = len(quiz_data.get("questions", []))  # Correct total question count
    num_choices = len(quiz_data["questions"][0]["options"]) if num_questions > 0 else 0  # Extract choices correctly
    correct_answers = session.get("score", 0)  # Fetch correct answers
    average_score = round((correct_answers / num_questions) * 100, 2) if num_questions else 0

    # Determine rank based on percentage
    rank = "Promoted" if average_score >= 50 else "Depromoted"

    # Store results in the database
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject TEXT,
            num_questions INTEGER,
            num_choices INTEGER,
            num_correct INTEGER,
            average_score REAL,
            rank TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        INSERT INTO assessments (user_id, subject, num_questions, num_choices, num_correct, average_score, rank) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, subject, num_questions, num_choices, correct_answers, average_score, rank))

    conn.commit()
    conn.close()

    return render_template('result.html', 
                           username=session.get("username", "Unknown"),
                           subject=subject,  
                           score=correct_answers, 
                           total=num_questions, 
                           user_answers=session.get("user_answers", []),
                           quiz_data=quiz_data,
                           rank=rank)
