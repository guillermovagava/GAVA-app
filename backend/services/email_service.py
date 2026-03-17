"""
Sends emails via Gmail SMTP using an App Password.
No OAuth needed — just a Gmail address + App Password in .env.
"""
import os
import ssl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(to_address: str, subject: str, body: str) -> dict:
    """
    Send an email from the configured Gmail account.
    Returns {"success": True} or {"success": False, "error": "..."}
    """
    gmail_address = os.getenv("GMAIL_ADDRESS", "")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "")

    if not gmail_address or not gmail_app_password:
        return {"success": False, "error": "Gmail credentials not configured in .env"}

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = to_address

    # Plain text version
    msg.attach(MIMEText(body, "plain"))

    context = ssl.create_default_context()

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(gmail_address, gmail_app_password)
            server.sendmail(gmail_address, to_address, msg.as_string())
        return {"success": True}
    except smtplib.SMTPAuthenticationError:
        return {
            "success": False,
            "error": "Gmail authentication failed. Make sure you used an App Password, not your regular password."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
