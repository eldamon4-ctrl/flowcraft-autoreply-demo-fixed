   import random
from flask import Flask, render_template, request, redirect, url_for
import openai
import os

# ---------- CONFIG ----------
openai.api_key = os.environ.get("OPENAI_API_KEY")  # Set this in Render secrets
app = Flask(__name__)

# ---------- SAMPLE INBOX ----------
sample_emails = [
    {
        "from": "client1@business.com",
        "subject": "Partnership Proposal",
        "body": "Hello, we are interested in a potential partnership with FlowCraftCo. Can we schedule a call?"
    },
    {
        "from": "client2@enterprise.com",
        "subject": "Request for Service Quote",
        "body": "Hi, please provide a quote for your automation services. Thanks!"
    },
    {
        "from": "client3@startup.io",
        "subject": "Invoice Inquiry",
        "body": "Good morning, we haven’t received the latest invoice. Could you resend it?"
    },
]

review_queue = []
sent_history = []

# ---------- ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html", queue=review_queue, history=sent_history, msg=request.args.get("msg", ""))

@app.route("/fetch_emails")
def fetch_emails():
    # Simulate fetching random emails from the sample inbox
    new_email = random.choice(sample_emails).copy()
    # Generate AI draft
    try:
        prompt = f"""You are a professional human customer support assistant for FlowCraftCo.
Generate a polite, professional email reply to the following message, keeping the tone human-like:

Email content:
{new_email['body']}

Reply in clear English, include a subtle brand signature like 'Customer Support – FlowCraftCo'."""
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250
        )
        draft = response.choices[0].message.content.strip()
    except Exception as e:
        draft = f"Error generating reply: {e}"

    new_email["draft"] = draft
    review_queue.append(new_email)
    return redirect(url_for("index", msg="Fetched new email draft!"))

@app.route("/send/<int:index>")
def send_draft(index):
    try:
        if index < 0 or index >= len(review_queue):
            return redirect(url_for("index", msg="Invalid queue index."))

        item = review_queue[index]
        sent_history.append({
            "to": item["from"],
            "subject": item["subject"],
            "body": item["draft"]
        })
        review_queue.pop(index)
        return redirect(url_for("index", msg=f"Email reply approved (simulated send) to {item['from']}"))
    except Exception as e:
        return redirect(url_for("index", msg=f"Error: {e}"))                         
