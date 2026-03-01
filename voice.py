from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/")
def home():
    return "WhatsApp Text Bot Running ✅"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    incoming_msg = request.form.get("Body", "").strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    # 🧠 Simple auto-replies
    if incoming_msg in ["hi", "hello"]:
        msg.body("Hello 👋 Welcome to E-Akshaya WhatsApp Service")

    elif "name" in incoming_msg:
        msg.body("Please type your full name.")

    elif "help" in incoming_msg:
        msg.body("Available services:\n1️⃣ Certificate Apply\n2️⃣ Aadhaar Services\n3️⃣ Bill Payment")

    else:
        msg.body("Thanks! We received your message ✅")

    return str(resp)

if __name__ == "__main__":
    app.run()
