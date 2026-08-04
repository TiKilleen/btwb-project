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

# "Complete as many rounds as possible in 12 mins of:" -> "AMRAP-12:" -- BTWB
# always spells this scheme out (with the same trailing "of:" as other scheme
# lines), but every CrossFitter reads it as AMRAP.
_AMRAP = re.compile(
    r"^(?:complete\s+)?as\s+many\s+(?:rounds|reps)\s+as\s+possible\s+in\s+(\d+)\s*min(?:ute)?s?(?:\s+of)?\s*:?\s*$",
    re.IGNORECASE,
)

# Whole lines BTWB sometimes includes that don't add anything on a poster --
# dropped entirely rather than cleaned, since there's nothing to keep.
_IGNORED_LINES = re.compile(
    r"^use the heaviest weight you can for each set\.?$",
    re.IGNORECASE,
)


def _clean_movement_line(line):
    line = line.strip()
    amrap_match = _AMRAP.match(line)
    if amrap_match:
        return f"AMRAP-{amrap_match.group(1)}:"
    for phrase in _NOISE_PHRASES:
        line = re.sub(re.escape(phrase), "", line, flags=re.IGNORECASE)
    line = _TRAILING_OF.sub(":", line)
    return line.strip().strip(",").strip()


def _movements_from_description(description):
    movements = []
    for raw_line in description.split("\n"):
        line = raw_line.strip()
        if not line or _SEPARATOR_LINE.match(line) or _IGNORED_LINES.match(line):
            continue
        cleaned = _clean_movement_line(line)
        if cleaned:
            movements.append(cleaned)
    return movements


def _hero_wod_name(entry):
    """
    BTWB's wod_title is always a generic section label ("CSC WOD"), but
    workout_name is a verbose restatement of the movements for a regular
    workout (e.g. "Power Snatch 1-1-1-1-1, rest 1:30") vs. just the actual
    name for a benchmark/hero WOD (e.g. "Randy") -- a single word is a
    reliable signal it's a real name worth showing, not a description.
    """
    name = ((entry.get("workout") or {}).get("workout_name") or "").strip()
    return name if name and len(name.split()) == 1 else None


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

        hero_name = _hero_wod_name(entry)
        if hero_name:
            # Hero WODs come with a memorial bio trailing the actual
            # movements, starting with the honoree's full name -- drop it,
            # and use the real name as the section title instead of the
            # generic "CSC WOD" label every entry otherwise gets.
            movements = [m for m in movements if not m.lower().startswith(hero_name.lower())]
            title = f'"{hero_name}"'

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
