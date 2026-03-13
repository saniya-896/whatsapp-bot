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

app = Flask(**name**)

ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

AudioSegment.converter = "/usr/bin/ffmpeg"

user_data = {}

ADMIN_NUMBERS = ["whatsapp:+919633406610"]

# ---------------- NORMALIZE COMMAND ----------------

def normalize_command(text):

```
text = text.lower()

if any(w in text for w in ["pension","പെൻഷൻ"]):
    return "1"

if any(w in text for w in ["income","income certificate","ഇൻകം"]):
    return "2"

if any(w in text for w in ["ration","ration card","റേഷൻ"]):
    return "3"

return text
```

# ---------------- CONFIRM SCREEN ----------------

def show_confirm(msg,data):

```
text = (
    f"Confirm Details\n\n"
    f"Service:{data['service']}\n"
    f"Name:{data['name']}\n"
    f"Aadhaar:{data['aadhaar']}\n"
    f"Phone:{data['phone']}\n"
    f"Address:{data['address']}\n"
)

if "family" in data:
    text += f"Family Members:{data['family']}\n"

text += (
    "\n1 Confirm\n"
    "2 Edit Name\n"
    "3 Edit Aadhaar\n"
    "4 Edit Address\n"
    "5 Cancel Application"
)

msg.body(text)
```

# ---------------- PDF GENERATION ----------------

def generate_pdf(data, app_id):

```
filename = f"/tmp/{app_id}.pdf"
styles = getSampleStyleSheet()

elements=[]

elements.append(Paragraph("E-Akshaya Digital Service Application", styles['Title']))
elements.append(Spacer(1,20))

elements.append(Paragraph(f"Application ID: {app_id}", styles['Normal']))
elements.append(Paragraph(f"Service: {data['service']}", styles['Normal']))
elements.append(Paragraph(f"Name: {data['name']}", styles['Normal']))

if "age" in data:
    elements.append(Paragraph(f"Age: {data['age']}", styles['Normal']))

if "occupation" in data:
    elements.append(Paragraph(f"Occupation: {data['occupation']}", styles['Normal']))

if "income" in data:
    elements.append(Paragraph(f"Income: {data['income']}", styles['Normal']))

elements.append(Paragraph(f"Aadhaar: {data['aadhaar']}", styles['Normal']))
elements.append(Paragraph(f"Phone: {data['phone']}", styles['Normal']))
elements.append(Paragraph(f"Address: {data['address']}", styles['Normal']))
elements.append(Paragraph("Status: Submitted", styles['Normal']))

pdf = SimpleDocTemplate(filename)
pdf.build(elements)

return filename
```

# ---------------- SAVE CSV ----------------

def save_application(data,app_id):

```
file_exists = os.path.exists("applications.csv")

with open("applications.csv","a",newline="") as f:

    writer=csv.writer(f)

    if not file_exists:
        writer.writerow(["ID","Service","Name","Aadhaar","Phone","Address","Status"])

    writer.writerow([
        app_id,
        data["service"],
        data["name"],
        data["aadhaar"],
        data["phone"],
        data["address"],
        "Submitted"
    ])
```

# ---------------- UPDATE STATUS ----------------

def update_status(app_id,new_status):

```
if not os.path.exists("applications.csv"):
    return

rows=[]

with open("applications.csv","r") as f:
    rows=list(csv.reader(f))

for r in rows:

    if len(r)<7:
        continue

    if r[0]==app_id:
        r[6]=new_status

with open("applications.csv","w",newline="") as f:
    csv.writer(f).writerows(rows)
```

# ---------------- PDF DOWNLOAD ----------------

@app.route("/pdf/<filename>")
def get_pdf(filename):

```
path=f"/tmp/{filename}"

if os.path.exists(path):
    return send_file(path,as_attachment=True)

return "PDF not found",404
```

# ---------------- HOME ----------------

@app.route("/")
def home():
return "WhatsApp Bot Running"

# ---------------- WHATSAPP BOT ----------------

@app.route("/whatsapp",methods=["POST"])
def whatsapp_bot():

```
resp=MessagingResponse()
msg=resp.message()

sender=request.values.get("From")
body=request.values.get("Body")

user_text=(body or "").strip().lower()
text_msg=normalize_command(user_text)
```

# ---------------- CANCEL ----------------

```
if text_msg in ["cancel","5"]:
    user_data.pop(sender,None)
    msg.body("Application cancelled.")
    return str(resp)
```

# ---------------- STATUS CHECK ----------------

```
if user_text.startswith("status"):

    parts=user_text.split()

    if len(parts)!=2:
        msg.body("Use: status AKS-123456")
        return str(resp)

    app_id=parts[1].upper()

    with open("applications.csv","r") as f:

        reader=csv.reader(f)

        for row in reader:

            if len(row)<7:
                continue

            if row[0]==app_id:

                msg.body(
                    f"Application Status\n\n"
                    f"ID:{row[0]}\n"
                    f"Service:{row[1]}\n"
                    f"Name:{row[2]}\n"
                    f"Status:{row[6]}"
                )

                return str(resp)

    msg.body("Application not found")
    return str(resp)
```

# ---------------- START ----------------

```
if text_msg in ["hi","hello","menu"]:

    user_data[sender]={"step":"menu"}

    msg.body(
        "Welcome to E-Akshaya Digital Service\n\n"
        "1 Pension Application\n"
        "2 Income Certificate\n"
        "3 Ration Card"
    )

    return str(resp)
```

# ---------------- USER INIT ----------------

```
if sender not in user_data:

    user_data[sender]={"step":"menu"}
    msg.body("Type menu to start")
    return str(resp)

step=user_data[sender]["step"]
```

# ---------------- MENU ----------------

```
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
```

# ---------------- NAME ----------------

```
elif step=="name":

    user_data[sender]["name"]=text_msg.title()

    service=user_data[sender]["service"]

    if service=="Pension":
        user_data[sender]["step"]="age"
        msg.body("Enter your age")

    elif service=="Income Certificate":
        user_data[sender]["step"]="occupation"
        msg.body("Enter occupation")

    else:
        user_data[sender]["step"]="aadhaar"
        msg.body("Enter Aadhaar number")
```

# ---------------- AGE ----------------

```
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
```

# ---------------- OCCUPATION ----------------

```
elif step=="occupation":

    user_data[sender]["occupation"]=text_msg
    user_data[sender]["step"]="income"
    msg.body("Enter annual income")
```

# ---------------- INCOME ----------------

```
elif step=="income":

    if not text_msg.isdigit():
        msg.body("Enter valid income")

    else:

        user_data[sender]["income"]=text_msg
        user_data[sender]["step"]="aadhaar"
        msg.body("Enter Aadhaar number")
```

# ---------------- AADHAAR ----------------

```
elif step=="aadhaar":

    if not text_msg.isdigit() or len(text_msg)!=12:
        msg.body("Enter valid 12 digit Aadhaar")

    else:

        user_data[sender]["aadhaar"]=text_msg
        user_data[sender]["step"]="phone"
        msg.body("Enter phone number")
```

# ---------------- PHONE ----------------

```
elif step=="phone":

    if not text_msg.isdigit() or len(text_msg)!=10:
        msg.body("Enter valid phone")

    else:

        user_data[sender]["phone"]=text_msg
        user_data[sender]["step"]="address"
        msg.body("Enter address")
```

# ---------------- ADDRESS ----------------

```
elif step=="address":

    user_data[sender]["address"]=text_msg
    user_data[sender]["step"]="confirm"

    show_confirm(msg,user_data[sender])
```

# ---------------- CONFIRM ----------------

```
elif step=="confirm":

    if text_msg=="1":

        app_id="AKS-"+str(random.randint(100000,999999))

        save_application(user_data[sender],app_id)
        generate_pdf(user_data[sender],app_id)

        pdf_url=f"https://whatsapp-bot-mr7x.onrender.com/pdf/{app_id}.pdf"

        msg.body(
            f"Application Submitted\n\n"
            f"Application ID:{app_id}\n"
            f"Check status:\nstatus {app_id}"
        )

        msg.media(pdf_url)

        user_data.pop(sender)

    elif text_msg=="2":

        user_data[sender]["step"]="edit_name"
        msg.body("Enter correct name")

    elif text_msg=="3":

        user_data[sender]["step"]="edit_aadhaar"
        msg.body("Enter correct Aadhaar")

    elif text_msg=="4":

        user_data[sender]["step"]="edit_address"
        msg.body("Enter correct address")
```

# ---------------- EDIT NAME ----------------

```
elif step=="edit_name":

    user_data[sender]["name"]=text_msg.title()
    user_data[sender]["step"]="confirm"
    show_confirm(msg,user_data[sender])
```

# ---------------- EDIT AADHAAR ----------------

```
elif step=="edit_aadhaar":

    if not text_msg.isdigit() or len(text_msg)!=12:
        msg.body("Enter valid Aadhaar")
        return str(resp)

    user_data[sender]["aadhaar"]=text_msg
    user_data[sender]["step"]="confirm"
    show_confirm(msg,user_data[sender])
```

# ---------------- EDIT ADDRESS ----------------

```
elif step=="edit_address":

    user_data[sender]["address"]=text_msg
    user_data[sender]["step"]="confirm"
    show_confirm(msg,user_data[sender])


return str(resp)
```

if **name**=="**main**":

```
port=int(os.environ.get("PORT",8080))
app.run(host="0.0.0.0",port=port)
```
