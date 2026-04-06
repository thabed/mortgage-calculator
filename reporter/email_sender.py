"""
email_sender.py
Send the weekly report via Gmail SMTP using an App Password.

Setup (one-time):
  1. Enable 2-Step Verification on your Google account.
  2. Go to https://myaccount.google.com/apppasswords
  3. Create a new app password (name it e.g. "mortgage-reporter").
  4. Paste the 16-character password (without spaces) into config.json
     as "email_app_password".
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date


def send_report(config: dict, html_body: str) -> None:
    subject = f"Húsnæðislán — Vikuleg skýrsla {date.today().strftime('%d.%m.%Y')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config["email_from"]
    msg["To"] = config["email_to"]
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(config["email_from"], config["email_app_password"])
        smtp.sendmail(config["email_from"], config["email_to"], msg.as_string())

    print(f"[email] Report sent to {config['email_to']}")
