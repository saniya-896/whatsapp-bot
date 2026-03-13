```python
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from gtts import gTTS
from openai import OpenAI

app = Flask(__name__)

ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")

client = Client(ACCOUNT_SID, AUTH_TOKEN)
ai_client = OpenAI(api_key=OPENAI_KEY)

AudioSegment.converter = os.getenv("FFMPEG_PATH", "/usr/bin/ffmpeg")

# CHANGE THIS TO YOUR RENDER DOMAIN
BASE_URL = "https://whatsapp-bot-mr7x.onrender.com"

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

# ---------------- AI CHAT ----------------

def ai_chat(question):

    prompt = f"""
You are an Akshaya digital assistant helping Kerala citizens.
Reply clearly in Malayalam.

User question: {question}
"""

    try:

        response = ai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"user","content":prompt}]
        )

        return response.choices[0].message.content

    except Exception as e:

        print(e)

        return "ക്ഷമിക്കണം, ഇപ്പോൾ സർവീസ് ലഭ്യമല്ല."

# ---------------- VOICE GENERATION ----------------

def generate_voice(text):

    filename="/tmp/reply.mp3"

    tts=gTTS(text=text,lang="ml")

    tts.save(filename)

    return filename

# ---------------- CONFIRM SCREEN ----------------

def show_confirm(msg,data):

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

def generate_pdf(data,app_id):

    filename=f"/tmp/{app_id}.pdf"

    styles=getSampleStyleSheet()

    elements=[]

    elements.append(Paragraph("Government of Kerala",styles['Title']))
    elements.append(Paragraph("E-Akshaya Digital Service Center",styles['Heading2']))
    elements.append(Spacer(1,20))
    elements.append(Paragraph(f"<b>Application ID:</b> {app_id}",styles['Normal']))
    elements.append(Spacer(1,20))

    table_data=[
        ["Service",data["service"]],
        ["Name",data["name"]],
        ["Aadhaar",data["aadhaar"]],
        ["Address",data["address"]],
        ["Status","Submitted"]
    ]

    table=Table(table_data,colWidths=[200,300])

    table.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),1,colors.black),
        ("BACKGROUND",(0,0),(0,-1),colors.lightgrey)
    ]))

    elements.append(table)

    elements.append(Spacer(1,40))

    elements.append(Paragraph("Digitally generated application",styles['Italic']))

    pdf=SimpleDocTemplate(filename,pagesize=A4)

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
            data["service"],
            data["name"],
            data["aadhaar"],
            data["address"],
            "Submitted"
        ])

# ---------------- PDF DOWNLOAD ----------------

@app.route("/pdf/<filename>")
def get_pdf(filename):

    file_path=f"/tmp/{filename}"

    if os.path.exists(file_path):
        return send_file(file_path,as_attachment=True)

    return "PDF not found",404

# ---------------- VOICE FILE ----------------

@app.route("/voice/<filename>")
def get_voice(filename):

    file_path=f"/tmp/{filename}"

    if os.path.exists(file_path):
        return send_file(file_path,mimetype="audio/mpeg")

    return "File not found",404

# ---------------- HOME ----------------

@app.route("/")
def home():
    return "WhatsApp Bot Running"

# ---------------- WHATSAPP BOT ----------------

@app.route("/whatsapp",methods=["POST"])
def whatsapp_bot():

    resp=MessagingResponse()
    msg=resp.message()

    sender=request.values.get("From")
    body=request.values.get("Body")

    user_text=(body or "").strip().lower()
    text_msg=normalize_command(user_text)

    num_media=int(request.values.get("NumMedia",0))

# ---------------- AI CHAT ----------------

    if user_text.startswith("ai"):

        question=user_text.replace("ai","").strip()

        answer=ai_chat(question)

        generate_voice(answer)

        msg.body(answer)

        msg.media(f"{BASE_URL}/voice/reply.mp3")

        return str(resp)

# ---------------- START ----------------

    if text_msg in ["hi","hello","menu"]:

        user_data[sender]={"step":"menu"}

        msg.body(
            "Welcome to E-Akshaya Digital Service\n\n"
            "1 Pension Application\n"
            "2 Income Certificate\n"
            "3 Ration Card"
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

            msg.body("Enter valid 12 digit Aadhaar")

        else:

            user_data[sender]["aadhaar"]=text_msg
            user_data[sender]["step"]="address"

            msg.body("Enter address")

# ---------------- ADDRESS ----------------

    elif step=="address":

        user_data[sender]["address"]=text_msg
        user_data[sender]["step"]="confirm"

        show_confirm(msg,user_data[sender])

# ---------------- CONFIRM ----------------

    elif step=="confirm":

        if text_msg=="1":

            app_id="AKS-"+str(random.randint(100000,999999))

            save_application(user_data[sender],app_id)

            generate_pdf(user_data[sender],app_id)

            pdf_url=f"{BASE_URL}/pdf/{app_id}.pdf"

            msg.body(
                f"Application Submitted\n\n"
                f"Application ID: {app_id}\n"
                f"Check status:\nstatus {app_id}"
            )

            msg.media(pdf_url)

            user_data.pop(sender)

            return str(resp)

    return str(resp)

if __name__=="__main__":

    port=int(os.environ.get("PORT",8080))

    app.run(host="0.0.0.0",port=port)
```
