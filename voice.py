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

app = Flask(__name__)

ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

AudioSegment.converter = "/usr/bin/ffmpeg"

user_data = {}

ADMIN_NUMBERS = ["whatsapp:+919633406610"]


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
        writer=csv.writer(f)
        writer.writerows(rows)


# ---------------- PDF DOWNLOAD ----------------

@app.route("/pdf/<filename>")
def get_pdf(filename):

    file_path = f"/tmp/{filename}"

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)

    return "PDF not found",404


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

    user_text = (body or "").strip().lower()

    # CANCEL APPLICATION
    if user_text == "cancel":

        if sender in user_data:
            user_data.pop(sender)

        msg.body("❌ Application cancelled.\n\nType *menu* to start again.")
        return str(resp)

    text_msg = normalize_command(user_text)

    num_media = int(request.values.get("NumMedia") or 0)


# ---------------- VOICE SUPPORT ----------------

    if num_media > 0:

        content_type = request.values.get("MediaContentType0","")

        if "audio" not in content_type:
            msg.body("❌ Please send a voice message")
            return str(resp)

        media_url = request.values.get("MediaUrl0")

        voice_ogg="/tmp/voice.ogg"
        voice_wav="/tmp/voice.wav"

        audio_data = requests.get(
            media_url,
            auth=HTTPBasicAuth(ACCOUNT_SID, AUTH_TOKEN),
            stream=True
        )

        with open(voice_ogg,"wb") as f:
            for chunk in audio_data.iter_content(1024):
                f.write(chunk)

        if os.path.getsize(voice_ogg)==0:
            msg.body("❌ Voice empty. Send again.")
            return str(resp)

        try:

            sound = AudioSegment.from_file(voice_ogg)
            sound = sound.set_channels(1)
            sound = sound.set_frame_rate(16000)
            sound.export(voice_wav, format="wav")

            recognizer = sr.Recognizer()

            with sr.AudioFile(voice_wav) as source:
                audio = recognizer.record(source)

            try:
                spoken = recognizer.recognize_google(audio, language="ml-IN").lower()
            except:
                spoken = recognizer.recognize_google(audio, language="en-IN").lower()

            print("VOICE:",spoken)

            user_text = spoken
            text_msg = normalize_command(spoken)

        except Exception as e:
            print(e)
            msg.body("❌ Voice not understood")
            return str(resp)

        finally:

            if os.path.exists(voice_ogg):
                os.remove(voice_ogg)

            if os.path.exists(voice_wav):
                os.remove(voice_wav)


# ---------------- STATUS CHECK ----------------

    if user_text.startswith("status"):

        parts = user_text.split()

        if len(parts) != 2:
            msg.body("Use: status AKS-123456")
            return str(resp)

        app_id = parts[1].upper()

        if not os.path.exists("applications.csv"):
            msg.body("Database empty")
            return str(resp)

        with open("applications.csv","r") as f:

            reader = csv.reader(f)

            for row in reader:

                if len(row) < 6:
                    continue

                if row[0] == app_id:

                    msg.body(
                        f"Application Status\n\n"
                        f"ID: {row[0]}\n"
                        f"Service: {row[1]}\n"
                        f"Name: {row[2]}\n"
                        f"Status: {row[5]}"
                    )

                    return str(resp)

        msg.body("Application not found")
        return str(resp)


# ---------------- ADMIN ----------------

    if sender in ADMIN_NUMBERS:

        if text_msg == "admin":

            if not os.path.exists("applications.csv"):
                msg.body("No applications yet")
                return str(resp)

            with open("applications.csv","r") as f:
                rows=list(csv.reader(f))

            text="Recent Applications\n\n"

            for r in rows[-5:]:

                if len(r) < 6:
                    continue

                text+=(
                    f"ID:{r[0]}\n"
                    f"Service:{r[1]}\n"
                    f"Name:{r[2]}\n"
                    f"Status:{r[5]}\n\n"
                )

            msg.body(text)
            return str(resp)


# ---------------- START ----------------

    if text_msg in ["hi","hello","menu"]:

        user_data[sender]={"step":"menu"}

        msg.body(
            "Welcome to E-Akshaya Digital Service\n\n"
            "1️⃣ Pension Application\n"
            "2️⃣ Income Certificate\n"
            "3️⃣ Ration Card"
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
            msg.body("Enter your name")

        elif text_msg=="2":
            user_data[sender]["service"]="Income Certificate"
            user_data[sender]["step"]="name"
            msg.body("Enter your name")

        elif text_msg=="3":
            user_data[sender]["service"]="Ration Card"
            user_data[sender]["step"]="name"
            msg.body("Enter your name")


# ---------------- NAME ----------------

    elif step=="name":

        user_data[sender]["name"]=text_msg.title()
        user_data[sender]["step"]="aadhaar"

        msg.body("Enter Aadhaar number")


# ---------------- AADHAAR ----------------

    elif step=="aadhaar":

        if not text_msg.isdigit() or len(text_msg)!=12:
            msg.body("Enter valid Aadhaar")
        else:

            user_data[sender]["aadhaar"]=text_msg
            user_data[sender]["step"]="address"
            msg.body("Enter address")


# ---------------- ADDRESS ----------------

    elif step=="address":

        user_data[sender]["address"]=text_msg
        user_data[sender]["step"]="confirm"

        d=user_data[sender]

        msg.body(
            f"Confirm Details\n\n"
            f"{d['service']}\n"
            f"{d['name']}\n"
            f"{d['aadhaar']}\n"
            f"{d['address']}\n\n"
            "1 Confirm\n2 Edit Name\n3 Edit Aadhaar\n4 Edit Address"
        )


# ---------------- CONFIRM ----------------

    elif step=="confirm":

        if text_msg=="1":

            app_id="AKS-"+str(random.randint(100000,999999))

            save_application(user_data[sender],app_id)

            generate_pdf(user_data[sender],app_id)

            base_url=request.host_url
            pdf_url=f"{base_url}pdf/{app_id}.pdf"

            msg.body(
                f"Application Submitted\n\n"
                f"Application ID: {app_id}\n"
                f"Check status:\nstatus {app_id}"
            )

            try:
                client.messages.create(
                    from_="whatsapp:+14155238886",
                    to=sender,
                    body="Your Application Receipt",
                    media_url=[pdf_url]
                )
            except:
                pass

            user_data.pop(sender)

            return str(resp)

        elif text_msg=="2":
            user_data[sender]["step"]="name"
            msg.body("Enter correct name")

        elif text_msg=="3":
            user_data[sender]["step"]="aadhaar"
            msg.body("Enter correct Aadhaar number")

        elif text_msg=="4":
            user_data[sender]["step"]="address"
            msg.body("Enter correct address")

    return str(resp)


if __name__=="__main__":

    port=int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port)
