import logging
import time
from datetime import datetime

import requests

from config import BTWB_API_KEY, BTWB_TRACK_ID

logger = logging.getLogger(__name__)

BTWB_WIDGET_URL = "https://webwidgets.prod.btwb.com/webwidgets/wods"

# BTWB has shown brief, intermittent 500s a few times in production -- failing,
# then succeeding again within under two minutes of its own accord. A couple
# of quick retries catches that without giving up and falling back to
# placeholder data over what's usually a passing blip.
MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 3


def fetch_wod_json(date_str):
    """
    Fetch raw WOD data for a YYYY-MM-DD date from BTWB's webwidget endpoint.

    This is the undocumented endpoint the embeddable BTWB widget itself calls
    (found via network inspection), not the public REST API. It could change
    without notice -- callers should expect that and fall back gracefully.
    """
    if not BTWB_API_KEY:
        raise RuntimeError("BTWB_API_KEY environment variable is not set")

    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    # BTWB requires non-zero-padded month/day, e.g. "2025-7-4" not "2025-07-04"
    btwb_date = f"{target_date.year}-{target_date.month}-{target_date.day}"

    params = {
        "sections": "main",
        "track_ids": BTWB_TRACK_ID,
        "date": btwb_date,
        "activity_length": 0,
        "leaderboard_length": 0,
    }
    headers = {
        "Authorization": f"Bearer {BTWB_API_KEY}",
        "Accept": "application/vnd.btwb.v1.webwidgets+json",
    }

    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(BTWB_WIDGET_URL, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            logger.info("BTWB fetch for %s -> HTTP %s (attempt %d/%d)", date_str, response.status_code, attempt, MAX_ATTEMPTS)
            return response.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if e.response is not None:
                logger.warning(
                    "BTWB error response for %s: HTTP %s, headers=%s, body=%r",
                    date_str, status, dict(e.response.headers), e.response.text[:500],
                )
            if status is not None and 400 <= status < 500:
                raise  # client error (bad key, bad params) -- retrying won't help
            last_error = e
        except requests.exceptions.RequestException as e:
            last_error = e

        if attempt < MAX_ATTEMPTS:
            logger.warning(
                "BTWB fetch for %s failed (attempt %d/%d): %s -- retrying in %ds",
                date_str, attempt, MAX_ATTEMPTS, last_error, RETRY_DELAY_SECONDS,
            )
            time.sleep(RETRY_DELAY_SECONDS)

    raise last_error
