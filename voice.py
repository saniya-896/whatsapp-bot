from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import speech_recognition as sr
from pydub import AudioSegment
import os
import random
import csv
from requests.auth import HTTPBasicAuth

app = Flask(__name__)

ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

AudioSegment.converter = "/usr/bin/ffmpeg"

user_data = {}

ADMIN_NUMBER = "whatsapp:+919745658544"

# SAVE TO CSV
def save_application(data):

    with open("applications.csv", "a", newline="") as file:

        writer = csv.writer(file)

        writer.writerow([
            data.get("service"),
            data.get("name"),
            data.get("aadhaar"),
            data.get("address")
        ])


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

    # HI / HELLO START
    if text_msg in ["hi", "hello", "hai"]:

        user_data.pop(sender, None)

        user_data[sender] = {"step": "menu"}

        msg.body(
            "🙏 Welcome to E-Akshaya Digital Service\n\n"
            "1️⃣ Pension Application\n"
            "2️⃣ Income Certificate\n"
            "3️⃣ Ration Card\n\n"
            "Reply with option number."
        )

        return str(resp)

    # ADMIN VIEW
    if sender == ADMIN_NUMBER and text_msg == "admin":

        try:

            with open("applications.csv", "r") as file:
                reader = csv.reader(file)
                rows = list(reader)

            if not rows:
                msg.body("No applications found.")
            else:

                result = "Recent Applications\n\n"

                for r in rows[-5:]:
                    result += (
                        f"Service: {r[0]}\n"
                        f"Name: {r[1]}\n"
                        f"Aadhaar: {r[2]}\n"
                        f"Address: {r[3]}\n\n"
                    )

                msg.body(result)

        except:
            msg.body("No data available.")

        return str(resp)

    # CANCEL
    if text_msg == "cancel":
        user_data.pop(sender, None)

        msg.body("Application cancelled.\n\nType menu to start again.")
        return str(resp)

    # MENU
    if text_msg in ["menu", "restart", "start"]:

        user_data.pop(sender, None)

        user_data[sender] = {"step": "menu"}

        msg.body(
            "Welcome to E-Akshaya Digital Service\n\n"
            "1 Pension Application\n"
            "2 Income Certificate\n"
            "3 Ration Card\n\n"
            "Reply with option number."
        )

        return str(resp)

    # VOICE HANDLING
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

            sound = AudioSegment.from_file("voice.ogg")
            sound.export("voice.wav", format="wav")

            recognizer = sr.Recognizer()

            with sr.AudioFile("voice.wav") as source:
                audio = recognizer.record(source)

            try:
                text_msg = recognizer.recognize_google(audio, language="ml-IN").lower()
            except:
                text_msg = recognizer.recognize_google(audio, language="en-IN").lower()

            print("VOICE TEXT:", text_msg)

        except:
            msg.body("Could not understand voice.")
            return str(resp)

        finally:

            if os.path.exists("voice.ogg"):
                os.remove("voice.ogg")

            if os.path.exists("voice.wav"):
                os.remove("voice.wav")

    # FIRST TIME
    if sender not in user_data:

        user_data[sender] = {"step": "menu"}

        msg.body(
            "Welcome to E-Akshaya Digital Service\n\n"
            "1 Pension Application\n"
            "2 Income Certificate\n"
            "3 Ration Card"
        )

        return str(resp)

    step = user_data[sender]["step"]

    # MENU
    if step == "menu":

        if text_msg == "1":
            user_data[sender]["service"] = "Pension Application"
            user_data[sender]["step"] = "name"
            msg.body("Enter your name.")

        elif text_msg == "2":
            user_data[sender]["service"] = "Income Certificate"
            user_data[sender]["step"] = "name"
            msg.body("Enter your name.")

        elif text_msg == "3":
            user_data[sender]["service"] = "Ration Card"
            user_data[sender]["step"] = "name"
            msg.body("Enter your name.")

        else:
            msg.body("Invalid option. Type 1,2 or 3.")

    # NAME
    elif step == "name":

        user_data[sender]["name"] = text_msg.title()

        service = user_data[sender]["service"]

        if service == "Pension Application":
            user_data[sender]["step"] = "age"
            msg.body("Enter your age.")

        elif service == "Income Certificate":
            user_data[sender]["step"] = "occupation"
            msg.body("Enter your occupation.")

        elif service == "Ration Card":
            user_data[sender]["step"] = "family"
            msg.body("Number of family members?")

    # AGE
    elif step == "age":

        if not text_msg.isdigit():
            msg.body("Enter age in numbers.")
        else:

            age = int(text_msg)

            if age < 60:
                msg.body("Pension available only for age 60+.")
            else:

                user_data[sender]["age"] = age
                user_data[sender]["step"] = "aadhaar"
                msg.body("Enter Aadhaar number.")

    # OCCUPATION
    elif step == "occupation":

        user_data[sender]["occupation"] = text_msg
        user_data[sender]["step"] = "income"

        msg.body("Enter monthly income.")

    # INCOME
    elif step == "income":

        user_data[sender]["income"] = text_msg
        user_data[sender]["step"] = "aadhaar"

        msg.body("Enter Aadhaar number.")

    # FAMILY
    elif step == "family":

        user_data[sender]["family"] = text_msg
        user_data[sender]["step"] = "aadhaar"

        msg.body("Enter Aadhaar of family head.")

    # AADHAAR
    elif step == "aadhaar":

        if not text_msg.isdigit() or len(text_msg) != 12:
            msg.body("Invalid Aadhaar. Enter 12 digits.")
        else:

            user_data[sender]["aadhaar"] = text_msg

            if user_data[sender]["service"] == "Pension Application":
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

        summary = f"Service: {d['service']}\nName: {d['name']}\nAadhaar: {d['aadhaar']}\nAddress: {d['address']}"

        msg.body(
            f"Confirm Your Details\n\n{summary}\n\n"
            "1 Confirm\n"
            "2 Edit Name\n"
            "3 Edit Aadhaar\n"
            "4 Edit Address\n"
            "5 Menu"
        )

    # CONFIRM
    elif step == "confirm":

        if text_msg == "1":

            save_application(user_data[sender])

            application_id = "AKS-" + str(random.randint(100000, 999999))

            msg.body(
                f"Application Submitted!\n\n"
                f"Application ID: {application_id}\n\n"
                "Type menu to apply again."
            )

            user_data.pop(sender, None)

        elif text_msg == "2":
            user_data[sender]["step"] = "edit_name"
            msg.body("Enter correct name.")

        elif text_msg == "3":
            user_data[sender]["step"] = "edit_aadhaar"
            msg.body("Enter correct Aadhaar.")

        elif text_msg == "4":
            user_data[sender]["step"] = "edit_address"
            msg.body("Enter correct address.")

        elif text_msg == "5":
            user_data.pop(sender, None)
            msg.body("Type menu to start again.")

    # EDIT NAME
    elif step == "edit_name":

        user_data[sender]["name"] = text_msg.title()
        user_data[sender]["step"] = "confirm"

        msg.body("Name updated. Confirm again.")

    # EDIT AADHAAR
    elif step == "edit_aadhaar":

        user_data[sender]["aadhaar"] = text_msg
        user_data[sender]["step"] = "confirm"

        msg.body("Aadhaar updated. Confirm again.")

    # EDIT ADDRESS
    elif step == "edit_address":

        user_data[sender]["address"] = text_msg
        user_data[sender]["step"] = "confirm"

        msg.body("Address updated. Confirm again.")

    return str(resp)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
