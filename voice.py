from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import speech_recognition as sr
from pydub import AudioSegment
import os
import random
import sqlite3
from requests.auth import HTTPBasicAuth

app = Flask(__name__)

ACCOUNT_SID = os.environ.get("ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

AudioSegment.converter = "/usr/bin/ffmpeg"

user_data = {}

# ---------------- DATABASE ----------------

def init_db():

    conn = sqlite3.connect("applications.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications(
        app_id TEXT,
        service TEXT,
        name TEXT,
        aadhaar TEXT,
        address TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- HOME ----------------

@app.route("/")
def home():
    return "WhatsApp Bot Running"

# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
def admin():

    conn = sqlite3.connect("applications.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM applications")
    rows = cursor.fetchall()

    conn.close()

    html = """
    <h2>Akshaya Applications</h2>
    <table border=1>
    <tr>
    <th>ID</th>
    <th>Service</th>
    <th>Name</th>
    <th>Aadhaar</th>
    <th>Address</th>
    <th>Status</th>
    </tr>
    """

    for r in rows:

        html += f"""
        <tr>
        <td>{r[0]}</td>
        <td>{r[1]}</td>
        <td>{r[2]}</td>
        <td>{r[3]}</td>
        <td>{r[4]}</td>
        <td>{r[5]}</td>
        </tr>
        """

    html += "</table>"

    return html

# ---------------- UPDATE STATUS ----------------

@app.route("/update/<app_id>/<status>")
def update_status(app_id,status):

    conn = sqlite3.connect("applications.db")
    cursor = conn.cursor()

    cursor.execute(
    "UPDATE applications SET status=? WHERE app_id=?",
    (status,app_id)
    )

    conn.commit()
    conn.close()

    return f"Status updated to {status}"

# ---------------- WHATSAPP BOT ----------------

@app.route("/whatsapp", methods=["POST"])
def whatsapp_bot():

    resp = MessagingResponse()
    msg = resp.message()

    sender = request.values.get("From","")
    body = request.values.get("Body","")

    text_msg = body.strip().lower()
    num_media = int(request.values.get("NumMedia",0))

    print("User:", sender, "Message:", text_msg)

# ---------------- STATUS CHECK ----------------

    if text_msg.startswith("status"):

        try:

            app_id = text_msg.split(" ")[1]

            conn = sqlite3.connect("applications.db")
            cursor = conn.cursor()

            cursor.execute(
            "SELECT service,name,status FROM applications WHERE app_id=?",
            (app_id,)
            )

            result = cursor.fetchone()
            conn.close()

            if result:

                service,name,status = result

                msg.body(
                f"Application Found\n\n"
                f"ID: {app_id}\n"
                f"Name: {name}\n"
                f"Service: {service}\n"
                f"Status: {status}"
                )

            else:
                msg.body("Application not found")

        except:
            msg.body("Use: status AKS-123456")

        return str(resp)

# ---------------- MENU ----------------

    if text_msg in ["menu","start","restart"]:

        user_data.pop(sender,None)

        user_data[sender]={"step":"menu"}

        msg.body(
        "🙏 Welcome to E-Akshaya Digital Service\n\n"
        "1 Pension Application\n"
        "2 Income Certificate\n"
        "3 Ration Card\n\n"
        "Reply with option number"
        )

        return str(resp)

# ---------------- VOICE ----------------

    if num_media > 0:

        content_type = request.values.get("MediaContentType0","")

        if "audio" not in content_type:

            msg.body("Send voice message only")
            return str(resp)

        media_url = request.values.get("MediaUrl0")

        try:

            audio_data = requests.get(
            media_url,
            auth=HTTPBasicAuth(ACCOUNT_SID,AUTH_TOKEN)
            )

            with open("voice.ogg","wb") as f:
                f.write(audio_data.content)

            sound = AudioSegment.from_ogg("voice.ogg")
            sound.export("voice.wav",format="wav")

            recognizer = sr.Recognizer()

            with sr.AudioFile("voice.wav") as source:
                audio = recognizer.record(source)

            text_msg = recognizer.recognize_google(audio).lower()

        except:

            msg.body("Voice not recognized")
            return str(resp)

        finally:

            if os.path.exists("voice.ogg"):
                os.remove("voice.ogg")

            if os.path.exists("voice.wav"):
                os.remove("voice.wav")

# ---------------- FIRST START ----------------

    if sender not in user_data:

        user_data[sender]={"step":"menu"}

        msg.body(
        "🙏 Welcome to E-Akshaya Digital Service\n\n"
        "1 Pension Application\n"
        "2 Income Certificate\n"
        "3 Ration Card"
        )

        return str(resp)

    step=user_data[sender]["step"]

# ---------------- MENU SELECT ----------------

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

        else:

            msg.body("Invalid option")

# ---------------- NAME ----------------

    elif step=="name":

        user_data[sender]["name"]=text_msg.title()
        user_data[sender]["step"]="aadhaar"

        msg.body("Enter Aadhaar number")

# ---------------- AADHAAR ----------------

    elif step=="aadhaar":

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
        f"Service: {d['service']}\n"
        f"Name: {d['name']}\n"
        f"Aadhaar: {d['aadhaar']}\n"
        f"Address: {d['address']}\n\n"
        "1 Confirm\n"
        "2 Restart"
        )

# ---------------- CONFIRM ----------------

    elif step=="confirm":

        if text_msg=="1":

            d=user_data[sender]

            application_id="AKS-"+str(random.randint(100000,999999))

            conn=sqlite3.connect("applications.db")
            cursor=conn.cursor()

            cursor.execute(
            "INSERT INTO applications VALUES (?,?,?,?,?,?)",
            (
            application_id,
            d["service"],
            d["name"],
            d["aadhaar"],
            d["address"],
            "Processing"
            )
            )

            conn.commit()
            conn.close()

            msg.body(
            f"Application Submitted\n\n"
            f"Application ID: {application_id}\n\n"
            f"Check status:\nstatus {application_id}"
            )

            user_data.pop(sender,None)

        else:

            user_data.pop(sender,None)
            msg.body("Type menu to start again")

    return str(resp)

# ---------------- RUN ----------------

if __name__=="__main__":

    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)
