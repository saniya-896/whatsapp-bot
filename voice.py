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

user_data = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():

    resp = MessagingResponse()
    msg = resp.message()

    sender = request.values.get("From")

    body = request.values.get("Body")
    text_msg = (body or "").strip().lower()

    num_media = int(request.values.get("NumMedia", 0))

    # 🔄 Restart command
    if text_msg in ["menu", "restart", "start"]:
        user_data.pop(sender, None)
        resp.message("🔄 Service restarted. Please type *Hi*.")
        return str(resp)

    # 🎤 Voice Input
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

            sound = AudioSegment.from_file("voice.ogg", format="ogg")
            sound.export("voice.wav", format="wav")

            r = sr.Recognizer()

            with sr.AudioFile("voice.wav") as source:
                audio = r.record(source)

            text_msg = r.recognize_google(audio).lower()

        except:
            msg.body("❌ Voice not clear. Please send again.")
            return str(resp)

        finally:

            if os.path.exists("voice.ogg"):
                os.remove("voice.ogg")

            if os.path.exists("voice.wav"):
                os.remove("voice.wav")

    # 🟢 Start only with Hi / Hello
    if sender not in user_data:

        if text_msg in ["hi", "hello"]:
            user_data[sender] = {"step": "menu"}

            msg.body(
                "🙏 Welcome to E-Akshaya Digital Service\n\n"
                "1️⃣ Pension Application\n"
                "2️⃣ Income Certificate\n"
                "3️⃣ Ration Card\n\n"
                "Reply with option number."
            )

        else:
            msg.body("👋 Please type *Hi* or *Hello* to start.")

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

    # 🟢 ADDRESS
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
    elif step == "confirm":

        if "1" in text_msg:

            d = user_data[sender]
            application_id = "AKS-" + str(random.randint(100000, 999999))

            msg.body(
                f"✅ {d['service']} Submitted Successfully!\n\n"
                f"Name: {d['name']}\n"
                f"Aadhaar: {d['aadhaar']}\n"
                f"Address: {d['address']}\n\n"
                f"Application ID: {application_id}"
            )

            del user_data[sender]

        elif "2" in text_msg:
            user_data[sender]["step"] = "edit_name"
            msg.body("Please say your correct name.")

        elif "3" in text_msg:
            user_data[sender]["step"] = "edit_aadhaar"
            msg.body("Please say your correct Aadhaar number.")

        elif "4" in text_msg:
            user_data[sender]["step"] = "edit_address"
            msg.body("Please say your correct address.")

        else:
            msg.body("❌ Invalid option.")

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

    return str(resp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
