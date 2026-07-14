import base64
import logging

import requests

from config import NOTIFY_EMAIL, RESEND_API_KEY

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def send_approval_email(image_bytes, approve_url, date_str):
    """
    Embeds the poster directly in the email (as a cid: inline attachment)
    rather than linking to a URL -- Render's free tier can wipe the static
    file before you even open the email, and this way the preview always
    shows exactly what was generated, regardless of server state later.
    """
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY not configured")

    html = f"""
    <p>Tomorrow's WOD poster ({date_str}) is ready.</p>
    <p><img src="cid:poster" style="max-width: 400px; border: 1px solid #ccc;"></p>
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

    response = requests.post(
        RESEND_API_URL,
        headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
        json={
            "from": "WOD Poster <onboarding@resend.dev>",
            "to": [NOTIFY_EMAIL],
            "subject": f"WOD poster ready for {date_str} — approve to post",
            "html": html,
            "attachments": [
                {
                    "filename": "poster.png",
                    "content": base64.b64encode(image_bytes).decode("ascii"),
                    "content_type": "image/png",
                    "content_id": "poster",
                }
            ],
        },
        timeout=15,
    )
    response.raise_for_status()

    logger.info("Sent approval email for %s to %s", date_str, NOTIFY_EMAIL)
