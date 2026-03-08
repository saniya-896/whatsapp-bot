from flask import Flask, request, send_file
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import csv
import random
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

user_data = {}

ADMIN_NUMBERS = ["whatsapp:+919633406610"]

# ---------------- PDF ----------------

def generate_pdf(data, app_id):

    filename = f"/tmp/{app_id}.pdf"
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph("E-Akshaya Digital Service Application", styles['Title']))
    elements.append(Spacer(1,20))

    for k,v in data.items():
        if k != "step":
            elements.append(Paragraph(f"{k} : {v}", styles['Normal']))

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

        reader = csv.reader(f)

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

# ---------------- CANCEL ----------------

    if text in ["cancel","stop","exit"]:

        if sender in user_data:
            user_data.pop(sender)

        msg.body("Application cancelled.\nType menu to restart.")
        return str(resp)


# ---------------- MENU ----------------

    if text in ["hi","hello","menu"]:

        user_data[sender]={"step":"menu"}

        msg.body(
            "Welcome to E-Akshaya Services\n\n"
            "1 Pension Application\n"
            "2 Income Certificate\n"
            "3 Ration Card\n\n"
            "Type cancel anytime."
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


# ---------------- NAME ----------------

    elif step=="name":

        user_data[sender]["name"]=text.title()

        service=user_data[sender]["service"]

        if service=="Pension":
            user_data[sender]["step"]="age"
            msg.body("Enter Age")
        else:
            user_data[sender]["step"]="aadhaar"
            msg.body("Enter Aadhaar Number")


# ---------------- AGE ----------------

    elif step=="age":

        if not text.isdigit():
            msg.body("Enter valid age")
            return str(resp)

        age=int(text)

        if age<50:
            msg.body("Pension available only for age 50+")
            return str(resp)

        user_data[sender]["age"]=age
        user_data[sender]["step"]="gender"

        msg.body("Enter Gender")


# ---------------- GENDER ----------------

    elif step=="gender":

        user_data[sender]["gender"]=text
        user_data[sender]["step"]="aadhaar"

        msg.body("Enter Aadhaar Number")


# ---------------- AADHAAR ----------------

    elif step=="aadhaar":

        if not text.isdigit() or len(text)!=12:
            msg.body("Enter valid 12 digit Aadhaar")
            return str(resp)

        user_data[sender]["aadhaar"]=text
        user_data[sender]["step"]="mobile"

        msg.body("Enter Mobile Number")


# ---------------- MOBILE ----------------

    elif step=="mobile":

        if not text.isdigit() or len(text)!=10:
            msg.body("Enter valid 10 digit mobile")
            return str(resp)

        user_data[sender]["mobile"]=text
        user_data[sender]["step"]="address"

        msg.body("Enter Address")


# ---------------- ADDRESS ----------------

    elif step=="address":

        user_data[sender]["address"]=text

        service=user_data[sender]["service"]

        if service=="Pension":
            user_data[sender]["step"]="income"
            msg.body("Enter Annual Income")

        elif service=="Income":
            user_data[sender]["step"]="occupation"
            msg.body("Enter Occupation")

        elif service=="Ration":
            user_data[sender]["step"]="card"
            msg.body("Enter Card Type")


# ---------------- PENSION INCOME ----------------

    elif step=="income":

        user_data[sender]["income"]=text
        user_data[sender]["step"]="ration"

        msg.body("Enter Ration Card Number")


# ---------------- RATION NUMBER ----------------

    elif step=="ration":

        user_data[sender]["ration"]=text
        show_confirmation(sender,msg)


# ---------------- OCCUPATION ----------------

    elif step=="occupation":

        user_data[sender]["occupation"]=text
        user_data[sender]["step"]="monthly"

        msg.body("Enter Monthly Income")


# ---------------- MONTHLY ----------------

    elif step=="monthly":

        user_data[sender]["monthly"]=text
        user_data[sender]["step"]="annual"

        msg.body("Enter Total Annual Family Income")


# ---------------- ANNUAL ----------------

    elif step=="annual":

        user_data[sender]["annual"]=text
        user_data[sender]["step"]="members"

        msg.body("Enter Number of Family Members")


# ---------------- MEMBERS ----------------

    elif step=="members":

        user_data[sender]["members"]=text
        user_data[sender]["step"]="ration"

        msg.body("Enter Ration Card Number")


# ---------------- CARD TYPE ----------------

    elif step=="card":

        user_data[sender]["card"]=text
        show_confirmation(sender,msg)


# ---------------- EDIT STEPS ----------------

    elif step=="edit_name":

        user_data[sender]["name"]=text.title()
        show_confirmation(sender,msg)

    elif step=="edit_aadhaar":

        if not text.isdigit() or len(text)!=12:
            msg.body("Enter valid 12 digit Aadhaar")
            return str(resp)

        user_data[sender]["aadhaar"]=text
        show_confirmation(sender,msg)

    elif step=="edit_address":

        user_data[sender]["address"]=text
        show_confirmation(sender,msg)


# ---------------- CONFIRM CHOICE ----------------

    elif step=="confirm_choice":

        if text=="1":

            app_id="AKS-"+str(random.randint(100000,999999))

            save_application(user_data[sender],app_id)

            generate_pdf(user_data[sender],app_id)

            msg.body(
                f"Application Submitted\n\n"
                f"Application ID: {app_id}\n"
                f"Check status:\nstatus {app_id}"
            )

            user_data.pop(sender)

        elif text=="2":

            user_data[sender]["step"]="edit_name"
            msg.body("Enter Correct Name")

        elif text=="3":

            user_data[sender]["step"]="edit_aadhaar"
            msg.body("Enter Correct Aadhaar")

        elif text=="4":

            user_data[sender]["step"]="edit_address"
            msg.body("Enter Correct Address")

        elif text=="5":

            user_data.pop(sender)
            msg.body("Application Cancelled\nType menu to restart")

        else:
            msg.body("Please choose 1,2,3,4 or 5")

    return str(resp)


if __name__=="__main__":

    port=int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port)
