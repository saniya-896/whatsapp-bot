from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():
    msg = request.form.get("Body")

    response = MessagingResponse()
    response.message("Hello! Your bot is working ✅")

    return str(response)

if __name__ == "__main__":
    app.run(port=5000)
