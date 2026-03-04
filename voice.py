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


# Health check
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

    # Voice handling
    if num_media > 0:

        content_type = request.values.get("MediaContentType0", "")

        if "audio" not in content_type:
            msg.body("Please send a voice message.")
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

            recognizer = sr.Recognizer()

            with sr.AudioFile("voice.wav") as source:
                audio = recognizer.record(source)

            text_msg = recognizer.recognize_google(audio).lower()

        except:
            msg.body("Could not understand voice.")
            return str(resp)

        finally:

            if os.path.exists("voice.ogg"):
                os.remove("voice.ogg")

            if os.path.exists("voice.wav"):
                os.remove("voice.wav")

    # restart
    if text_msg in ["menu", "restart", "start"]:
        user_data.pop(sender, None)
        msg.body("Service restarted. Type Hi to start.")
        return str(resp)

    # first message
    if sender not in user_data:

        if text_msg in ["hi", "hello"]:

            user_data[sender] = {"step": "menu"}

            msg.body(
                "Welcome to E-Akshaya Digital Service\n\n"
                "1 Pension Application\n"
                "2 Income Certificate\n"
                "3 Ration Card\n\n"
                "Reply with option number."
            )

        else:
            msg.body("Please type Hi to start.")

        return str(resp)

    step = user_data[sender]["step"]

    # MENU
    if step == "menu":

        if "1" in text_msg:
            user_data[sender]["service"] = "Pension"
            user_data[sender]["step"] = "name"
            msg.body("Please enter your name.")

        elif "2" in text_msg:
            user_data[sender]["service"] = "Income Certificate"
            user_data[sender]["step"] = "name"
            msg.body("Please enter your name.")

        elif "3" in text_msg:
            user_data[sender]["service"] = "Ration Card"
            user_data[sender]["step"] = "name"
            msg.body("Please enter your name.")

        else:
            msg.body("Invalid option.")

    # NAME
    elif step == "name":

        user_data[sender]["name"] = text_msg.title()

        service = user_data[sender]["service"]

        if service == "Pension":
            user_data[sender]["step"] = "age"
            msg.body("Enter your age.")

        elif service == "Income Certificate":
            user_data[sender]["step"] = "occupation"
            msg.body("Enter your occupation.")

        elif service == "Ration Card":
            user_data[sender]["step"] = "family_members"
            msg.body("How many family members?")

    # AGE (PENSION)
    elif step == "age":

        user_data[sender]["age"] = text_msg
        user_data[sender]["step"] = "aadhaar"
        msg.body("Enter Aadhaar number.")

    # OCCUPATION (INCOME)
    elif step == "occupation":

        user_data[sender]["occupation"] = text_msg
        user_data[sender]["step"] = "family_income"
        msg.body("Enter family monthly income.")

    # FAMILY INCOME
    elif step == "family_income":

        user_data[sender]["income"] = text_msg
        user_data[sender]["step"] = "aadhaar"
        msg.body("Enter Aadhaar number.")

    # FAMILY MEMBERS (RATION)
    elif step == "family_members":

        user_data[sender]["family_members"] = text_msg
        user_data[sender]["step"] = "aadhaar"
        msg.body("Enter Aadhaar number.")

    # AADHAAR
    elif step == "aadhaar":

        user_data[sender]["aadhaar"] = text_msg

        service = user_data[sender]["service"]

        if service == "Pension":
            user_data[sender]["step"] = "bank"
            msg.body("Enter bank account number.")

        else:
            user_data[sender]["step"] = "address"
            msg.body("Enter your address.")

    # BANK
    elif step == "bank":

        user_data[sender]["bank"] = text_msg
        user_data[sender]["step"] = "address"
        msg.body("Enter your address.")

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
            summary += f"Family Members: {d['family_members']}\n"

        summary += f"Aadhaar: {d['aadhaar']}\nAddress: {d['address']}"

        msg.body(
            f"Confirm Details:\n\n{summary}\n\n"
            "1 Confirm\n"
            "2 Edit Name\n"
            "3 Edit Aadhaar\n"
            "4 Edit Address"
        )

    # CONFIRM
    elif step == "confirm":

        if "1" in text_msg:

            d = user_data[sender]

            app_id = "AKS-" + str(random.randint(100000, 999999))

            msg.body(
                f"Application Submitted Successfully\n\n"
                f"Application ID: {app_id}\n\n"
                "Our Akshaya team will contact you."
            )

            del user_data[sender]

        elif "2" in text_msg:
            user_data[sender]["step"] = "name"
            msg.body("Enter correct name.")

        elif "3" in text_msg:
            user_data[sender]["step"] = "aadhaar"
            msg.body("Enter correct Aadhaar.")

        elif "4" in text_msg:
            user_data[sender]["step"] = "address"
            msg.body("Enter correct address.")

        else:
            msg.body("Invalid option.")

    return str(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
