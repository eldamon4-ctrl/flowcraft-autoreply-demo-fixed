                    # app.py - FlowCraft AutoReply (stable + professional replies)
import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.header import decode_header
from email.utils import parseaddr
from flask import Flask, render_template, redirect, url_for, request
from openai import OpenAI

# ---------- CONFIG ----------
EMAIL_ACCOUNT = os.environ.get("EMAIL_ACCOUNT")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")  # 16-char Gmail App Password, no spaces
IMAP_SERVER = "imap.gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------- APP ----------
app = Flask(__name__)
review_queue = []
sent_history = []

# ---------- HELPERS ----------
def decode_header_value(value):
    """Decode a header value (handles encoded words). Returns a str."""
    if not value:
        return ""
    parts = decode_header(value)
    decoded = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            try:
                decoded += part.decode(enc or "utf-8", errors="ignore")
            except:
                decoded += part.decode("utf-8", errors="ignore")
        else:
            decoded += part
    return decoded

def extract_email_address(raw_from):
    """Return plain email address from a From header (e.g. 'Name <email@example.com>')."""
    if not raw_from:
        return ""
    name, addr = parseaddr(raw_from)
    return addr

def generate_flowcraft_reply(email_body, from_name=None):
    """Call OpenAI to generate a FlowCraft-style reply."""
    system_msg = "You are FlowCraftCo's professional email assistant. Reply concisely, warmly, and professionally."
    user_prompt = f"""
You are FlowCraftCo's AI Email Assistant. Write a concise, polite, professional reply that sounds human.
Tone: friendly, professional, slightly warm. Keep it short (3-6 sentences).
Sign off with: "Best regards,\\nFlowCraft AutoReply Bot"

Original email:
\"\"\"{email_body}\"\"\"

If the email is clearly a sales inquiry, offer a next step (e.g., "Would you like a quick call?"). If it's a request, offer to deliver the item or next action. Always include one clear call-to-action when appropriate.
"""
    try:
        resp = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6,
            max_tokens=400
        )
        draft = resp.choices[0].message.content.strip()
        return draft
    except Exception as e:
        return f"(Error generating reply: {e})"

# ---------- ROUTES ----------
@app.route("/")
def index():
    msg = request.args.get("msg", "")
    return render_template("index.html", queue=review_queue, message=msg)

@app.route("/fetch_emails")
def fetch_emails():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select("inbox")
        status, data = mail.search(None, "(UNSEEN)")
        if status != "OK":
            mail.logout()
            return redirect(url_for("index", msg="No new emails or IMAP search failed."))

        mail_ids = data[0].split()
        if not mail_ids:
            mail.logout()
            return redirect(url_for("index", msg="No unread emails."))

        for e_id in mail_ids:
            try:
                _, fetch_data = mail.fetch(e_id, "(RFC822)")
                raw = fetch_data[0][1]
                msg_obj = email.message_from_bytes(raw)

                raw_from = decode_header_value(msg_obj.get("From", ""))
                raw_subject = decode_header_value(msg_obj.get("Subject", "(no subject)"))
                from_addr = extract_email_address(raw_from)

                # get plain text body
                body = ""
                if msg_obj.is_multipart():
                    for part in msg_obj.walk():
                        ctype = part.get_content_type()
                        cdisp = str(part.get("Content-Disposition"))
                        if ctype == "text/plain" and "attachment" not in cdisp:
                            try:
                                body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                                break
                            except:
                                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                else:
                    body = msg_obj.get_payload(decode=True).decode(msg_obj.get_content_charset() or "utf-8", errors="ignore")

                draft = generate_flowcraft_reply(body)

                review_queue.append({
                    "from": from_addr or raw_from,
                    "subject": raw_subject,
                    "draft": draft
                })
            except Exception as inner_e:
                review_queue.append({
                    "from": "(error reading email)",
                    "subject": "(error)",
                    "draft": f"(Failed to parse email: {inner_e})"
                })
                continue

        mail.logout()
        return redirect(url_for("index", msg="Fetched and drafted unread emails."))
    except imaplib.IMAP4.error as imap_err:
        return redirect(url_for("index", msg=f"IMAP error: {imap_err}"))
    except Exception as e:
        return redirect(url_for("index", msg=f"Error fetching emails: {e}"))

@app.route("/send/<int:index>")
def send_draft(index):
    try:
        # Validate index
        if index < 0 or index >= len(review_queue):
            return redirect(url_for("index", msg="Invalid queue index."))

        item = review_queue[index]
        to_addr_raw = item.get("from", "")
        subject = item.get("subject", "(no subject)")
        body = item.get("draft", "")

        # Extract plain email safely
        import re
        match = re.search(r'[\w\.-]+@[\w\.-]+', to_addr_raw)
        if not match:
            return redirect(url_for("index", msg="Cannot determine recipient email address."))
        to_addr = match.group(0)

        # Clean up body and headers to avoid encoding errors
        body = body.replace("\r\n", "\n").replace("\r", "\n")
        subject = subject.strip()

        from email.mime.text import MIMEText
        msg = MIMEText(body, _subtype="plain", _charset="utf-8")
        msg["Subject"] = f"Re: {subject}"
        msg["From"] = f"FlowCraftCo Support <{EMAIL_ACCOUNT}>"
        msg["To"] = to_addr

        # Send via SMTP SSL
        import smtplib, ssl
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
            server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ACCOUNT, [to_addr], msg.as_string())

        # Only remove after successful send
        sent_history.append({
            "to": to_addr,
            "subject": subject,
            "body": body
        })
        review_queue.pop(index)

        return redirect(url_for("index", msg=f"Email sent to {to_addr}"))

    except smtplib.SMTPAuthenticationError:
        return redirect(url_for("index", msg="SMTP Authentication failed. Check Gmail App Password."))
    except smtplib.SMTPRecipientsRefused:
        return redirect(url_for("index", msg="Recipient refused by SMTP server."))
    except Exception as e:
        return redirect(url_for("index", msg=f"Error sending email: {e}"))

@app.route("/sent")
def show_sent():
    return render_template("sent.html", sent=sent_history)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
