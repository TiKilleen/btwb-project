"""
Entry point for a separate Render Cron Job, scheduled weekly. Instagram's
long-lived tokens are valid 60 days and refreshable any time after the first
24 hours, so a weekly cadence leaves enormous margin -- no need to track
"when was it last refreshed", just refresh unconditionally every run.

Reads the current token from this app's own Render web service via Render's
API (rather than keeping a separate copy in this Cron Job's own env vars,
which would go stale after the first refresh), then writes the refreshed
token back and triggers a redeploy so the running service actually picks it
up -- updating the env var alone does not take effect on its own.
"""
import logging

import requests

from config import RENDER_API_KEY, RENDER_SERVICE_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

RENDER_API_BASE = "https://api.render.com/v1"
INSTAGRAM_TOKEN_KEY = "INSTAGRAM_ACCESS_TOKEN"


def _render_headers():
    return {"Authorization": f"Bearer {RENDER_API_KEY}", "Content-Type": "application/json"}


def _get_current_instagram_token():
    response = requests.get(
        f"{RENDER_API_BASE}/services/{RENDER_SERVICE_ID}/env-vars",
        headers=_render_headers(),
        params={"limit": 100},
        timeout=15,
    )
    response.raise_for_status()
    entries = response.json()

    for entry in entries:
        # Render's list endpoints commonly wrap each item as {"envVar": {...},
        # "cursor": ...} -- tolerate that shape or a flat {"key", "value"} one,
        # since the exact shape isn't documented and this is unverified until
        # the first real run.
        env_var = entry.get("envVar", entry)
        if env_var.get("key") == INSTAGRAM_TOKEN_KEY:
            return env_var["value"]

    raise RuntimeError(f"{INSTAGRAM_TOKEN_KEY} not found among this service's environment variables")


def _refresh_token(current_token):
    response = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": current_token},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    logger.info("Instagram refresh succeeded, new token expires_in=%s seconds", data.get("expires_in"))
    return data["access_token"]


def _update_render_env_var(new_token):
    response = requests.put(
        f"{RENDER_API_BASE}/services/{RENDER_SERVICE_ID}/env-vars/{INSTAGRAM_TOKEN_KEY}",
        headers=_render_headers(),
        json={"value": new_token},
        timeout=15,
    )
    response.raise_for_status()
    logger.info("Updated %s on Render service %s", INSTAGRAM_TOKEN_KEY, RENDER_SERVICE_ID)


def _trigger_redeploy():
    response = requests.post(
        f"{RENDER_API_BASE}/services/{RENDER_SERVICE_ID}/deploys",
        headers=_render_headers(),
        json={},
        timeout=15,
    )
    response.raise_for_status()
    logger.info("Triggered redeploy of %s so the new token takes effect", RENDER_SERVICE_ID)


def main():
    if not RENDER_API_KEY or not RENDER_SERVICE_ID:
        raise RuntimeError("RENDER_API_KEY / RENDER_SERVICE_ID environment variables are not set")

    current_token = _get_current_instagram_token()
    new_token = _refresh_token(current_token)
    _update_render_env_var(new_token)
    _trigger_redeploy()


if __name__ == "__main__":
    main()
