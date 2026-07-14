import os

BTWB_API_KEY = os.environ.get("BTWB_API_KEY")
BTWB_TRACK_ID = os.environ.get("BTWB_TRACK_ID", "310497")

INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_USER_ID = os.environ.get("INSTAGRAM_USER_ID")

# x/y are normalized (0-1) positions within the 1080x1920 poster, based on
# the layout's known geometry (footer text centered at y=1850, black border
# band roughly y=1875-1910) -- not yet verified against a real rendered
# story, since Instagram doesn't offer any way to preview tag placement.
COACH_TAGS = [
    {"username": "csc_chesterspringscrossfit", "x": 0.5, "y": 0.94},
    {"username": "danes_n_gains", "x": 0.5, "y": 0.985},
]

# Gate on the final publish step only; container creation is harmless (an
# unpublished container just expires within 24h) so it's safe to always do
# for real, which gives much stronger confidence when testing.
DRY_RUN = os.environ.get("DRY_RUN", "true").lower() in ("1", "true", "yes")

# Render's free tier blocks outbound SMTP ports entirely, so email goes
# through Resend's HTTP API instead of SMTP. onboarding@resend.dev can send
# indefinitely to whatever address the Resend account was signed up with,
# with no domain verification needed -- exactly our case (emailing yourself).
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "tikilleen@gmail.com")

# Must be the real public URL -- used to build links that Instagram's
# servers and your email client both need to reach, regardless of what
# host the triggering request itself came in on.
APP_BASE_URL = os.environ.get("APP_BASE_URL", "https://btwb-project-1.onrender.com")

# Signs the creation_id directly into approval links so /approve needs no
# server-side memory of pending approvals -- Render's free tier can cycle
# the instance between when an email is sent and when it's clicked, which
# would otherwise silently lose an in-memory pending-approval record.
SECRET_KEY = os.environ.get("SECRET_KEY")
