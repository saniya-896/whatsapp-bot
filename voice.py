from flask import Flask, request, send_file
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import random
import csv
import time
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

user_data = {}

ADMIN_NUMBERS = [
    "whatsapp:+919633406610"
]

# -------- GOVERNMENT FORM LINKS --------

form_links = {
"Pension":"https://arun-goog.github.io/Online-Helper/forms.html",
"Income Certificate":"https://arun-goog.github.io/Online-Helper/forms.html",
"Ration Card":"https://arun-goog.github.io/Online-Helper/forms.html"
}

# ---------------- NORMALIZE COMMAND ----------------

def normalize_command(text):

    text = text.lower()

    if "pension" in text:
        return "1"

    if "income" in text:
        return "2"

    if "ration" in text:
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
        reader=csv.reader(f)
        rows=list(reader)

    for r in rows:

        if len(r) < 6:
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

    return "PDF not found", 404


# ---------------- WHATSAPP BOT ----------------

@app.route("/whatsapp",methods=["POST"])
def whatsapp_bot():

    resp = MessagingResponse()
    msg = resp.message()

    sender = request.values.get("From")
    body = request.values.get("Body")

    user_text = (body or "").strip().lower()
    text_msg = normalize_command(user_text)


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
        else:

            age=int(text_msg)

            if age<50:
                msg.body("Pension only for age 50+")
            else:
                user_data[sender]["age"]=age
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

        d=user_data[sender]

        msg.body(
            f"Confirm Details\n\n"
            f"Service:{d['service']}\n"
            f"Name:{d['name']}\n"
            f"Aadhaar:{d['aadhaar']}\n"
            f"Address:{d['address']}\n\n"
            "1 Confirm\n2 Edit Name\n3 Edit Aadhaar\n4 Edit Address"
        )


# ---------------- CONFIRM ----------------

    elif step=="confirm":

        if text_msg=="1":

            app_id="AKS-"+str(random.randint(100000,999999))

            save_application(user_data[sender],app_id)

            generate_pdf(user_data[sender],app_id)

            form_link = form_links.get(user_data[sender]["service"],"")

            msg.body(
                f"Application Submitted\n\n"
                f"Application ID: {app_id}\n\n"
                f"Download Official Form:\n{form_link}\n\n"
                f"Check status:\nstatus {app_id}"
            )

            user_data.pop(sender)

            return str(resp)

        elif text_msg=="2":
            user_data[sender]["step"]="edit_name"
            msg.body("Enter correct name")

        elif text_msg=="3":
            user_data[sender]["step"]="edit_aadhaar"
            msg.body("Enter correct Aadhaar")

        elif text_msg=="4":
            user_data[sender]["step"]="edit_address"
            msg.body("Enter correct address")


# ---------------- EDIT NAME ----------------

    elif step=="edit_name":

        user_data[sender]["name"]=text_msg.title()
        user_data[sender]["step"]="confirm"


# ---------------- EDIT AADHAAR ----------------

    elif step=="edit_aadhaar":

        if not text_msg.isdigit() or len(text_msg)!=12:
            msg.body("Enter valid Aadhaar")
        else:
            user_data[sender]["aadhaar"]=text_msg
            user_data[sender]["step"]="confirm"


# ---------------- EDIT ADDRESS ----------------

    elif step=="edit_address":

        user_data[sender]["address"]=text_msg
        user_data[sender]["step"]="confirm"


    return str(resp)


if __name__=="__main__":

    port=int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port)
