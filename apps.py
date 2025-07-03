from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import groq


# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize Groq client
client = groq.Client(api_key="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")  # Replace with actual key

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

@app.route("/")
def home():
    return render_template("app.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("query", "").strip().lower()
    
    if not user_input:
        return jsonify({"response": "I couldn't find relevant information. Can you rephrase?"})
    
    intent = detect_intent(user_input)
    
    if intent == "greeting":
        response = generate_greeting_response(user_input)
    else:
        # For non-greeting queries, use generate_response
        response = generate_response("", user_input)  # Pass an empty context for now
    
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

'''from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import groq

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Load embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize Groq client
client = groq.Client(api_key="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")  # Replace with actual key

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

@app.route("/")
def home():
    return render_template("app.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("query", "").strip().lower()
    
    if not user_input:
        return jsonify({"response": "I couldn't find relevant information. Can you rephrase?"})
    
    intent = detect_intent(user_input)
    
    if intent == "greeting":
        response = generate_greeting_response(user_input)
    else:
        # For non-greeting queries, use generate_response
        response = generate_response("", user_input)  # Pass an empty context for now
    
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    '''
from flask import Flask, request, jsonify
import groq

app = Flask(__name__)

GROQ_API_KEY = "your_groq_api_key"  # Replace with your actual Groq API key
client = groq.Client(api_key=GROQ_API_KEY)

@app.route("/rchat", methods=["POST"])
def chat():
    try:
        user_input = request.json.get("query", "").strip().lower()
        print(f"Received message: {user_input}")
        
        if not user_input:
            return jsonify({"response": "Please provide a valid location or route query."})
        
        intent = detect_intent(user_input)
        print(f"Detected intent: {intent}")
        
        if intent == "greeting":
            response = generate_greeting_response(user_input)
        elif intent == "route_request":
            response = generate_route_response(user_input)
        else:
            response = "I can help you find routes! Try asking 'Show me the route from A to B'."
        
        print(f"Sending response: {response}")
        return jsonify({"response": response})
    
    except Exception as e:
        print(f"Error in /chat route: {e}")
        return jsonify({"response": "An error occurred. Please try again later."}), 500

def detect_intent(text):
    greetings = ["hi", "hello", "hey", "greetings", "good morning", "good evening"]
    if any(greet in text for greet in greetings):
        return "greeting"
    elif "route" in text or "way to" in text or "directions" in text or "how to go" in text:
        return "route_request"
    return "unknown"

def generate_route_response(query):
    response = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[
            {"role": "system", "content": "You are a route-finding assistant that provides travel directions based on user queries."},
            {"role": "user", "content": query}
        ]
    )
    return response.choices[0].message.content.strip()

def generate_greeting_response(user_input):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a friendly assistant that greets users warmly and provides route-finding assistance."},
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    app.run(debug=True)
