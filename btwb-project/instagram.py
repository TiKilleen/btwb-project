import json
import logging
import time

import requests

from config import DRY_RUN, INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID

logger = logging.getLogger(__name__)

GRAPH_BASE_URL = "https://graph.instagram.com"


def _request(method, path, params):
    url = f"{GRAPH_BASE_URL}/{path}"
    params = {**params, "access_token": INSTAGRAM_ACCESS_TOKEN}
    response = requests.request(method, url, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def create_story_container(image_url, user_tags=None):
    """
    Creates a story media container. Always real, even under DRY_RUN --
    an unpublished container has no public visibility and just expires
    within 24h, so this is safe to actually call while testing.
    """
    params = {"media_type": "STORIES", "image_url": image_url}
    if user_tags:
        params["user_tags"] = json.dumps(user_tags)

    result = _request("POST", f"{INSTAGRAM_USER_ID}/media", params)
    creation_id = result["id"]
    logger.info("Created story container %s for %s", creation_id, image_url)
    return creation_id


def _wait_until_ready(creation_id, timeout_seconds=60, poll_interval=3):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        status = _request("GET", creation_id, {"fields": "status_code"})
        code = status.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            raise RuntimeError(f"Instagram container {creation_id} failed processing")
        time.sleep(poll_interval)
    raise TimeoutError(f"Instagram container {creation_id} not ready after {timeout_seconds}s")


def publish_container(creation_id):
    """The actual public-facing action -- gated behind DRY_RUN."""
    if DRY_RUN:
        logger.info("[DRY_RUN] Would publish container %s (no real API call made)", creation_id)
        return "dry-run-media-id"

    result = _request("POST", f"{INSTAGRAM_USER_ID}/media_publish", {"creation_id": creation_id})
    media_id = result["id"]
    logger.info("Published story, media id %s", media_id)
    return media_id


def publish_story(image_url, user_tags=None):
    creation_id = create_story_container(image_url, user_tags=user_tags)
    _wait_until_ready(creation_id)
    return publish_container(creation_id)
