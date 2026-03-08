from flask import Flask, request, send_file
from twilio.twiml.messaging_response import MessagingResponse
import os
import csv
import random
import requests
import speech_recognition as sr
from pydub import AudioSegment
from langdetect import detect
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

user_data = {}

ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

ADMIN_NUMBERS = ["whatsapp:+919633406610"]

# ---------------- LANGUAGE DETECTION ----------------

def detect_language(text):
    try:
        return detect(text)
    except:
        return "en"

# ---------------- MANGLISH → MALAYALAM ----------------

def manglish_to_malayalam(text):
    try:
        return transliterate(text, sanscript.ITRANS, sanscript.MALAYALAM)
    except:
        return text

# ---------------- SPEECH TO TEXT ----------------

def speech_to_text(audio_file):

    r = sr.Recognizer()

    with sr.AudioFile(audio_file) as source:
        audio = r.record(source)

    try:
        return r.recognize_google(audio, language="ml-IN").lower()
    except:
        return ""

# ---------------- PDF GENERATION ----------------

def generate_pdf(data, app_id):

    filename=f"/tmp/{app_id}.pdf"

    styles=getSampleStyleSheet()

    elements=[]
    elements.append(Paragraph("E-Akshaya Digital Service Application",styles['Title']))
    elements.append(Spacer(1,20))

    elements.append(Paragraph(f"Application ID : {app_id}",styles['Normal']))
    elements.append(Spacer(1,10))

    for k,v in data.items():
        if k!="step":
            elements.append(Paragraph(f"{k.capitalize()} : {v}",styles['Normal']))

    pdf=SimpleDocTemplate(filename)
    pdf.build(elements)

    return filename

# ---------------- SAVE CSV ----------------

def save_application(data,app_id):

    file_exists=os.path.exists("applications.csv")

    with open("applications.csv","a",newline="") as f:

        writer=csv.writer(f)

        if not file_exists:
            writer.writerow(["ID","Service","Name","Aadhaar","Address","Status"])

        writer.writerow([
            app_id,
            data.get("service",""),
            data.get("name",""),
            data.get("aadhaar",""),
            data.get("address",""),
            "Submitted"
        ])

# ---------------- STATUS ----------------

def check_status(app_id):

    if not os.path.exists("applications.csv"):
        return None

    with open("applications.csv","r") as f:

        reader=csv.reader(f)

        for r in reader:
            if len(r)>=6 and r[0]==app_id:
                return r

    return None

# ---------------- UPDATE STATUS ----------------

def update_status(app_id,new_status):

    if not os.path.exists("applications.csv"):
        return

    rows=[]

    with open("applications.csv","r") as f:
        rows=list(csv.reader(f))

    for r in rows:
        if len(r)>=6 and r[0]==app_id:
            r[5]=new_status

    with open("applications.csv","w",newline="") as f:
        csv.writer(f).writerows(rows)

# ---------------- CONFIRM SCREEN ----------------

def show_confirmation(sender,msg):

    d=user_data[sender]

    details="Confirm Details\n\n"

    for k,v in d.items():
        if k!="step":
            details+=f"{k.capitalize()} : {v}\n"

    details+=(
        "\n1 Confirm"
        "\n2 Edit Name"
        "\n3 Edit Aadhaar"
        "\n4 Edit Address"
        "\n5 Cancel"
    )

    msg.body(details)

    user_data[sender]["step"]="confirm_choice"

# ---------------- HOME ----------------

@app.route("/")
def home():
    return "WhatsApp Bot Running"

# ---------------- PDF DOWNLOAD ----------------

@app.route("/pdf/<filename>")
def pdf_download(filename):

    file_path=f"/tmp/{filename}"

    if os.path.exists(file_path):
        return send_file(file_path,as_attachment=True)

    return "File not found",404

# ---------------- WHATSAPP BOT ----------------

@app.route("/whatsapp",methods=["POST"])
def whatsapp_bot():

    resp=MessagingResponse()
    msg=resp.message()

    sender=request.values.get("From")
    text=(request.values.get("Body") or "").strip().lower()

    # -------- Voice Processing --------

    num_media=int(request.values.get("NumMedia",0))

    if num_media>0:

        media_url=request.values.get("MediaUrl0")
        media_type=request.values.get("MediaContentType0")

        if "audio" in media_type:

            audio_file="/tmp/input.ogg"
            wav_file="/tmp/input.wav"

            r=requests.get(media_url,auth=(ACCOUNT_SID,AUTH_TOKEN))

            with open(audio_file,"wb") as f:
                f.write(r.content)

            sound=AudioSegment.from_file(audio_file)
            sound.export(wav_file,format="wav")

            text=speech_to_text(wav_file)

    # -------- Language Detection --------

    lang=detect_language(text)

    if lang=="en":
        text_ml=manglish_to_malayalam(text)
    else:
        text_ml=text

    # ---------------- CANCEL ----------------

    if text in ["cancel","stop","exit"]:
        user_data.pop(sender,None)
        msg.body("Application cancelled.\nType menu to restart.")
        return str(resp)

    # ---------------- MENU ----------------

    if text in ["hi","hello","menu","മെനു"]:

        user_data[sender]={"step":"menu"}

        msg.body(
            "Welcome to E-Akshaya Services\n"
            "ഇ-അക്ഷയ സേവനത്തിലേക്ക് സ്വാഗതം\n\n"
            "1 Pension Application / പെൻഷൻ\n"
            "2 Income Certificate / വരുമാന സർട്ടിഫിക്കറ്റ്\n"
            "3 Ration Card / റേഷൻ കാർഡ്"
        )

        return str(resp)

    # ---------------- STATUS ----------------

    if text.startswith("status"):

        parts=text.split()

        if len(parts)!=2:
            msg.body("Use: status AKS-123456")
            return str(resp)

        result=check_status(parts[1].upper())

        if not result:
            msg.body("Application not found")
        else:
            msg.body(
                f"Application Status\n\n"
                f"ID:{result[0]}"
                f"\nService:{result[1]}"
                f"\nName:{result[2]}"
                f"\nStatus:{result[5]}"
            )

        return str(resp)

    # ---------------- ADMIN ----------------

    if sender in ADMIN_NUMBERS:

        if text.startswith("approve"):
            app_id=text.split()[1].upper()
            update_status(app_id,"Approved")
            msg.body(f"{app_id} Approved")
            return str(resp)

        if text.startswith("reject"):
            app_id=text.split()[1].upper()
            update_status(app_id,"Rejected")
            msg.body(f"{app_id} Rejected")
            return str(resp)

    # ---------------- INIT ----------------

    if sender not in user_data:
        msg.body("Type menu to start")
        return str(resp)

    step=user_data[sender]["step"]

    # ---------------- MENU SELECT ----------------

    if step=="menu":

        if text=="1":
            user_data[sender]={"service":"Pension","step":"name"}
            msg.body("Enter Name")

        elif text=="2":
            user_data[sender]={"service":"Income","step":"name"}
            msg.body("Enter Name")

        elif text=="3":
            user_data[sender]={"service":"Ration","step":"name"}
            msg.body("Enter Head of Family Name")

    return str(resp)

if __name__=="__main__":
    port=int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port)
