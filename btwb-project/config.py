import os

BTWB_API_KEY = os.environ.get("BTWB_API_KEY")
BTWB_TRACK_ID = os.environ.get("BTWB_TRACK_ID", "310497")

INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
INSTAGRAM_USER_ID = os.environ.get("INSTAGRAM_USER_ID")

COACH_HANDLES = ["csc_chesterspringscrossfit", "danes_n_gains"]

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
