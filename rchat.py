from flask import Blueprint, request, jsonify
import groq

# Create a Blueprint for rchat
rchat_bp = Blueprint("rchat", __name__)

# Groq API Key (Replace with your actual key)
GROQ_API_KEY = "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"
client = groq.Client(api_key=GROQ_API_KEY)

@rchat_bp.route("/rchat", methods=["POST"])
def rchat():
    try:
        user_input = request.json.get("query", "").strip().lower()
        print(f"Received rchat message: {user_input}")

        if not user_input:
            return jsonify({"response": "Please provide a valid location or route query."})

        intent = detect_rchat_intent(user_input)
        print(f"Detected intent: {intent}")

        if intent == "greeting":
            response = generate_rchat_greeting_response(user_input)
        elif intent == "route_request":
            response = generate_rchat_route_response(user_input)
        else:
            response = "I can help you find routes! Try asking 'Show me the route from A to B'."

        print(f"Sending rchat response: {response}")
        return jsonify({"response": response})

    except Exception as e:
        print(f"Error in /rchat route: {e}")
        return jsonify({"response": "An error occurred. Please try again later."}), 500

def detect_rchat_intent(text):
    """Detects whether the query is a greeting or a route request."""
    greetings = ["hi", "hello", "hey", "greetings", "good morning", "good evening"]
    if any(greet in text for greet in greetings):
        return "greeting"
    elif "route" in text or "way to" in text or "directions" in text or "how to go" in text:
        return "route_request"
    return "unknown"

def generate_rchat_route_response(query):
    """Uses Groq API to generate route-related responses."""
    response = client.chat.completions.create(
        model="mixtral-8x7b-32768",
        messages=[
            {"role": "system", "content": "You are a route-finding assistant that provides travel directions based on user queries."},
            {"role": "user", "content": query}
        ]
    )
    return response.choices[0].message.content.strip()

def generate_rchat_greeting_response(user_input):
    """Uses Groq API to generate greeting responses."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a friendly assistant that greets users warmly and provides route-finding assistance."},
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content.strip()
