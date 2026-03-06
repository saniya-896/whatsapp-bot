from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
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

AudioSegment.converter = "/usr/bin/ffmpeg"

user_data = {}

ADMIN_NUMBERS = [
    "whatsapp:+919633406610"
]

# ---------------- PDF GENERATION ----------------

def generate_pdf(data, app_id):

    filename = f"{app_id}.pdf"

    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("E-Akshaya Digital Service Application", styles['Title']))
    elements.append(Spacer(1,20))

    elements.append(Paragraph(f"Application ID: {app_id}", styles['Normal']))
    elements.append(Paragraph(f"Service: {data.get('service')}", styles['Normal']))
    elements.append(Paragraph(f"Name: {data.get('name')}", styles['Normal']))
    elements.append(Paragraph(f"Aadhaar: {data.get('aadhaar')}", styles['Normal']))
    elements.append(Paragraph(f"Address: {data.get('address')}", styles['Normal']))
    elements.append(Paragraph("Status: Submitted", styles['Normal']))

    pdf = SimpleDocTemplate(filename)
    pdf.build(elements)

# ---------------- SAVE APPLICATION ----------------

def save_application(data, app_id):

    file_exists = os.path.exists("applications.csv")

    with open("applications.csv","a",newline="") as f:

        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["ID","Service","Name","Aadhaar","Address","Status"])

        writer.writerow([
            app_id,
            data.get("service"),
            data.get("name"),
            data.get("aadhaar"),
            data.get("address"),
            "Submitted"
        ])

# ---------------- UPDATE STATUS ----------------

def update_status(app_id,new_status):

    if not os.path.exists("applications.csv"):
        return

    rows=[]

    with open("applications.csv","r") as f:
        reader=csv.reader(f)
        rows=list(reader)

    for r in rows:
        if r[0]==app_id:
            r[5]=new_status

    with open("applications.csv","w",newline="") as f:
        writer=csv.writer(f)
        writer.writerows(rows)

# ---------------- HOME ----------------

@app.route("/")
def home():
    return "WhatsApp Bot Running"

# ---------------- BOT ----------------

@app.route("/whatsapp",methods=["POST"])
def whatsapp_bot():

    resp=MessagingResponse()
    msg=resp.message()

    sender=request.values.get("From")
    body=request.values.get("Body")

    text_msg=(body or "").strip().lower()
    num_media=int(request.values.get("NumMedia") or 0)

    print("User:",sender,text_msg)

# ---------------- STATUS CHECK ----------------

    if text_msg.startswith("status"):

        parts=text_msg.split()

        if len(parts)!=2:
            msg.body("Use: status AKS-123456")
            return str(resp)

        app_id=parts[1].upper()

        if not os.path.exists("applications.csv"):
            msg.body("Database not found.")
            return str(resp)

        with open("applications.csv","r") as f:

            reader=csv.reader(f)

            for row in reader:

                if row[0]==app_id:

                    msg.body(
                        f"Application Status\n\n"
                        f"ID: {row[0]}\n"
                        f"Service: {row[1]}\n"
                        f"Name: {row[2]}\n"
                        f"Status: {row[5]}"
                    )

                    return str(resp)

        msg.body("Application not found.")
        return str(resp)

# ---------------- ADMIN ----------------

    if sender in ADMIN_NUMBERS:

        if text_msg=="admin":

            if not os.path.exists("applications.csv"):
                msg.body("No applications found.")
                return str(resp)

            with open("applications.csv","r") as f:
                reader=csv.reader(f)
                rows=list(reader)

            text="Recent Applications\n\n"

            for r in rows[-5:]:

                text+=(
                    f"ID: {r[0]}\n"
                    f"Service: {r[1]}\n"
                    f"Name: {r[2]}\n"
                    f"Status: {r[5]}\n\n"
                )

            msg.body(text)
            return str(resp)

        if text_msg.startswith("approve"):

            try:
                app_id=text_msg.split()[1].upper()
                update_status(app_id,"Approved")
                msg.body(f"{app_id} Approved")
            except:
                msg.body("Invalid command")

            return str(resp)

        if text_msg.startswith("reject"):

            try:
                app_id=text_msg.split()[1].upper()
                update_status(app_id,"Rejected")
                msg.body(f"{app_id} Rejected")
            except:
                msg.body("Invalid command")

            return str(resp)

# ---------------- START ----------------

    if text_msg in ["hi","hello","hai"]:

        user_data[sender]={"step":"menu"}

        msg.body(
            "🙏 Welcome to E-Akshaya Digital Service\n\n"
            "1️⃣ Pension Application\n"
            "2️⃣ Income Certificate\n"
            "3️⃣ Ration Card\n\n"
            "Reply with option number"
        )

        return str(resp)

# ---------------- CANCEL ----------------

    if text_msg=="cancel":

        user_data.pop(sender,None)

        msg.body("❌ Application cancelled.\nType menu to restart")

        return str(resp)

# ---------------- MENU ----------------

    if text_msg in ["menu","restart","start"]:

        user_data[sender]={"step":"menu"}

        msg.body(
            "📋 E-Akshaya Digital Service\n\n"
            "1️⃣ Pension Application\n"
            "2️⃣ Income Certificate\n"
            "3️⃣ Ration Card"
        )

        return str(resp)

# ---------------- VOICE ----------------

    if num_media>0:

        media_url=request.values.get("MediaUrl0")

        audio_data=requests.get(
            media_url,
            auth=HTTPBasicAuth(ACCOUNT_SID,AUTH_TOKEN)
        )

        with open("voice.ogg","wb") as f:
            f.write(audio_data.content)

        try:

            sound=AudioSegment.from_file("voice.ogg")
            sound.export("voice.wav",format="wav")

            r=sr.Recognizer()

            with sr.AudioFile("voice.wav") as source:
                audio=r.record(source)

            try:
                text_msg=r.recognize_google(audio,language="ml-IN").lower()
            except:
                text_msg=r.recognize_google(audio,language="en-IN").lower()

        except:
            msg.body("Could not understand voice.")
            return str(resp)

# ---------------- FIRST USER ----------------

    if sender not in user_data:

        user_data[sender]={"step":"menu"}

        msg.body(
            "E-Akshaya Digital Service\n\n"
            "1 Pension\n2 Income Certificate\n3 Ration Card"
        )

        return str(resp)

    step=user_data[sender]["step"]

# ---------------- MENU SELECT ----------------

    if step=="menu":

        if text_msg=="1":
            user_data[sender]["service"]="Pension"
            user_data[sender]["step"]="name"
            msg.body("Enter your name.")

        elif text_msg=="2":
            user_data[sender]["service"]="Income Certificate"
            user_data[sender]["step"]="name"
            msg.body("Enter your name.")

        elif text_msg=="3":
            user_data[sender]["service"]="Ration Card"
            user_data[sender]["step"]="name"
            msg.body("Enter your name.")

# ---------------- NAME ----------------

    elif step=="name":

        user_data[sender]["name"]=text_msg.title()

        if user_data[sender]["service"]=="Pension":

            user_data[sender]["step"]="age"
            msg.body("Enter your age.")

        else:

            user_data[sender]["step"]="aadhaar"
            msg.body("Enter Aadhaar number.")

# ---------------- AGE ----------------

    elif step=="age":

        if not text_msg.isdigit():
            msg.body("Enter valid age.")
        else:

            age=int(text_msg)

            if age<60:
                msg.body("Pension only for age 60+")
            else:
                user_data[sender]["age"]=age
                user_data[sender]["step"]="aadhaar"
                msg.body("Enter Aadhaar number.")

# ---------------- AADHAAR ----------------

    elif step=="aadhaar":

        if not text_msg.isdigit() or len(text_msg)!=12:
            msg.body("Enter valid 12 digit Aadhaar.")
        else:

            user_data[sender]["aadhaar"]=text_msg
            user_data[sender]["step"]="address"
            msg.body("Enter address.")

# ---------------- ADDRESS ----------------

    elif step=="address":

        user_data[sender]["address"]=text_msg
        user_data[sender]["step"]="confirm"

        d=user_data[sender]

        msg.body(
            f"📋 Confirm Details\n\n"
            f"Service: {d['service']}\n"
            f"Name: {d['name']}\n"
            f"Aadhaar: {d['aadhaar']}\n"
            f"Address: {d['address']}\n\n"
            "1 Confirm\n2 Edit Name\n3 Edit Aadhaar\n4 Edit Address"
        )

# ---------------- CONFIRM ----------------

    elif step=="confirm":

        if text_msg=="1":

            app_id="AKS-"+str(random.randint(100000,999999))

            save_application(user_data[sender],app_id)

            generate_pdf(user_data[sender],app_id)

            msg.body(
                f"✅ Application Submitted\n\n"
                f"📄 Application ID: {app_id}\n"
                f"PDF receipt generated\n\n"
                f"Check status using:\nstatus {app_id}"
            )

            user_data.pop(sender)

        elif text_msg=="2":
            user_data[sender]["step"]="edit_name"
            msg.body("Enter correct name.")

        elif text_msg=="3":
            user_data[sender]["step"]="edit_aadhaar"
            msg.body("Enter correct Aadhaar.")

        elif text_msg=="4":
            user_data[sender]["step"]="edit_address"
            msg.body("Enter correct address.")

# ---------------- EDIT ----------------

    elif step=="edit_name":

        user_data[sender]["name"]=text_msg.title()
        user_data[sender]["step"]="confirm"
        msg.body("Name updated. Type 1 to confirm.")

    elif step=="edit_aadhaar":

        if not text_msg.isdigit() or len(text_msg)!=12:
            msg.body("Invalid Aadhaar.")
        else:
            user_data[sender]["aadhaar"]=text_msg
            user_data[sender]["step"]="confirm"
            msg.body("Aadhaar updated. Type 1 to confirm.")

    elif step=="edit_address":

        user_data[sender]["address"]=text_msg
        user_data[sender]["step"]="confirm"
        msg.body("Address updated. Type 1 to confirm.")

    return str(resp)

# ---------------- RUN ----------------

if __name__=="__main__":

    port=int(os.environ.get("PORT",10000))

    app.run(host="0.0.0.0",port=port)
