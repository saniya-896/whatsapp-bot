from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "WhatsApp Bot Running ✅"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    incoming_msg = request.form.get("Body", "").strip().lower()
    resp = MessagingResponse()

    if incoming_msg in ["hi", "hello"]:
        resp.message("Hello 👋 Welcome to E-Akshaya WhatsApp Service")

    elif "help" in incoming_msg:
        resp.message("Available services:\n1️⃣ Certificate Apply\n2️⃣ Aadhaar Services\n3️⃣ Bill Payment")

    else:
        resp.message("Message received ✅")

    return str(resp)


# ⭐ IMPORTANT FOR RENDER ⭐
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
