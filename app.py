import imaplib
import smtplib
import email
from email.mime.text import MIMEText
import openai
import os
from flask import Flask, request, render_template, redirect, url_for

# ---------- CONFIG ----------
GMAIL_USER = os.environ.get("GMAIL_USER")      # your Gmail address
GMAIL_PASS = os.environ.get("GMAIL_APP_PASS")  # 16-char app password
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

openai.api_key = OPENAI_API_KEY

# ---------- FLASK APP ----------
app = Flask(__name__)

# In-memory queues for demo
queue = []
history = []

# ---------- ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html", queue=queue, history=history)

@app.route("/fetch_emails")
def fetch_emails():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")
        typ, data = mail.search(None, 'UNSEEN')
        mail_ids = data[0].split()
        for num in mail_ids:
            typ, msg_data = mail.fetch(num, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject = msg["subject"]
                    sender = msg["from"]
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode()
                    else:
                        body = msg.get_payload(decode=True).decode()
                    
                    # Generate draft reply safely
                    prompt = f"Write a professional email reply to:\n\n{body}\n\nKeep it polite, concise, and friendly."
                    try:
                        response = openai.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=250
                        )
                        draft = response.choices[0].message["content"].strip()
                    except Exception as e:
                        draft = f"Error generating reply: {e}"

                    queue.append({"from": sender, "subject": subject, "draft": draft})
        mail.logout()
        return redirect(url_for("index"))
    except Exception as e:
        return f"Error fetching emails: {e}"

@app.route("/send/<int:index>")
def send_email(index):
    if index >= len(queue):
        return "Invalid index"
    item = queue.pop(index)
    try:
        # Connect SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        msg = MIMEText(item["draft"])
        msg["Subject"] = item["subject"]
        msg["From"] = GMAIL_USER
        msg["To"] = item["from"]
        server.sendmail(GMAIL_USER, item["from"], msg.as_string())
        server.quit()
        # Add to history
        history.append({"to": item["from"], "subject": item["subject"], "body": item["draft"]})
        return redirect(url_for("index"))
    except Exception as e:
        # Push back into queue if sending fails
        queue.insert(index, item)
        return f"Error sending email: {e}"

if __name__ == "__main__":
    app.run(debug=True)                    
