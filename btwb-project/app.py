import base64
import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta

import requests
from flask import Flask, request, render_template, send_file
from requests.exceptions import HTTPError

import instagram
from config import APP_BASE_URL, DRY_RUN, SECRET_KEY
from mapper import get_fallback_wod, map_wod_json_to_workouts
from notifier import send_approval_email
from poster import generate_image
from scraper import fetch_wod_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)


def _sign(creation_id, date_str):
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY environment variable is not set")
    message = f"{creation_id}:{date_str}".encode()
    return hmac.new(SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


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
    container from it, and emails a link to /review. Nothing goes live
    until you choose an option there. The link is signed (HMAC) rather
    than looked up server-side, so it still works even if the instance
    cycles between now and when it's clicked -- Render's free tier can
    do that within minutes of inactivity.
    """
    date_str = request.args.get("date") or (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    img_io = _generate_and_save(date_str)

    image_url = f"{APP_BASE_URL}/static/preview.png"
    creation_id = instagram.create_story_container(image_url)

    signature = _sign(creation_id, date_str)
    review_url = f"{APP_BASE_URL}/review?creation_id={creation_id}&date={date_str}&sig={signature}"
    send_approval_email(img_io.getvalue(), review_url, date_str)

    logger.info("Prepared post for %s, awaiting review (creation_id=%s)", date_str, creation_id)
    return {"status": "awaiting_review", "date": date_str}


@app.route("/review")
def review():
    """
    Presents the two publishing options: fully-automated (no tags, via
    the Graph API) or hand off to Instagram's own app so you can tag
    manually and get real reshare rights (see /approve for why the API
    can't grant those itself). Embeds the poster directly rather than
    linking to the static file, since that can go stale by the time
    this link is actually clicked.
    """
    creation_id = request.args.get("creation_id", "")
    date_str = request.args.get("date", "")
    signature = request.args.get("sig", "")

    expected = _sign(creation_id, date_str)
    if not hmac.compare_digest(signature, expected):
        return "This link is invalid.", 403

    try:
        with open(os.path.join("static", "preview.png"), "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("ascii")
    except FileNotFoundError:
        return "The poster image is no longer available on the server -- run /prepare_post again to get a fresh link.", 410

    approve_url = f"{APP_BASE_URL}/approve?creation_id={creation_id}&date={date_str}&sig={signature}"
    return render_template("review.html", image_b64=image_b64, approve_url=approve_url, date_str=date_str)


@app.route("/approve")
def approve():
    creation_id = request.args.get("creation_id", "")
    date_str = request.args.get("date", "")
    signature = request.args.get("sig", "")

    expected = _sign(creation_id, date_str)
    if not hmac.compare_digest(signature, expected):
        return "This approval link is invalid.", 403

    try:
        media_id = instagram.publish_container(creation_id)
    except HTTPError:
        logger.exception("Publish failed for creation_id=%s", creation_id)
        return "Instagram rejected this publish -- it may have already been posted, or the container expired.", 409

    if DRY_RUN:
        return f"DRY_RUN is on -- would have published container {creation_id} for {date_str}. No real post was made."
    return f"Posted to Instagram for {date_str} (media id: {media_id})"


@app.route("/debug")
def debug():
    return f"<h1>Flask is working!</h1><p>Time: {datetime.now()}</p>"


@app.route("/debug_ip")
def debug_ip():
    """TEMPORARY -- diagnosing whether BTWB is rejecting this service's
    outbound IP specifically. Remove once that's resolved."""
    try:
        response = requests.get("https://api.ipify.org", params={"format": "json"}, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}, 502


@app.route("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
