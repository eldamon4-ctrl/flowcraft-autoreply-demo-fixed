from flask import Flask, render_template
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
import openai

app = Flask(__name__)

# ---------- CONFIG ----------
IMAP_SERVER = 'imap.gmail.com'
SMTP_SERVER = 'smtp.gmail.com'
EMAIL_ACCOUNT = 'damonflowcraftco@gmail.com'
EMAIL_PASSWORD = 'sncj fetn jenw rgxi'
OPENAI_API_KEY = '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'

openai.api_key = OPENAI_API_KEY
review_queue = []


def fetch_unread_emails():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    mail.select('inbox')
    status, response = mail.search(None, '(UNSEEN)')
    unread_msg_nums = response[0].split()
    emails = []
    for e_id in unread_msg_nums:
        _, data = mail.fetch(e_id, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])
        emails.append({
            'from': msg['From'],
            'subject': msg['Subject'],
            'body': msg.get_payload(decode=True).decode(errors="ignore")
        })
    return emails


def generate_reply(email_body):
    prompt = f"You are FlowCraftCo's AI assistant. Write a concise, polite reply:\n\n{email_body}"
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']


def send_email(to_email, subject, body):
    msg = MIMEText(body)
    msg['Subject'] = f"Re: {subject}"
    msg['From'] = EMAIL_ACCOUNT
    msg['To'] = to_email
    server = smtplib.SMTP_SSL(SMTP_SERVER, 465)
    server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    server.sendmail(EMAIL_ACCOUNT, to_email, msg.as_string())
    server.quit()


@app.route('/')
def index():
    return render_template('index.html', queue=review_queue)


@app.route('/fetch_emails')
def fetch_emails():
    emails = fetch_unread_emails()
    for e in emails:
        draft = generate_reply(e['body'])
        review_queue.append({
            'from': e['from'],
            'subject': e['subject'],
            'draft': draft
        })
    return "Fetched emails and generated drafts!"


@app.route('/send/<int:index>')
def send_email_route(index):
    draft = review_queue.pop(index)
    send_email(draft['from'], draft['subject'], draft['draft'])
    return f"Email sent to {draft['from']}!"


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
