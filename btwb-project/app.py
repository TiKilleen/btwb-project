import logging
import os
import secrets
from datetime import datetime, timedelta

from flask import Flask, request, render_template, send_file

import instagram
from config import APP_BASE_URL, DRY_RUN
from mapper import get_fallback_wod, map_wod_json_to_workouts
from notifier import send_approval_email
from poster import generate_image
from scraper import fetch_wod_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)

# In-memory only -- lost on restart/redeploy. Acceptable tradeoff for a
# once-a-day approval click; see conversation notes for the reasoning.
PENDING_APPROVALS = {}


def get_wod_by_date(date_str):
    try:
        raw = fetch_wod_json(date_str)
        workouts = map_wod_json_to_workouts(raw)
        logger.info("Fetched %d workout(s) from BTWB for %s", len(workouts), date_str)
        return {"date": date_str, "workouts": workouts}
    except Exception:
        logger.exception("BTWB fetch failed for %s", date_str)
        return get_fallback_wod(date_str)


def _generate_and_save(date_str):
    wod_data = get_wod_by_date(date_str)
    img_io = generate_image(wod_data)

    os.makedirs("static", exist_ok=True)
    with open(os.path.join("static", "preview.png"), "wb") as f:
        f.write(img_io.getvalue())

    img_io.seek(0)
    return img_io


@app.route("/")
def home():
    default_date = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    return render_template("home.html", default_date=default_date)


@app.route("/generate")
def generate():
    date_str = request.args.get("date") or (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    img_io = _generate_and_save(date_str)
    return send_file(img_io, mimetype="image/png", as_attachment=True, download_name=f"wod_{date_str}.png")


@app.route("/prepare_post")
def prepare_post():
    """
    Generates the poster, creates a (real, unpublished) Instagram story
    container from it, and emails an approval link. Nothing goes live
    until that link is clicked -- see /approve.
    """
    date_str = request.args.get("date") or (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    _generate_and_save(date_str)

    image_url = f"{APP_BASE_URL}/static/preview.png"
    creation_id = instagram.create_story_container(image_url)

    token = secrets.token_urlsafe(32)
    PENDING_APPROVALS[token] = {"creation_id": creation_id, "date": date_str, "used": False}

    approve_url = f"{APP_BASE_URL}/approve/{token}"
    send_approval_email(image_url, approve_url, date_str)

    logger.info("Prepared post for %s, awaiting approval (creation_id=%s)", date_str, creation_id)
    return {"status": "awaiting_approval", "date": date_str}


@app.route("/approve/<token>")
def approve(token):
    pending = PENDING_APPROVALS.get(token)
    if not pending:
        return "This approval link is invalid or has expired.", 404
    if pending["used"]:
        return "This approval link has already been used.", 410

    pending["used"] = True
    media_id = instagram.publish_container(pending["creation_id"])

    if DRY_RUN:
        return f"DRY_RUN is on -- would have published container {pending['creation_id']} for {pending['date']}. No real post was made."
    return f"Posted to Instagram for {pending['date']} (media id: {media_id})"


@app.route("/debug")
def debug():
    return f"<h1>Flask is working!</h1><p>Time: {datetime.now()}</p>"


@app.route("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
