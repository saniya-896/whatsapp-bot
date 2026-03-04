from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import speech_recognition as sr
from pydub import AudioSegment
import os
from requests.auth import HTTPBasicAuth

app = Flask(__name__)

# 🔐 Environment variables (set in Render)
ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

user_data = {}


@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():

    resp = MessagingResponse()
    msg = resp.message()

    sender = request.values.get("From")
    num_media = int(request.values.get("NumMedia", 0))
    text_msg = request.values.get("Body", "").strip().lower()

    # 🎤 ===== VOICE INPUT =====
    if num_media > 0:

        content_type = request.values.get("MediaContentType0", "")

        if "audio" not in content_type:
            msg.body("❌ Please send a voice message.")
            return str(resp)

        media_url = request.values.get("MediaUrl0")

        audio_data = requests.get(
            media_url,
            auth=HTTPBasicAuth(ACCOUNT_SID, AUTH_TOKEN)
        )

        with open("voice.ogg", "wb") as f:
            f.write(audio_data.content)

        try:
            # Convert OGG → WAV
            sound = AudioSegment.from_file("voice.ogg", format="ogg")
            sound.export("voice.wav", format="wav")

            recognizer = sr.Recognizer()

            with sr.AudioFile("voice.wav") as source:
                audio = recognizer.record(source)

            text_msg = recognizer.recognize_google(audio).lower()

        except Exception:
            msg.body("❌ Could not understand voice.")
            return str(resp)

        finally:
            if os.path.exists("voice.ogg"):
                os.remove("voice.ogg")
            if os.path.exists("voice.wav"):
                os.remove("voice.wav")

    # 🟢 NEW USER → MENU
    if sender not in user_data:
        user_data[sender] = {"step": "menu"}

        msg.body(
            "🙏 Welcome to E-Akshaya Digital Service\n\n"
            "1️⃣ Pension Application\n"
            "2️⃣ Income Certificate\n"
            "3️⃣ Ration Card\n\n"
            "Reply with option number."
        )
        return str(resp)

    step = user_data[sender]["step"]

    # 🟢 MENU
    if step == "menu":

        if "1" in text_msg:
            user_data[sender]["service"] = "Pension Application"
            user_data[sender]["step"] = "name"
            msg.body("Please say your name.")

        elif "2" in text_msg:
            user_data[sender]["service"] = "Income Certificate"
            user_data[sender]["step"] = "name"
            msg.body("Please say your name.")

        elif "3" in text_msg:
            user_data[sender]["service"] = "Ration Card"
            user_data[sender]["step"] = "name"
            msg.body("Please say your name.")

        else:
            msg.body("❌ Invalid option.")

    # 🟢 NAME
    elif step == "name":
        user_data[sender]["name"] = text_msg.title()
        user_data[sender]["step"] = "aadhaar"
        msg.body("Please say your Aadhaar number.")

    # 🟢 AADHAAR
    elif step == "aadhaar":
        user_data[sender]["aadhaar"] = text_msg
        user_data[sender]["step"] = "address"
        msg.body("Please say your address.")

    # 🟢 ADDRESS → CONFIRM
    elif step == "address":

        user_data[sender]["address"] = text_msg
        user_data[sender]["step"] = "confirm"

        d = user_data[sender]

        msg.body(
            f"📋 Please Confirm Your Details:\n\n"
            f"Service: {d['service']}\n"
            f"Name: {d['name']}\n"
            f"Aadhaar: {d['aadhaar']}\n"
            f"Address: {d['address']}\n\n"
            "1️⃣ Confirm\n"
            "2️⃣ Edit Name\n"
            "3️⃣ Edit Aadhaar\n"
            "4️⃣ Edit Address"
        )

    # 🟢 CONFIRM
   # 🟢 EDIT NAME
elif step == "edit_name":

    user_data[sender]["name"] = text_msg.title()
    user_data[sender]["step"] = "confirm"

    d = user_data[sender]

    msg.body(
        f"📋 Updated Details:\n\n"
        f"Service: {d['service']}\n"
        f"Name: {d['name']}\n"
        f"Aadhaar: {d['aadhaar']}\n"
        f"Address: {d['address']}\n\n"
        "1️⃣ Confirm\n"
        "2️⃣ Edit Name\n"
        "3️⃣ Edit Aadhaar\n"
        "4️⃣ Edit Address"
    )


# 🟢 EDIT AADHAAR
elif step == "edit_aadhaar":

    user_data[sender]["aadhaar"] = text_msg
    user_data[sender]["step"] = "confirm"

    d = user_data[sender]

    msg.body(
        f"📋 Updated Details:\n\n"
        f"Service: {d['service']}\n"
        f"Name: {d['name']}\n"
        f"Aadhaar: {d['aadhaar']}\n"
        f"Address: {d['address']}\n\n"
        "1️⃣ Confirm\n"
        "2️⃣ Edit Name\n"
        "3️⃣ Edit Aadhaar\n"
        "4️⃣ Edit Address"
    )


# 🟢 EDIT ADDRESS
elif step == "edit_address":

    user_data[sender]["address"] = text_msg
    user_data[sender]["step"] = "confirm"

    d = user_data[sender]

    msg.body(
        f"📋 Updated Details:\n\n"
        f"Service: {d['service']}\n"
        f"Name: {d['name']}\n"
        f"Aadhaar: {d['aadhaar']}\n"
        f"Address: {d['address']}\n\n"
        "1️⃣ Confirm\n"
        "2️⃣ Edit Name\n"
        "3️⃣ Edit Aadhaar\n"
        "4️⃣ Edit Address"
    )

    # 🟢 FINAL SUBMIT
    elif step == "submit":

        d = user_data[sender]

        msg.body(
            f"✅ {d['service']} Submitted Successfully!\n\n"
            f"Name: {d['name']}\n"
            f"Aadhaar: {d['aadhaar']}\n"
            f"Address: {d['address']}\n\n"
            f"Application ID: AKS{sender[-4:]}"
        )

        del user_data[sender]

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


