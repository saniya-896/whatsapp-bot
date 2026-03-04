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

# ffmpeg path for Render
AudioSegment.converter = "/usr/bin/ffmpeg"

user_data = {}

# Home
@app.route("/")
def home():
    return "WhatsApp Bot Running"

# Status
@app.route("/status")
def status():
    return {"status": "running"}

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():

    resp = MessagingResponse()
    msg = resp.message()

    sender = request.values.get("From")
    body = request.values.get("Body")
    text_msg = (body or "").strip().lower()

    num_media = int(request.values.get("NumMedia") or 0)

    print("User:", sender, "Message:", text_msg)

    # 🎤 Voice message handling
    if num_media > 0:

        content_type = request.values.get("MediaContentType0", "")

        if "audio" in content_type:

            media_url = request.values.get("MediaUrl0")

            audio = requests.get(
                media_url,
                auth=HTTPBasicAuth(ACCOUNT_SID, AUTH_TOKEN)
            )

            with open("voice.ogg", "wb") as f:
                f.write(audio.content)

            try:

                sound = AudioSegment.from_file("voice.ogg", format="ogg")
                sound.export("voice.wav", format="wav")

                recognizer = sr.Recognizer()

                with sr.AudioFile("voice.wav") as source:
                    audio_data = recognizer.record(source)

                text_msg = recognizer.recognize_google(audio_data).lower()

                print("Voice converted:", text_msg)

            except:
                msg.body("❌ Sorry, could not understand voice.")
                return str(resp)

            finally:

                if os.path.exists("voice.ogg"):
                    os.remove("voice.ogg")

                if os.path.exists("voice.wav"):
                    os.remove("voice.wav")

        else:
            msg.body("❌ Please send a voice message.")
            return str(resp)

    # Restart command
    if text_msg in ["menu", "restart", "start"]:

        user_data.pop(sender, None)

        msg.body(
            "🔄 Restarted.\n\n"
            "Type *Hi* to start again."
        )

        return str(resp)

    # First interaction
    if sender not in user_data:

        if text_msg in ["hi", "hello"]:

            user_data[sender] = {"step": "menu"}

            msg.body(
                "🙏 Welcome to E-Akshaya Digital Service\n\n"
                "1️⃣ Pension Application\n"
                "2️⃣ Income Certificate\n"
                "3️⃣ Ration Card\n\n"
                "Reply with option number or voice."
            )

        else:
            msg.body("👋 Please type or say *Hi* to start.")

        return str(resp)

    step = user_data[sender]["step"]

    # MENU
    if step == "menu":

        if "1" in text_msg:

            user_data[sender]["service"] = "Pension"
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

    # NAME
    elif step == "name":

        user_data[sender]["name"] = text_msg.title()

        service = user_data[sender]["service"]

        if service == "Pension":
            user_data[sender]["step"] = "age"
            msg.body("Please say your age.")

        elif service == "Income Certificate":
            user_data[sender]["step"] = "occupation"
            msg.body("Please say your occupation.")

        elif service == "Ration Card":
            user_data[sender]["step"] = "family"
            msg.body("How many family members?")

    # AGE
    elif step == "age":

        user_data[sender]["age"] = text_msg
        user_data[sender]["step"] = "aadhaar"

        msg.body("Please say your Aadhaar number.")

    # OCCUPATION
    elif step == "occupation":

        user_data[sender]["occupation"] = text_msg
        user_data[sender]["step"] = "income"

        msg.body("Please say your family income.")

    # INCOME
    elif step == "income":

        user_data[sender]["income"] = text_msg
        user_data[sender]["step"] = "aadhaar"

        msg.body("Please say your Aadhaar number.")

    # FAMILY MEMBERS
    elif step == "family":

        user_data[sender]["family"] = text_msg
        user_data[sender]["step"] = "aadhaar"

        msg.body("Please say your Aadhaar number.")

    # AADHAAR
    elif step == "aadhaar":

        user_data[sender]["aadhaar"] = text_msg

        service = user_data[sender]["service"]

        if service == "Pension":

            user_data[sender]["step"] = "bank"
            msg.body("Please say your bank account number.")

        else:

            user_data[sender]["step"] = "address"
            msg.body("Please say your address.")

    # BANK
    elif step == "bank":

        user_data[sender]["bank"] = text_msg
        user_data[sender]["step"] = "address"

        msg.body("Please say your address.")

    # ADDRESS
    elif step == "address":

        user_data[sender]["address"] = text_msg
        user_data[sender]["step"] = "confirm"

        d = user_data[sender]

        summary = f"Service: {d['service']}\nName: {d['name']}\n"

        if d["service"] == "Pension":
            summary += f"Age: {d['age']}\nBank: {d['bank']}\n"

        if d["service"] == "Income Certificate":
            summary += f"Occupation: {d['occupation']}\nIncome: {d['income']}\n"

        if d["service"] == "Ration Card":
            summary += f"Family Members: {d['family']}\n"

        summary += f"Aadhaar: {d['aadhaar']}\nAddress: {d['address']}"

        msg.body(
            f"📋 Confirm Details\n\n{summary}\n\n"
            "1️⃣ Confirm\n"
            "2️⃣ Restart"
        )

    # CONFIRM
    elif step == "confirm":

        if "1" in text_msg:

            app_id = "AKS-" + str(random.randint(100000, 999999))

            msg.body(
                f"✅ Application Submitted!\n\n"
                f"Application ID: {app_id}\n\n"
                "Akshaya team will process your request."
            )

            del user_data[sender]

        else:
            user_data.pop(sender, None)
            msg.body("Restarted. Say Hi again.")

    return str(resp)


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)
