import os
from flask import Flask, request, jsonify
import openai
from twilio.rest import Client
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Load API keys from .env file
openai.api_key = os.getenv("OPENAI_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
ADMIN_PHONE_NUMBER = os.getenv("ADMIN_PHONE_NUMBER")
MONGO_URI = os.getenv("MONGO_URI")

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client.support_bot
chat_logs = db.chat_logs

# Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Predefined FAQ responses
faq_responses = {
    "What are your business hours?": "Our business hours are from 9 AM to 6 PM, Monday to Friday.",
    "How can I reset my password?": "To reset your password, go to the login page and click on 'Forgot Password'.",
    "How do I contact customer support?": "You can reach our customer support at support@example.com or call us at +123456789."
}

def get_ai_response(user_message):
    """ Fetch AI-generated response from OpenAI """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_message}]
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return "Sorry, I am unable to process your request at the moment."

def escalate_to_human(user_message, user_phone):
    """ Escalate chat to a human agent via Twilio SMS/WhatsApp """
    try:
        twilio_client.messages.create(
            body=f"Customer ({user_phone}) needs support: {user_message}",
            from_=TWILIO_PHONE_NUMBER,
            to=ADMIN_PHONE_NUMBER
        )
        return "Your request has been forwarded to a human agent. They will contact you shortly."
    except Exception as e:
        return "Failed to escalate. Please try again later."

def log_chat(user_message, bot_response, user_phone):
    """ Store chat interactions in MongoDB """
    chat_logs.insert_one({"user": user_phone, "message": user_message, "response": bot_response})

@app.route("/chat", methods=["POST"])
def chat():
    """ Handle incoming chat messages """
    data = request.json
    user_message = data.get("message", "").strip()
    user_phone = data.get("phone", "")

    # Check if the message is a predefined FAQ
    if user_message in faq_responses:
        bot_reply = faq_responses[user_message]
    else:
        # Get AI-generated response
        bot_reply = get_ai_response(user_message)

    # If AI response is unclear, escalate
    if "Sorry" in bot_reply or "I don't know" in bot_reply:
        bot_reply = escalate_to_human(user_message, user_phone)

    # Log the conversation
    log_chat(user_message, bot_reply, user_phone)

    return jsonify({"reply": bot_reply})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
