import logging
import re

logger = logging.getLogger(__name__)

# Inline cruft BTWB includes in movement text that we don't want on the poster.
_NOISE_PHRASES = [", pick load", ", rx+", ", scale as needed", ", modify as needed"]

# BTWB inserts these as visual separators between parts of a workout description
# (e.g. "Run, 1200 m\n-- then --\n100 Thrusters..."); drop them as their own line.
_SEPARATOR_LINE = re.compile(r"^-+\s*(then|and)?\s*-+$", re.IGNORECASE)

# "3 rounds for quality of:" -> "3 rounds for quality:" -- BTWB's scheme-line
# phrasing always trails with "of" before the colon; drop it for a tighter read.
_TRAILING_OF = re.compile(r"\s+of:\s*$", re.IGNORECASE)


def _clean_movement_line(line):
    line = line.strip()
    for phrase in _NOISE_PHRASES:
        line = re.sub(re.escape(phrase), "", line, flags=re.IGNORECASE)
    line = _TRAILING_OF.sub(":", line)
    return line.strip().strip(",").strip()


def _movements_from_description(description):
    movements = []
    for raw_line in description.split("\n"):
        line = raw_line.strip()
        if not line or _SEPARATOR_LINE.match(line):
            continue
        cleaned = _clean_movement_line(line)
        if cleaned:
            movements.append(cleaned)
    return movements


def map_wod_json_to_workouts(raw_json):
    """
    Turn BTWB's raw webwidget JSON into the [{"title": ..., "movements": [...]}]
    shape the poster renderer expects. Returns [] for a rest day (no entries).
    """
    wodsets = raw_json.get("wodsets") or []
    if not wodsets:
        return []

    entries = wodsets[0].get("entries") or []
    workouts = []
    for entry in entries:
        title = entry.get("wod_title") or "WOD"
        description = (entry.get("workout") or {}).get("workout_description", "")
        movements = _movements_from_description(description)
        if not movements:
            continue
        workouts.append({"title": title, "movements": movements})

    return workouts


def get_fallback_wod(date_str):
    """
    Generic, clearly-labeled placeholder used when the BTWB fetch fails or
    returns nothing unexpected. Deliberately not disguised as a real workout,
    so a fallback poster is obviously a fallback poster if it ever gets seen.
    """
    logger.warning("FALLBACK WOD DATA IN USE for %s -- BTWB fetch failed or returned nothing", date_str)
    return {
        "date": date_str,
        "workouts": [
            {
                "title": "CSC WOD",
                "movements": [
                    "PLACEHOLDER - BTWB DATA UNAVAILABLE",
                    "This is fallback content, not today's real workout.",
                ],
            }
        ],
    }
