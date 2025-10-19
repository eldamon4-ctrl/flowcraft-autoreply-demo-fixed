import random
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "your_super_secret_key_here"  # Change this to a strong secret
app.permanent_session_lifetime = timedelta(hours=1)  # Optional: session lasts 1 hour

# ---------- CONFIG ----------
MAX_QUEUE = 5  # Max drafts per user session

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

# ---------- DUMMY AI REPLIES ----------
DUMMY_REPLIES = [
    "Hello,\n\nThank you for reaching out! We would be happy to assist and discuss the details further. Please let us know a suitable time for a call.\n\nBest regards,\nCustomer Support – FlowCraftCo",
    "Hi,\n\nThank you for your inquiry. We can provide a detailed quote for our automation services. Let us know your requirements so we can prepare it promptly.\n\nBest regards,\nCustomer Support – FlowCraftCo",
    "Good morning,\n\nThank you for contacting us. We have resent the latest invoice for your review. Please confirm receipt.\n\nBest regards,\nCustomer Support – FlowCraftCo"
]

# ---------- ROUTES ----------
@app.route("/")
def index():
    session.permanent = True
    if "review_queue" not in session:
        session["review_queue"] = []
    if "sent_history" not in session:
        session["sent_history"] = []

    return render_template(
        "index.html",
        queue=session["review_queue"],
        history=session["sent_history"],
        msg=request.args.get("msg", "")
    )

@app.route("/fetch_emails")
def fetch_emails():
    session.permanent = True
    review_queue = session.get("review_queue", [])

    # Limit queue per user
    if len(review_queue) >= MAX_QUEUE:
        review_queue.pop(0)  # Remove oldest draft

    # Simulate fetching random email
    new_email = random.choice(sample_emails).copy()
    draft = random.choice(DUMMY_REPLIES)
    new_email["draft"] = draft
    review_queue.append(new_email)

    session["review_queue"] = review_queue
    return redirect(url_for("index", msg="Fetched new email draft!"))

@app.route("/send/<int:index>")
def send_draft(index):
    session.permanent = True
    review_queue = session.get("review_queue", [])
    sent_history = session.get("sent_history", [])

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

        session["review_queue"] = review_queue
        session["sent_history"] = sent_history

        return redirect(url_for("index", msg=f"Email reply approved (simulated send) to {item['from']}"))
    except Exception as e:
        return redirect(url_for("index", msg=f"Error: {e}"))

if __name__ == "__main__":
    app.run(debug=True)
