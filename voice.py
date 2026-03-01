from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    msg = request.form.get("Body")

    response = MessagingResponse()
    response.message("Hello! Your bot is LIVE on Render ✅")

    return str(response)
