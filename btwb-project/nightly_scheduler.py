"""
Entry point for the Render Cron Job. Runs every ~10 minutes; only does
anything during the nightly trigger window (19:55-20:15 America/New_York),
which is checked with a timezone-aware clock so it stays correct across
DST changes without ever needing the cron schedule itself edited.
"""
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://btwb-project-1.onrender.com")
TIMEZONE = ZoneInfo("America/New_York")


def in_trigger_window(now_local):
    window_start = now_local.replace(hour=19, minute=55, second=0, microsecond=0)
    window_end = window_start + timedelta(minutes=20)
    return window_start <= now_local < window_end


def main():
    now_local = datetime.now(TIMEZONE)
    logger.info("Nightly check running at %s (America/New_York)", now_local.isoformat())

    if not in_trigger_window(now_local):
        logger.info("Outside the 19:55-20:15 ET trigger window, nothing to do.")
        return

    tomorrow = (now_local + timedelta(days=1)).strftime("%Y-%m-%d")
    logger.info("Within trigger window, requesting poster for %s", tomorrow)

    # Render's free tier can take 30-50s to wake from idle; give it room.
    response = requests.get(f"{APP_BASE_URL}/prepare_post", params={"date": tomorrow}, timeout=120)
    response.raise_for_status()
    logger.info("Poster prepared and approval email sent for %s: %s", tomorrow, response.json())


if __name__ == "__main__":
    main()
