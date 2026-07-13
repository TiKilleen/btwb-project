import logging
from datetime import datetime

import requests

from config import BTWB_API_KEY, BTWB_TRACK_ID

logger = logging.getLogger(__name__)

BTWB_WIDGET_URL = "https://webwidgets.prod.btwb.com/webwidgets/wods"


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

    response = requests.get(
        BTWB_WIDGET_URL,
        params={
            "sections": "main",
            "track_ids": BTWB_TRACK_ID,
            "date": btwb_date,
            "activity_length": 0,
            "leaderboard_length": 0,
        },
        headers={
            "Authorization": f"Bearer {BTWB_API_KEY}",
            "Accept": "application/vnd.btwb.v1.webwidgets+json",
        },
        timeout=15,
    )
    response.raise_for_status()
    logger.info("BTWB fetch for %s -> HTTP %s", date_str, response.status_code)
    return response.json()
