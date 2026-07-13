import logging
import os
from datetime import datetime, timedelta

from flask import Flask, request, render_template, send_file

from mapper import get_fallback_wod, map_wod_json_to_workouts
from poster import generate_image
from scraper import fetch_wod_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)


def get_wod_by_date(date_str):
    try:
        raw = fetch_wod_json(date_str)
        workouts = map_wod_json_to_workouts(raw)
        logger.info("Fetched %d workout(s) from BTWB for %s", len(workouts), date_str)
        return {"date": date_str, "workouts": workouts}
    except Exception:
        logger.exception("BTWB fetch failed for %s", date_str)
        return get_fallback_wod(date_str)


@app.route("/")
def home():
    default_date = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    return render_template("home.html", default_date=default_date)


@app.route("/generate")
def generate():
    date_str = request.args.get("date") or (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    wod_data = get_wod_by_date(date_str)
    img_io = generate_image(wod_data)

    os.makedirs("static", exist_ok=True)
    with open(os.path.join("static", "preview.png"), "wb") as f:
        f.write(img_io.getvalue())

    img_io.seek(0)
    return send_file(img_io, mimetype="image/png", as_attachment=True, download_name=f"wod_{date_str}.png")


@app.route("/debug")
def debug():
    return f"<h1>Flask is working!</h1><p>Time: {datetime.now()}</p>"


@app.route("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
