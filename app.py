from flask import Flask, render_template, request, session, redirect, url_for
from flask import render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import google.generativeai as genai
import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import openai  # don't go for upgraded version
import json
import requests
from flask_weasyprint import HTML, render_pdf
from weasyprint import CSS
from appone import assessment_bp
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import google.generativeai as genai
import markdown
from markdown.extensions.fenced_code import FencedCodeExtension
import re
import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import openai
import json
import requests
from flask_weasyprint import HTML, render_pdf
from weasyprint import CSS
from appone import assessment_bp
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import groq
from flask_cors import CORS
from models import db, Assessment, User, Course
from rchat import rchat_bp  # Import rchat Blueprint
import sqlite3
import datetime
import traceback
from flask import session
from flask_bcrypt import bcrypt
from groq import Groq

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'alpha-beta-gamma'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'newindex'#new
openai.api_key = "AIzaSyCOLpGZ6588XLVPiZ2xgtrQWrUUGo4TOv4"
UPLOAD_FOLDER = 'static/profile_photos'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
genai.configure(api_key="AIzaSyCOLpGZ6588XLVPiZ2xgtrQWrUUGo4TOv4")
# Create a Markdown instance with the FencedCodeExtension
md = markdown.Markdown(extensions=[FencedCodeExtension()])
# Initialize Groq client
client = groq.Client(api_key="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")  # Replace with actual key
# Register the rchat bot in the main Flask app
app.register_blueprint(rchat_bp)
# Load embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Register the assessment Blueprint
app.register_blueprint(assessment_bp, url_prefix='/assessment')
from models import User, Assessment
DB_NAME = "users.db"
'''class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)'''




'''lass User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique = True)
    email = db.Column(db.String(50), unique = True)
    password = db.Column(db.String(80))
    courses = db.relationship('Course', backref='user', lazy=True)
    date_joined = db.Column(db.DateTime, default=datetime.now)
    profile_photo = db.Column(db.String(100), nullable=True)  # New column
    total_coins = db.Column(db.Integer, default=0)  # New column for coins
    assessments = db.relationship('Assessment', backref='user', lazy=True)#new'''

# Assessment model
'''class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(100))
    num_questions = db.Column(db.Integer)
    num_correct = db.Column(db.Integer)
    num_choices = db.Column(db.Integer)'''


@app.route('/extrahtml')
def extrahtml():
    return render_template('extrahtml.html')

@app.route('/performance')
def performance():
    return render_template('performance.html')

def create_tables():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            last_login TEXT,
            total_time_spent INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# Call the function at the start of the app
create_tables()

# Ensure the user_activity table exists in users.db
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_activity (
                            username TEXT PRIMARY KEY,
                            last_login TEXT,
                            total_time_spent INTEGER
                        )''')
        conn.commit()

  # Display the study gap system in app.html

@app.route("/track", methods=["POST"])
def track_activity():
    username = request.json.get("username")  # Using username instead of user_id
    time_spent = request.json.get("time_spent")  # Time in minutes

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT last_login, total_time_spent FROM user_activity WHERE username=?", (username,))
        row = cursor.fetchone()

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if row:
            last_login, total_time = row
            last_login_date = datetime.datetime.strptime(last_login, "%Y-%m-%d %H:%M:%S")
            days_gap = (datetime.datetime.now() - last_login_date).days
            new_total_time = total_time + time_spent
            cursor.execute("UPDATE user_activity SET last_login=?, total_time_spent=? WHERE username=?",
                           (current_time, new_total_time, username))
        else:
            days_gap = 0
            cursor.execute("INSERT INTO user_activity (username, last_login, total_time_spent) VALUES (?, ?, ?)",
                           (username, current_time, time_spent))

        conn.commit()

    return jsonify({"message": "Activity recorded", "days_gap": days_gap, "total_time_spent": new_total_time if row else time_spent})

@app.route("/get_gap/<username>")
def get_gap(username):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT last_login, total_time_spent FROM user_activity WHERE username=?", (username,))
        row = cursor.fetchone()

        if row:
            last_login, total_time = row
            last_login_date = datetime.datetime.strptime(last_login, "%Y-%m-%d %H:%M:%S")
            days_gap = (datetime.datetime.now() - last_login_date).days
            return jsonify({"days_gap": days_gap, "total_time_spent": total_time})
        else:
            return jsonify({"days_gap": "No data", "total_time_spent": "No data"})

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




@app.route("/quiz_interface")
def quiz_interface():
    return render_template("home.html")


@app.route('/feedback')
def feedback():
    return render_template('feedback.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    # Handle form data here
    name = request.form['name']
    email = request.form['email']
    rating = request.form['rating']
    comments = request.form['comments']
    # Process and store the feedback
    return redirect(url_for('feedback'))

@app.route("/chat", methods=["POST"])
def chat():
    try:
        # Get the user input from the request
        user_input = request.json.get("query", "").strip().lower()
        print(f"Received message: {user_input}")  # Debugging
        
        if not user_input:
            return jsonify({"response": "I couldn't find relevant information. Can you rephrase?"})
        
        # Detect the intent of the user input
        intent = detect_intent(user_input)
        print(f"Detected intent: {intent}")  # Debugging
        
        # Generate a response based on the intent
        if intent == "greeting":
            response = generate_greeting_response(user_input)
        else:
            response = generate_response("", user_input)  # Pass an empty context for now
        
        print(f"Sending response: {response}")  # Debugging
        
        # Return the response as JSON
        return jsonify({"response": response})
    
    except Exception as e:
        print(f"Error in /chat route: {e}")
        return jsonify({"response": "An error occurred. Please try again later."}), 500

def detect_intent(text):
    """Detects if the input is a greeting or a general query."""
    greetings = ["hi", "hello", "hey", "greetings", "what's up", "good morning", "காலை வணக்கம்!", "எப்படி இருக்கிறீர்கள்?", "நன்றி","how are you","how ar u","hw ar u","வணக்கம்!"]
    return "greeting" if any(greet in text for greet in greetings) else "search"

def generate_response(context, query):
    """Generates chatbot responses for educational queries using Groq API."""
    print("Searching for relevant answer...")

    search_prompt = [
        {"role": "system", "content": """You are an AI tutor specializing in educational queries. 
        Your goal is to provide **concise, engaging, and accurate** answers while keeping the explanation simple. 

        📌 *Response Guidelines*:
        1. Use simple and clear language.
        2. Avoid long paragraphs—keep answers **short and to the point**.
        3. Include **examples** when necessary.
        4. If context is missing, use general knowledge to answer.
        5. Format answers for **better readability** using bullet points, equations, or steps when needed.

        🎯 *Example Responses*:
        - **Query:** "What is Newton's First Law?"
          **Response:**  
          *Newton's First Law (Law of Inertia) states:*  
          - An object at rest stays at rest.  
          - An object in motion stays in motion unless acted upon by an external force.  
          - Example: A book on a table stays still until someone moves it.

        - **Query:** "Explain Pythagoras' theorem."
          **Response:**  
          - Formula: *a² + b² = c²* (In a right-angled triangle).  
          - Example: If one side is 3 and the other is 4, the hypotenuse is **5** (since 3² + 4² = 5²).  

        - **Query:** "What are the applications of AI in healthcare?"
          **Response:**  
          AI in healthcare is used for:  
          - **Medical Diagnosis** (detecting diseases faster).  
          - **Personalized Treatment** (AI-based prescriptions).  
          - **Robotic Surgery** (precise, minimally invasive).  
          - **Drug Discovery** (faster research for medicines).  

        Now, provide a **concise and engaging** response following these guidelines.
        """},
        {"role": "user", "content": f"Context: {context} \nUser Query: {query}"}
    ]

    response = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=search_prompt
    ) 

    return response.choices[0].message.content.strip()

def generate_greeting_response(user_input):
    """Handles greeting responses for the educational chatbot."""
    print("Generating greeting response...")

    greet_prompt = [
        {"role": "system", "content": """You are an AI tutor that provides friendly and **engaging** greetings.
        Your goal is to be **warm, welcoming, and concise** while maintaining an **educational** focus.

        🎓 *Guidelines*:
        - Keep responses **short and friendly**.
        - Match the user's language (if they use informal tone, respond casually).
        - If they ask how you are, respond **positively**.
        - Encourage users to ask educational queries.

        📌 *Example Responses*:
        - **User:** "Hi!"  
          **Response:** "Hello! How can I assist with your studies today?"
        - **User:** "Hey, what's up?"  
          **Response:** "Hey! I'm here to help you learn. What would you like to know?"
        - **User:** "Good morning!"  
          **Response:** "Good morning! Ready to explore something new today?"
        - **User:** "How are you?"  
          **Response:** "I'm great! Always ready to help with learning. What’s your question?"

        Now, generate a **friendly and engaging** greeting.
        """},
        {"role": "user", "content": f"User Query: {user_input}"}
    ]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=greet_prompt
    )
    
    return response.choices[0].message.content.strip()



@app.route("/quiz", methods=["GET", "POST"])





def quiz():
    if request.method == "POST":
        print(request.form)
        language = request.form["language"]
        questions = request.form["ques"]
        choices = request.form["choices"]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"Hey ChatGPT, prepare a quick quiz on this programming language: {language}. "
                               f"Prepare {questions} number of questions and for each of them keep {choices} choices. "
                               f"Reply in JSON format with an object containing 'topic', and a 'questions' array with 'question', "
                               f"'choices', and the correct 'answer'."
                }
            ],  
            temperature=0.7,
        )

        quiz_content = response['choices'][0]['message']['content']

        try:
            quiz_content = json.loads(quiz_content)  # Convert JSON string to dictionary
        except json.JSONDecodeError:
            return "Error: Invalid response format from OpenAI", 500  # Handle JSON errors safely

        session['response'] = quiz_content  # Store quiz in session

        return render_template("quiz.html", quiz_content=quiz_content)

    if request.method == "GET":
        score = 0
        actual_answers = []
        given_answers = list(request.args.values()) or []
        res = session.get('response', {})

        if "questions" in res:
            for answer in res["questions"]:
                actual_answers.append(answer["answer"])

            if given_answers:
                for i in range(min(len(actual_answers), len(given_answers))):  # Prevent index errors
                    if actual_answers[i] == given_answers[i]:
                        score += 1

        return render_template("score.html", actual_answers=actual_answers, given_answers=given_answers, score=score)





ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')

        # Handle profile photo upload
        profile_photo = request.files.get('profile_photo')  # Use .get() to avoid KeyError

        if profile_photo and allowed_file(profile_photo.filename):  
            filename = secure_filename(profile_photo.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Ensure the 'static/profile_photos' directory exists
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            profile_photo.save(filepath)
        else:
            filename = "default.jpg"  # Default profile picture

        new_user = User(username=username, email=email, password=password, profile_photo=filename)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('signup.html')





@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            
            # ✅ Store username in session
            session["username"] = user.email  # Or user.username if you have a username field

            print("Session after login:", session)  # Debugging

            return redirect(url_for('dashboard'))
            
    return render_template('login.html')


'''@app.route('/signup', methods=['POST'])
def signup():
    return redirect(url_for('auth'))  # Redirects to auth for signup processing

@app.route('/login', methods=['POST'])
def login():
    return redirect(url_for('auth'))'''  # Redirects to auth for signup processing



app.register_blueprint(assessment_bp, url_prefix='/assessment_bot')
@app.route('/dashboard')
def dashboard():
    if current_user.is_authenticated:
        return render_template('dashboard.html', user=current_user)
    else:
        # Redirect to login page or handle the case where user is not logged in
        return redirect(url_for('login'))


'''@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_authenticated:
        return render_template('dashboard.html', user=current_user)
    else:
        return redirect(url_for('newindex'))'''

from flask_login import current_user  # Ensure this is imported

@app.route("/")
def home():
    if current_user.is_authenticated:
        saved_courses = Course.query.filter_by(user_id=current_user.id).all()
        recommended_courses = generate_recommendations(saved_courses)

        # Add leaderboard data
        leaderboard = db.session.query(
            User.username, Assessment.subject, Assessment.num_correct, 
            Assessment.num_questions, Assessment.num_choices
        ).join(Assessment, User.id == Assessment.user_id)\
        .order_by((Assessment.num_correct / Assessment.num_questions).desc())\
        .all()

        print("Root route - Leaderboard data:", leaderboard)  # Debug
        return render_template('app.html', saved_courses=saved_courses, recommended_courses=recommended_courses, 
                               user=current_user, leaderboard=leaderboard)
    else:
        print("Redirecting to newindex (login/signup page)")
        return redirect(url_for('login'))  # ✅ FIXED: Redirecting to correct page

    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

from sqlalchemy import case, desc

@app.route('/leaderboard')
@login_required
def leaderboard():
    print("Entering leaderboard route")

    # Ensure num_questions is not zero to avoid division errors
    score_percentage = (Assessment.num_correct /
                        case([(Assessment.num_questions == 0, 1)], else_=Assessment.num_questions)
                        ).label("score_percentage")
    
    # Assign rank based on percentage (≥50% = Promoted, else Depromoted)
    '''rank = case(
        [(score_percentage >= 50, 'Promoted')],
        else_='Depromoted'
    ).label("rank")'''

    leaderboard = db.session.query(
        User.username, 
        Assessment.subject, 
        Assessment.num_correct, 
        Assessment.num_questions, 
        Assessment.num_choices,  # 🔹 Added num_choices to retrieve correct data
        Assessment.rank,
        score_percentage
    ).join(Assessment, User.id == Assessment.user_id) \
     .order_by(desc(score_percentage).nulls_last()) \
     .all()

    print("Leaderboard data:", leaderboard)  # Debugging print statement

    return render_template('app.html', leaderboard=leaderboard, user=current_user)


'''@app.route('/leaderboard')
@login_required
def leaderboard():
    print("Entering leaderboard route")
    
    # Handling division by zero using case() to return 0 if num_questions is 0
    leaderboard = db.session.query(User.username, 
                                    Assessment.subject, 
                                    Assessment.num_correct, 
                                    Assessment.num_questions, 
                                    Assessment.num_choices) \
        .join(Assessment, User.id == Assessment.user_id) \
        .order_by(case([(Assessment.num_questions == 0, 0)], else_=(Assessment.num_correct / Assessment.num_questions)).desc()) \
        .all()
    
    print("Leaderboard data:", leaderboard)
    return render_template('app.html', leaderboard=leaderboard, user=current_user)'''


'''@app.route('/leaderboard')
@login_required
def leaderboard():
    print("Entering leaderboard route")
    leaderboard = db.session.query(User.username, Assessment.subject, Assessment.num_correct, 
                                  Assessment.num_questions, Assessment.num_choices)\
        .join(Assessment, User.id == Assessment.user_id)\
        .order_by((Assessment.num_correct / Assessment.num_questions).desc())\
        .all()
    print("Leaderboard data:", leaderboard)
    return render_template('app.html', leaderboard=leaderboard, user=current_user)

@app.route("/")
def home():
    if current_user.is_authenticated:
        saved_courses = Course.query.filter_by(user_id=current_user.id).all()
        recommended_courses = generate_recommendations(saved_courses)
        return render_template('app.html', saved_courses=saved_courses, recommended_courses=recommended_courses, user=current_user)
    else:
        return redirect(url_for('login'))'''


'''@app.route('/')
def home():
    if current_user.is_authenticated:
        saved_courses = Course.query.filter_by(user_id=current_user.id).all()
        recommended_courses = generate_recommendations(saved_courses)
        return render_template('app.html', saved_courses=saved_courses, recommended_courses = recommended_courses, user=current_user)
    else:
        return redirect(url_for('login'))'''




@app.route('/course', methods=['GET', 'POST'])
@login_required
def course():
    if request.method == 'POST':
        course_name = request.form['course_name']
        completions = generate_text(course_name)
        print(f"course_name: {course_name}")
        rendered = render_template('courses/course1.html', completions=completions, course_name=course_name)
        new_course = Course(course_name=course_name, content=rendered, user_id=current_user.id)
        db.session.add(new_course)
        db.session.commit()
        return rendered
    return render_template('courses/course1.html')




@app.route('/r_course/<course_name>', methods=['GET', 'POST'])
@login_required
def r_course(course_name):
    completions = None  # Initialize completions to None
    if request.method == 'POST':
        completions = generate_text(course_name)
        print(f"course_name: {course_name}")
        rendered = render_template('courses/course1.html', completions=completions, course_name=course_name)
        new_course = Course(course_name=course_name, content=rendered, user_id=current_user.id)
        db.session.add(new_course)
        db.session.commit()
        return rendered
    # If the request method is 'GET', generate the text for the course
    completions = generate_text(course_name)
    return render_template('courses/course1.html', completions=completions, course_name=course_name)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
@app.route('/saved_course/<course_name>')
@login_required
def saved_course(course_name):
    # Fetch the current user
    user = User.query.get(current_user.id)

    # Increment the total coins
    user.total_coins += 1
    db.session.commit()

    # Fetch the course (if it exists in the database)
    course = Course.query.filter_by(course_name=course_name, user_id=current_user.id).first()

    # Generate course content using the Gemini API
    completions = generate_text(course_name)

    # Render the course page
    if course:
        return render_template('courses/saved_course.html', course=course, completions=completions)
    else:
        return render_template('courses/saved_course.html', course_name=course_name, completions=completions)

@app.route('/get_coins')
@login_required
def get_coins():
    # Fetch the current user's total coins from the database
    user = User.query.get(current_user.id)
    return str(user.total_coins)

@app.route('/module/<course_name>/<module_name>', methods=['GET'])
def module(course_name,module_name):
    content = generate_module_content(course_name,module_name)
    if not content:
        return "<p>Module not found</p>"
    html = render_template('module.html', content=content)
    
    # If the 'download' query parameter is present in the URL, return the page as a PDF
    if 'download' in request.args:
        #Create a CSS object for the A3 page size
        a3_css = CSS(string='@page {size: A3; margin: 1cm;}')
        return render_pdf(HTML(string=html), stylesheets=[a3_css])

    # Otherwise, return the page as HTML
    return html 


@app.route('/app1')
def app1():
    if current_user.is_authenticated:
        saved_courses = Course.query.filter_by(user_id=current_user.id).all()
        recommended_courses = generate_recommendations(saved_courses)
        return render_template('app.html', saved_courses=saved_courses, recommended_courses = recommended_courses, user=current_user)
    else:
        return redirect(url_for('login'))





def markdown_to_list(markdown_string):
    # Split the string into lines
    lines = markdown_string.split('\n')
    # Use a regular expression to match lines that start with '* '
    list_items = [re.sub(r'\* ', '', line) for line in lines if line.startswith('* ')]
    return list_items

def generate_text(course):
    client = Groq(api_key="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")  # Replace with your Groq API key

    prompts = {
        'approach': f"You are a pedagogy expert and you are designing a learning material for {course} for an undergrad university student. You have to decide the approach to take for learning from this learning material. Please provide a brief description of the approach you would take to study this learning material (provide in points). After that, please provide a brief description of the learning outcomes that you expect from this learning material.",
        'modules': f"Based on the course {course}, please provide a list of modules that you would include in the course. Each module should be a subtopic of the course and should be listed in bullet points. Additionally, please provide a brief description of each module to give an overview of the content covered in the module.",
    }

    completions = {}    
    for key, prompt in prompts.items():
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Replace with the Groq model you want to use
            messages=[{"role": "user", "content": prompt}]
        )

        if response and response.choices:
            if key == 'modules':
                markdown_string = response.choices[0].message.content.replace('•', '*')  # Replace bullet points
                completions[key] = markdown_string.split("\n")  # Convert to list
            else:
                completions[key] = markdown.markdown(response.choices[0].message.content)
        else:
            completions[key] = ""

    return completions
def generate_module_content(course_name, module_name):
    client = Groq(api_key="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")  # Replace with your Groq API key

    # First prompt for module content
    module_prompt = f"""
    Course Name: {course_name}
    Topic: {module_name}.
    Please provide a comprehensive explanation of {module_name}. 
    Feel free to use examples or analogies to clarify complex ideas.
    """
    
    module_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": module_prompt}]
    )
    module_content = module_response.choices[0].message.content if module_response and module_response.choices else ""

    # Second prompt for code snippets
    code_prompt = f"""
    Course Name: {course_name}
    Topic: {module_name}.
    If the explanation of {module_name} requires code snippets for better understanding, please provide them.
    """
    
    code_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": code_prompt}]
    )
    code_content = code_response.choices[0].message.content if code_response and code_response.choices else ""

    # Third prompt for ASCII art diagrams
    ascii_prompt = f"""
    Course Name: {course_name}
    Topic: {module_name}.
    If the explanation of {module_name} requires diagrams for better understanding, please provide them in ASCII art format.
    """
    
    ascii_response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": ascii_prompt}]
    )
    ascii_content = ascii_response.choices[0].message.content if ascii_response and ascii_response.choices else ""

    # Convert markdown content to HTML
    module_content_html = markdown.markdown(module_content)
    code_content_html = markdown.markdown(f"```python\n{code_content}\n```")  # Wrap in code block
    ascii_content_html = markdown.markdown(f"```\n{ascii_content}\n```")  # Wrap in ASCII block

    # Combine all content
    combined_content = f"{module_content_html}\n{code_content_html}\n{ascii_content_html}"

    return combined_content
def generate_recommendations(saved_courses):
    recommended_courses = []
    client = Groq(api_key="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")  # Replace with your Groq API key

    for course in saved_courses:
        prompt = f"""
        Based on the course {course.course_name}, please provide just a single course name at the top
        and a concise description (less than 70 characters) for a new recommended course that would be beneficial
        for the student to take next.
        """

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )

        if response and response.choices:
            course_name = response.choices[0].message.content.strip()
            recommended_courses.append({'name': course_name, 'description': course_name})

    return recommended_courses

'''
def generate_text(course):
    model = genai.GenerativeModel("gemini-1.5")

    prompts = {
        'approach': f"You are a pedagogy expert and you are designing a learning material for {course} for an undergrad university student. You have to decide the approach to take for learning from this learning material. Please provide a brief description of the approach you would take to study this learning material (provide in points). After that, please provide a brief description of the learning outcomes that you expect from this learning material.",
        'modules': f"Based on the course {course}, please provide a list of modules that you would include in the course. Each module should be a subtopic of the course and should be listed in bullet points. Additionally, please provide a brief description of each module to give an overview of the content covered in the module.",
    }

    completions = {}    
    for key, prompt in prompts.items():
        response = model.generate_content(prompt)

        if response and response.text:
            if key == 'modules':
                markdown_string = response.text.replace('•', '*')  # Replace bullet points
                completions[key] = markdown_string.split("\n")  # Convert to list
            else:
                completions[key] = markdown.markdown(response.text)
        else:
            completions[key] = ""

    return completions




def generate_module_content(course_name, module_name):
    model = genai.GenerativeModel("gemini-1.5")

    # First prompt for module content
    module_prompt = f"""
    Course Name: {course_name}
    Topic: {module_name}.
    Please provide a comprehensive explanation of {module_name}. 
    Feel free to use examples or analogies to clarify complex ideas.
    """
    
    module_completion = model.generate_content(module_prompt)
    module_content = module_completion.text if module_completion and module_completion.text else ""

    # Second prompt for code snippets
    code_prompt = f"""
    Course Name: {course_name}
    Topic: {module_name}.
    If the explanation of {module_name} requires code snippets for better understanding, please provide them.
    """
    
    code_completion = model.generate_content(code_prompt)
    code_content = code_completion.text if code_completion and code_completion.text else ""

    # Third prompt for ASCII art diagrams
    ascii_prompt = f"""
    Course Name: {course_name}
    Topic: {module_name}.
    If the explanation of {module_name} requires diagrams for better understanding, please provide them in ASCII art format.
    """
    
    ascii_completion = model.generate_content(ascii_prompt)
    ascii_content = ascii_completion.text if ascii_completion and ascii_completion.text else ""

    # Convert markdown content to HTML
    module_content_html = markdown.markdown(module_content)
    code_content_html = markdown.markdown(f"```python\n{code_content}\n```")  # Wrap in code block
    ascii_content_html = markdown.markdown(f"```\n{ascii_content}\n```")  # Wrap in ASCII block

    # Combine all content
    combined_content = f"{module_content_html}\n{code_content_html}\n{ascii_content_html}"

    return combined_content




def generate_recommendations(saved_courses):
    recommended_courses = []
    model = genai.GenerativeModel("gemini-1.5-pro")

    for course in saved_courses:
        prompt = f"""
        Based on the course {course.course_name}, please provide just a single course name at the top
        and a concise description (less than 70 characters) for a new recommended course that would be beneficial
        for the student to take next.
        """

        response = model.generate_content(prompt)

        if response and response.text:
            course_name = response.text.strip()
            recommended_courses.append({'name': course_name, 'description': course_name})

    return recommended_courses'''
@app.route('/assessment_bot/result')
def result():
    # Fetch session data
    quiz_data = session.get('quiz_data', [])
    user_answers = session.get('user_answers', [])
    score = session.get('score', 0)

    # Ensure the data is not empty and then calculate the result
    if quiz_data and user_answers:
        # Calculate score based on answers
        for i, question in enumerate(quiz_data):
            if user_answers[i] == question['answer']:
                score += 1

    return render_template('result.html', score=score, quiz_data=quiz_data, user_answers=user_answers)




@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/ais')
def ais_page():
    return render_template('aiss.html')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="127.0.0.1", debug=True)
    
