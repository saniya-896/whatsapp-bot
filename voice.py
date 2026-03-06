from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import speech_recognition as sr
from pydub import AudioSegment
import os
import random
from requests.auth import HTTPBasicAuth

app = Flask(__name__)

ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

AudioSegment.converter = "/usr/bin/ffmpeg"

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
    num_media = int(request.values.get("NumMedia") or 0)

    print("User:", sender, "Message:", text_msg)

    # MENU
    if text_msg in ["menu", "start", "restart"]:

        user_data.pop(sender, None)
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

    # VOICE MESSAGE
    if num_media > 0:

        content_type = request.values.get("MediaContentType0", "")

        if "audio" not in content_type:
            msg.body("❌ Please send a voice message.")
            return str(resp)

        media_url = request.values.get("MediaUrl0")

        try:
            audio_data = requests.get(
                media_url,
                auth=HTTPBasicAuth(ACCOUNT_SID, AUTH_TOKEN)
            )

            with open("voice.ogg", "wb") as f:
                f.write(audio_data.content)

            sound = AudioSegment.from_ogg("voice.ogg")
            sound.export("voice.wav", format="wav")

            recognizer = sr.Recognizer()

            with sr.AudioFile("voice.wav") as source:
                audio = recognizer.record(source)

            text_msg = recognizer.recognize_google(audio).lower()

            print("Voice converted to:", text_msg)

        except:
            msg.body("❌ Could not understand voice.")
            return str(resp)

        finally:

            if os.path.exists("voice.ogg"):
                os.remove("voice.ogg")

            if os.path.exists("voice.wav"):
                os.remove("voice.wav")

    # FIRST USER
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
            msg.body("👤 Enter your name.")

        elif text_msg == "2":
            user_data[sender]["service"] = "Income Certificate"
            user_data[sender]["step"] = "name"
            msg.body("👤 Enter your name.")

        elif text_msg == "3":
            user_data[sender]["service"] = "Ration Card"
            user_data[sender]["step"] = "name"
            msg.body("👤 Enter your name.")

        else:
            msg.body("❌ Invalid option. Type 1, 2 or 3.")

    # NAME
    elif step == "name":

        user_data[sender]["name"] = text_msg.title()

        service = user_data[sender]["service"]

        if service == "Pension Application":
            user_data[sender]["step"] = "age"
            msg.body("🎂 Enter your age.")

        elif service == "Income Certificate":
            user_data[sender]["step"] = "occupation"
            msg.body("💼 Enter your occupation.")

        elif service == "Ration Card":
            user_data[sender]["step"] = "family"
            msg.body("👨‍👩‍👧‍👦 Number of family members?")

    # AGE VALIDATION
    elif step == "age":

        if not text_msg.isdigit():
            msg.body("❌ Enter age in numbers.")
        else:

            age = int(text_msg)

            if age < 60:
                msg.body("⚠️ Pension available only for age 60+.")
            else:
                user_data[sender]["age"] = age
                user_data[sender]["step"] = "aadhaar"
                msg.body("🆔 Enter Aadhaar number.")

    # OCCUPATION
    elif step == "occupation":

        user_data[sender]["occupation"] = text_msg
        user_data[sender]["step"] = "income"

        msg.body("💰 Enter monthly income.")

    # INCOME
    elif step == "income":

        user_data[sender]["income"] = text_msg
        user_data[sender]["step"] = "aadhaar"

        msg.body("🆔 Enter Aadhaar number.")

    # FAMILY
    elif step == "family":

        user_data[sender]["family"] = text_msg
        user_data[sender]["step"] = "aadhaar"

        msg.body("🆔 Enter Aadhaar of family head.")

    # AADHAAR VALIDATION
    elif step == "aadhaar":

        if not text_msg.isdigit() or len(text_msg) != 12:
            msg.body("❌ Aadhaar must be 12 digits.")
        else:

            user_data[sender]["aadhaar"] = text_msg

            if user_data[sender]["service"] == "Pension Application":
                user_data[sender]["step"] = "bank"
                msg.body("🏦 Enter bank account number.")
            else:
                user_data[sender]["step"] = "address"
                msg.body("📍 Enter your address.")

    # BANK
    elif step == "bank":

        user_data[sender]["bank"] = text_msg
        user_data[sender]["step"] = "address"

        msg.body("📍 Enter your address.")

    # ADDRESS
    elif step == "address":

        user_data[sender]["address"] = text_msg
        user_data[sender]["step"] = "confirm"

        d = user_data[sender]

        summary = f"Service: {d['service']}\nName: {d['name']}\n"

        if d["service"] == "Pension Application":
            summary += f"Age: {d['age']}\nBank: {d['bank']}\n"

        if d["service"] == "Income Certificate":
            summary += f"Occupation: {d['occupation']}\nIncome: {d['income']}\n"

        if d["service"] == "Ration Card":
            summary += f"Family Members: {d['family']}\n"

        summary += f"Aadhaar: {d['aadhaar']}\nAddress: {d['address']}"

        msg.body(
            f"📋 Confirm Details\n\n{summary}\n\n"
            "1️⃣ Confirm\n"
            "5️⃣ Menu"
        )

    # CONFIRM
    elif step == "confirm":

        if text_msg == "1":

            application_id = "AKS-" + str(random.randint(100000,999999))

            msg.body(
                f"✅ Application Submitted!\n\n"
                f"📌 Application ID: {application_id}\n\n"
                "Type *menu* to apply again."
            )

            user_data.pop(sender, None)

        elif text_msg == "5":

            user_data.pop(sender, None)
            msg.body("🔄 Type *menu* to restart.")

    return str(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0", port=port)
