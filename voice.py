from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import os

app = Flask(__name__)

# Store user sessions
user_data = {}

@app.route("/")
def home():
    return "WhatsApp Bot Running"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():

    resp = MessagingResponse()
    msg = resp.message()

    sender = request.values.get("From")
    body = request.values.get("Body")

    text_msg = (body or "").strip().lower()

    print("User:", sender, "Message:", text_msg)

    # START / MENU
    if text_msg in ["menu", "start", "hi", "hello"]:

        user_data[sender] = {"step": "menu"}

        msg.body(
            "🙏 *Welcome to E-Akshaya Digital Service*\n\n"
            "📋 Available Services\n\n"
            "1️⃣ Pension Application\n"
            "2️⃣ Income Certificate\n"
            "3️⃣ Ration Card\n\n"
            "Reply with option number."
        )

        return str(resp)

    # FIRST USER MESSAGE
    if sender not in user_data:

        user_data[sender] = {"step": "menu"}

        msg.body(
            "🙏 *Welcome to E-Akshaya Digital Service*\n\n"
            "1️⃣ Pension Application\n"
            "2️⃣ Income Certificate\n"
            "3️⃣ Ration Card\n\n"
            "Reply with option number."
        )

        return str(resp)

    step = user_data[sender]["step"]

    # MENU OPTION
    if step == "menu":

        if text_msg == "1":

            user_data[sender]["service"] = "Pension Application"
            user_data[sender]["step"] = "name"

            msg.body("👤 Please enter your name.")

        elif text_msg == "2":

            user_data[sender]["service"] = "Income Certificate"
            user_data[sender]["step"] = "name"

            msg.body("👤 Please enter your name.")

        elif text_msg == "3":

            user_data[sender]["service"] = "Ration Card"
            user_data[sender]["step"] = "name"

            msg.body("👤 Please enter your name.")

        else:

            msg.body("❌ Invalid option. Please type 1, 2 or 3.")

    # NAME STEP
    elif step == "name":

        user_data[sender]["name"] = text_msg.title()

        msg.body("🆔 Enter your Aadhaar number.")

        user_data[sender]["step"] = "aadhaar"

    # AADHAAR STEP
    elif step == "aadhaar":

        if not text_msg.isdigit() or len(text_msg) != 12:

            msg.body("❌ Invalid Aadhaar. Please enter a 12 digit Aadhaar number.")

        else:

            user_data[sender]["aadhaar"] = text_msg

            msg.body("📍 Enter your address.")

            user_data[sender]["step"] = "address"

    # ADDRESS STEP
    elif step == "address":

        user_data[sender]["address"] = text_msg

        service = user_data[sender]["service"]
        name = user_data[sender]["name"]
        aadhaar = user_data[sender]["aadhaar"]
        address = user_data[sender]["address"]

        msg.body(
            f"✅ Application Submitted!\n\n"
            f"Service: {service}\n"
            f"Name: {name}\n"
            f"Aadhaar: {aadhaar}\n"
            f"Address: {address}\n\n"
            f"Type *menu* to apply again."
        )

        user_data.pop(sender, None)

    return str(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
