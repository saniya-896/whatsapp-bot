from flask import Flask, request, send_file
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import requests
import speech_recognition as sr
from pydub import AudioSegment
import os
import random
import csv
from requests.auth import HTTPBasicAuth
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from gtts import gTTS

app = Flask(__name__)

ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

AudioSegment.converter = "/usr/bin/ffmpeg"

user_data = {}

ADMIN_NUMBERS = ["whatsapp:+919633406610"]


# ---------------- VOICE CREATION ----------------

def create_voice(text, sender):

    filename = f"/tmp/{sender.replace(':','')}.mp3"

    tts = gTTS(text=text, lang="ml")

    tts.save(filename)

    return filename


def send_voice(msg, text, sender):

    voice_file = create_voice(text, sender)

    audio_url = f"https://whatsapp-bot-mr7x.onrender.com/audio/{os.path.basename(voice_file)}"

    msg.body(text)

    msg.media(audio_url)


# ---------------- AUDIO ROUTE ----------------

@app.route("/audio/<filename>")
def get_audio(filename):

    path = f"/tmp/{filename}"

    if os.path.exists(path):
        return send_file(path, mimetype="audio/mpeg")

    return "Audio not found",404


# ---------------- NORMALIZE COMMAND ----------------

def normalize_command(text):

    text = text.lower()

    if any(w in text for w in ["pension","pension venam","പെൻഷൻ"]):
        return "1"

    if any(w in text for w in ["income","income certificate","ഇൻകം"]):
        return "2"

    if any(w in text for w in ["ration","ration card","റേഷൻ"]):
        return "3"

    return text


# ---------------- CONFIRM SCREEN ----------------

def show_confirm(msg, data):

    msg.body(
        f"Confirm Details\n\n"
        f"Service: {data['service']}\n"
        f"Name: {data['name']}\n"
        f"Aadhaar: {data['aadhaar']}\n"
        f"Address: {data['address']}\n\n"
        "1 Confirm\n"
        "2 Edit Name\n"
        "3 Edit Aadhaar\n"
        "4 Edit Address\n"
        "5 Cancel Application"
    )


# ---------------- PDF GENERATION ----------------

def generate_pdf(data, app_id):

    filename = f"/tmp/{app_id}.pdf"

    styles = getSampleStyleSheet()

    elements = []

    elements.append(Paragraph("E-Akshaya Digital Service Application", styles['Title']))
    elements.append(Spacer(1,20))

    elements.append(Paragraph(f"Application ID: {app_id}", styles['Normal']))
    elements.append(Paragraph(f"Service: {data['service']}", styles['Normal']))
    elements.append(Paragraph(f"Name: {data['name']}", styles['Normal']))
    elements.append(Paragraph(f"Aadhaar: {data['aadhaar']}", styles['Normal']))
    elements.append(Paragraph(f"Address: {data['address']}", styles['Normal']))
    elements.append(Paragraph("Status: Submitted", styles['Normal']))

    pdf = SimpleDocTemplate(filename)
    pdf.build(elements)

    return filename


# ---------------- SAVE CSV ----------------

def save_application(data, app_id):

    file_exists = os.path.exists("applications.csv")

    with open("applications.csv","a",newline="") as f:

        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["ID","Service","Name","Aadhaar","Address","Status"])

        writer.writerow([
            app_id,
            data["service"],
            data["name"],
            data["aadhaar"],
            data["address"],
            "Submitted"
        ])


# ---------------- UPDATE STATUS ----------------

def update_status(app_id,new_status):

    if not os.path.exists("applications.csv"):
        return

    rows=[]

    with open("applications.csv","r") as f:
        rows=list(csv.reader(f))

    for r in rows:

        if len(r)<6:
            continue

        if r[0]==app_id:
            r[5]=new_status

    with open("applications.csv","w",newline="") as f:
        csv.writer(f).writerows(rows)


# ---------------- PDF DOWNLOAD ----------------

@app.route("/pdf/<filename>")
def get_pdf(filename):

    file_path = f"/tmp/{filename}"

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)

    return "PDF not found", 404


# ---------------- HOME ----------------

@app.route("/")
def home():
    return "WhatsApp Bot Running"


# ---------------- WHATSAPP BOT ----------------

@app.route("/whatsapp",methods=["POST"])
def whatsapp_bot():

    resp = MessagingResponse()
    msg = resp.message()

    sender = request.values.get("From")
    body = request.values.get("Body")

    user_text = (body or "").strip()
    text_msg = normalize_command(user_text)

    num_media = int(request.values.get("NumMedia") or 0)


# ---------------- VOICE INPUT ----------------

    if num_media > 0:

        media_url = request.values.get("MediaUrl0")

        audio_data = requests.get(
            media_url,
            auth=HTTPBasicAuth(ACCOUNT_SID, AUTH_TOKEN)
        )

        voice_file = f"/tmp/{sender.replace(':','')}.ogg"

        with open(voice_file,"wb") as f:
            f.write(audio_data.content)

        try:

            sound = AudioSegment.from_file(voice_file)
            wav_file = voice_file.replace(".ogg",".wav")
            sound.export(wav_file, format="wav")

            recognizer = sr.Recognizer()

            with sr.AudioFile(wav_file) as source:
                audio = recognizer.record(source)

            spoken = recognizer.recognize_google(audio, language="ml-IN")

            user_text = spoken
            text_msg = normalize_command(spoken)

        except:
            msg.body("Voice not understood")
            return str(resp)


# ---------------- START ----------------

    if text_msg in ["hi","hello","menu"]:

        user_data[sender]={"step":"menu"}

        send_voice(
            msg,
            "ഇ അക്ഷയ ഡിജിറ്റൽ സർവീസിലേക്ക് സ്വാഗതം. ഒന്ന് പെൻഷൻ. രണ്ട് ഇൻകം സർട്ടിഫിക്കറ്റ്. മൂന്ന് റേഷൻ കാർഡ്.",
            sender
        )

        return str(resp)


# ---------------- USER INIT ----------------

    if sender not in user_data:
        user_data[sender]={"step":"menu"}
        msg.body("Type menu to start")
        return str(resp)

    step=user_data[sender]["step"]


# ---------------- MENU ----------------

    if step=="menu":

        if text_msg=="1":
            user_data[sender]["service"]="Pension"
            user_data[sender]["step"]="name"
            send_voice(msg,"നിങ്ങളുടെ പേര് നൽകുക",sender)

        elif text_msg=="2":
            user_data[sender]["service"]="Income Certificate"
            user_data[sender]["step"]="name"
            send_voice(msg,"നിങ്ങളുടെ പേര് നൽകുക",sender)

        elif text_msg=="3":
            user_data[sender]["service"]="Ration Card"
            user_data[sender]["step"]="name"
            send_voice(msg,"നിങ്ങളുടെ പേര് നൽകുക",sender)


# ---------------- NAME ----------------

    elif step=="name":

        user_data[sender]["name"]=user_text.title()

        if user_data[sender]["service"]=="Pension":
            user_data[sender]["step"]="age"
            send_voice(msg,"നിങ്ങളുടെ വയസ് നൽകുക",sender)
        else:
            user_data[sender]["step"]="aadhaar"
            send_voice(msg,"ആധാർ നമ്പർ നൽകുക",sender)


# ---------------- AGE ----------------

    elif step=="age":

        if not user_text.isdigit():
            msg.body("Enter valid age")

        else:

            age=int(user_text)

            if age<50:
                msg.body("Pension only for age 50+")
            else:
                user_data[sender]["age"]=age
                user_data[sender]["step"]="aadhaar"
                send_voice(msg,"ആധാർ നമ്പർ നൽകുക",sender)


# ---------------- AADHAAR ----------------

    elif step=="aadhaar":

        if not user_text.isdigit() or len(user_text)!=12:
            msg.body("Enter valid 12 digit Aadhaar")

        else:
            user_data[sender]["aadhaar"]=user_text
            user_data[sender]["step"]="address"
            send_voice(msg,"നിങ്ങളുടെ വിലാസം നൽകുക",sender)


# ---------------- ADDRESS ----------------

    elif step=="address":

        user_data[sender]["address"]=user_text

        user_data[sender]["step"]="confirm"

        show_confirm(msg,user_data[sender])


# ---------------- CONFIRM ----------------

    elif step=="confirm":

        if text_msg=="1":

            app_id="AKS-"+str(random.randint(100000,999999))

            save_application(user_data[sender],app_id)

            generate_pdf(user_data[sender],app_id)

            pdf_url = f"https://whatsapp-bot-mr7x.onrender.com/pdf/{app_id}.pdf"

            msg.body(
                f"Application Submitted\n\n"
                f"Application ID: {app_id}\n"
                f"Check status:\nstatus {app_id}"
            )

            msg.media(pdf_url)

            user_data.pop(sender)

        elif text_msg=="5":
            user_data.pop(sender)
            msg.body("Application cancelled")

    return str(resp)


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
