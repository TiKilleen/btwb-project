import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, NOTIFY_EMAIL

logger = logging.getLogger(__name__)


def send_approval_email(image_url, approve_url, date_str):
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        raise RuntimeError("GMAIL_ADDRESS / GMAIL_APP_PASSWORD not configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"WOD poster ready for {date_str} — approve to post"
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = NOTIFY_EMAIL

    html = f"""
    <p>Tomorrow's WOD poster ({date_str}) is ready.</p>
    <p><img src="{image_url}" style="max-width: 400px; border: 1px solid #ccc;"></p>
    <p>
      <a href="{approve_url}"
         style="display:inline-block;padding:12px 20px;background:#000;color:#fff;
                text-decoration:none;font-family:sans-serif;">
        Approve &amp; Post to Instagram
      </a>
    </p>
    <p style="color:#666;font-family:sans-serif;font-size:13px;">
      If you don't click this, nothing gets posted.
    </p>
    """
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, [NOTIFY_EMAIL], msg.as_string())

    logger.info("Sent approval email for %s to %s", date_str, NOTIFY_EMAIL)
