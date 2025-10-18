import imaplib
import smtplib
from email.mime.text import MIMEText
import email
import os
import openai
from flask import Flask, render_template, redirect, url_for

# ---------- CONFIG ----------
EMAIL_ACCOUNT = os.environ.get("EMAIL_ACCOUNT")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
openai.api_key = os.environ.get("OPENAI_API_KEY")

# ---------- GLOBAL QUEUE ----------
review_queue = []

# ---------- FLASK APP ----------
app = Flask(__name__)

# ---------- INDEX ----------
@app.route('/')
def index():
    error = None
    return render_template("index.html", queue=review_queue, error=error)

# ---------- FETCH EMAILS ----------
@app.route('/fetch_emails')
def fetch_emails():
    try:
        # Connect to Gmail
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select("inbox")

        # Search for unseen emails
        status, messages = mail.search(None, '(UNSEEN)')
        email_ids = messages[0].split()

        for e_id in email_ids:
            status, data = mail.fetch(e_id, '(RFC822)')
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            sender = msg["From"]
            subject = msg["Subject"]

            # Get email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="ignore")
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors="ignore")

            # Generate draft reply (simplified example)
            draft = f"Hello {sender},\n\nThank you for your email regarding '{subject}'.\n\n— FlowCraft AutoReply Bot"

            # Add to review queue
            review_queue.append({
                "from": sender,
                "subject": subject,
                "draft": draft
            })

        mail.logout()
        return redirect(url_for("index"))

    except Exception as e:
        # Return dashboard with error instead of crashing
        return render_template("index.html", queue=review_queue, error=str(e))

# ---------- SEND DRAFT ----------
@app.route('/send/<int:index>')
def send_email(index):
    try:
        draft_item = review_queue.pop(index)

        msg = MIMEText(draft_item["draft"])
        msg["Subject"] = "Re: " + draft_item["subject"]
        msg["From"] = EMAIL_ACCOUNT
        msg["To"] = draft_item["from"]

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
            server.send_message(msg)

        return redirect(url_for("index"))

    except Exception as e:
        return render_template("index.html", queue=review_queue, error=str(e))

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
