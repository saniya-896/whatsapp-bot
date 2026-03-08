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

    if any(w in text for w in ["pension","പെൻഷൻ"]):
        return "1"

    if any(w in text for w in ["income","ഇൻകം"]):
        return "2"

    if any(w in text for w in ["ration","റേഷൻ"]):
        return "3"

    return text


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

    elements.append(Paragraph("E-Akshaya Digital Service Application",styles['Title']))
    elements.append(Spacer(1,20))

    elements.append(Paragraph(f"Application ID: {app_id}",styles['Normal']))
    elements.append(Paragraph(f"Service: {data['service']}",styles['Normal']))
    elements.append(Paragraph(f"Name: {data['name']}",styles['Normal']))
    elements.append(Paragraph(f"Aadhaar: {data['aadhaar']}",styles['Normal']))
    elements.append(Paragraph(f"Address: {data['address']}",styles['Normal']))
    elements.append(Paragraph("Status: Submitted",styles['Normal']))

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

    file_path=f"/tmp/{filename}"

    if os.path.exists(file_path):
        return send_file(file_path,as_attachment=True)

    return "PDF not found",404


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

    num_media=int(request.values.get("NumMedia") or 0)


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

        if user_data[sender]["service"]=="Pension":
            user_data[sender]["step"]="age"
            msg.body("Enter your age")
        else:
            user_data[sender]["step"]="aadhaar"
            msg.body("Enter Aadhaar number")


# ---------------- AGE ----------------

    elif step=="age":

        if not text_msg.isdigit():
            msg.body("Enter valid age")
            return str(resp)

        age=int(text_msg)

        if age<50:
            msg.body("Pension only for age 50+")
            return str(resp)

        user_data[sender]["age"]=age
        user_data[sender]["step"]="aadhaar"

        msg.body("Enter Aadhaar number")


# ---------------- AADHAAR ----------------

    elif step=="aadhaar":

        if not text_msg.isdigit() or len(text_msg)!=12:
            msg.body("Enter valid 12 digit Aadhaar")
            return str(resp)

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

            msg.body(
                f"Application Submitted\n\n"
                f"Application ID: {app_id}\n"
                f"Check status: status {app_id}"
            )

            user_data.pop(sender)

            return str(resp)

        elif text_msg=="2":
            user_data[sender]["step"]="edit_name"
            msg.body("Enter correct name")
            return str(resp)

        elif text_msg=="3":
            user_data[sender]["step"]="edit_aadhaar"
            msg.body("Enter correct Aadhaar number")
            return str(resp)

        elif text_msg=="4":
            user_data[sender]["step"]="edit_address"
            msg.body("Enter correct address")
            return str(resp)

        elif text_msg=="5":

            user_data.pop(sender)

            msg.body("Application cancelled. Type menu to start again.")

            return str(resp)


# ---------------- EDIT NAME ----------------

    elif step=="edit_name":

        user_data[sender]["name"]=text_msg.title()

        user_data[sender]["step"]="confirm"

        show_confirm(msg,user_data[sender])


# ---------------- EDIT AADHAAR ----------------

    elif step=="edit_aadhaar":

        if not text_msg.isdigit() or len(text_msg)!=12:
            msg.body("Enter valid 12 digit Aadhaar")
            return str(resp)

        user_data[sender]["aadhaar"]=text_msg

        user_data[sender]["step"]="confirm"

        show_confirm(msg,user_data[sender])


# ---------------- EDIT ADDRESS ----------------

    elif step=="edit_address":

        user_data[sender]["address"]=text_msg

        user_data[sender]["step"]="confirm"

        show_confirm(msg,user_data[sender])


    return str(resp)


if __name__=="__main__":

    port=int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port)
