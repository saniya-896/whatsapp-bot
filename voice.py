from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import speech_recognition as sr
from pydub import AudioSegment
import os
from requests.auth import HTTPBasicAuth

app = Flask(__name__)   # ✅ MUST be first

ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

user_data = {}


@app.route("/")
def home():
    return "Bot is running ✅"


@app.route("/whatsapp", methods=['POST'])
def whatsapp_bot():
    resp = MessagingResponse()
    msg = resp.message()

    sender = request.values.get("From")
    num_media = int(request.values.get("NumMedia", 0))
    text_msg = request.values.get("Body", "").strip().lower()

    # 🎤 VOICE INPUT
    if num_media > 0:
        media_url = request.values.get("MediaUrl0")

        audio_data = requests.get(
            media_url,
            auth=HTTPBasicAuth(ACCOUNT_SID, AUTH_TOKEN)
        )

        with open("audio.ogg", "wb") as f:
            f.write(audio_data.content)

        sound = AudioSegment.from_file("audio.ogg", format="ogg")
        sound.export("audio.wav", format="wav")

        recognizer = sr.Recognizer()

        with sr.AudioFile("audio.wav") as source:
            audio = recognizer.record(source)

        try:
            text_msg = recognizer.recognize_google(audio).lower()
        except:
            msg.body("❌ Could not understand audio.")
            return str(resp)

        os.remove("audio.ogg")
        os.remove("audio.wav")

    # MENU
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

    msg.body("Processing...")

    return str(resp)


# ✅ RUN SERVER — MUST BE LAST
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
