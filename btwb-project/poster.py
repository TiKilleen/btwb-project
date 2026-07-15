import io
import logging
import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

CLASS_SCHEDULE = {
    "Monday": ["6AM", "9:30AM", "4:15PM", "5:30PM", "6:30PM"],
    "Tuesday": ["6AM", "9:30AM", "4:15PM", "5:30PM"],
    "Wednesday": ["6AM", "9:30AM", "4:15PM", "5:30PM", "6:30PM"],
    "Thursday": ["6AM", "9:30AM", "4:15PM", "5:30PM"],
    "Friday": ["6AM", "9:30AM", "4:15PM", "5:30PM"],
    "Saturday": ["8AM", "9AM"],
    "Sunday": ["10AM"],
}

# Always-true weekly rules: these days always run the same named WOD, shown
# as its own line directly above the class times.
DAY_LABELS = {
    "Saturday": "ENDURANCE WOD",
    "Sunday": "SUNDAY PUMP SWEAT WOD",
}

FONT_PATH = "fonts/Anton-Regular.ttf"
LOGO_PATH = "csc_logo.jpg"

# Matches the logo's actual red (most common pixel value sampled directly
# from csc_logo.jpg) rather than pure #FF0000, which reads brighter/more
# orange next to it.
BRAND_RED = "#CB2229"


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + " " + word if current_line else word
        if draw.textlength(test_line, font=font) <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    return lines


def _load_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError:
        logger.warning("Could not load %s, falling back to default font", FONT_PATH)
        return ImageFont.load_default()


def _line_height(font):
    # Different font families have very different ascent/descent proportions
    # at the same nominal size -- a fixed offset from font_size overlaps for
    # tall-glyph fonts. Measure the font's actual metrics instead.
    try:
        ascent, descent = font.getmetrics()
        return ascent + descent
    except AttributeError:
        return 30


def _is_csc_wod(workout):
    title_lower = workout["title"].lower()
    return (
        title_lower == "csc wod"
        or title_lower == "csc strength"
        or "pump" in title_lower
        or "ewod" in title_lower
    )


# How much bigger a section's "header line" reads than its body text --
# applies uniformly whether that header is an actual title (drawn via
# section_title_font) or a CSC WOD/Strength section's first movement line
# standing in for one (e.g. "Power Snatch 3-3-3"). Both are the same
# semantic role and should look it.
TITLE_SIZE_OFFSET = 8


def _fit_font_size(draw, movements, content_height, max_content_height, max_text_width, first_move_is_header=False, start_size=54, min_size=20):
    font_size = start_size
    while font_size > min_size:
        test_font = _load_font(font_size)
        test_header_font = _load_font(font_size + TITLE_SIZE_OFFSET)
        test_content_height = content_height
        for idx, move in enumerate(movements):
            font_for_line = test_header_font if (first_move_is_header and idx == 0) else test_font
            wrapped = wrap_text(draw, move.upper(), font_for_line, max_text_width)
            test_content_height += len(wrapped) * _line_height(font_for_line) + 15
        if test_content_height <= max_content_height:
            return font_size
        font_size -= 2
    return font_size


def generate_image(wod_data):
    """
    Render the 1080x1920 story-format WOD poster. Handles multiple workouts
    per day (equal vertical split with a separator line). The first movement
    line of every section (BTWB's rep/round scheme sentence, e.g. "4 rounds
    for time:") always renders as a black header line at title size, since
    it's structurally part of the header, not a real movement -- separately,
    CSC WOD / CSC Strength / Pump / eWOD titled sections suppress their
    (redundant) real title entirely.
    """
    img = Image.new("RGB", (1080, 1920), color="white")
    draw = ImageDraw.Draw(img)

    title_font = _load_font(54)
    header_font = _load_font(50)

    center_x = 540
    y = 150

    border_padding = 20
    border_thickness = 30
    draw.rectangle(
        [(border_padding, border_padding), (1080 - border_padding, 1920 - border_padding)],
        outline="black",
        width=border_thickness,
    )

    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo_width = 820
        logo_ratio = logo_width / logo.width
        logo_height = int(logo.height * logo_ratio)
        logo = logo.resize((logo_width, logo_height))
        logo_x = int((1080 - logo_width) / 2)
        img.paste(logo, (logo_x, y), logo)
        y += logo_height + 5
    except Exception:
        logger.exception("Could not load logo, falling back to text")
        draw.text((center_x, y), "CSC", font=title_font, fill=BRAND_RED, anchor="mm")
        y += 100

    try:
        selected_date = datetime.strptime(wod_data["date"], "%Y-%m-%d")
    except Exception:
        selected_date = datetime.today()

    weekday = selected_date.strftime("%A")

    day_label = DAY_LABELS.get(weekday)
    if day_label:
        draw.text((center_x, y), day_label, font=header_font, fill="black", anchor="mm")
        y += 55

    schedule_list = CLASS_SCHEDULE.get(weekday, [])
    schedule_text = " // ".join(schedule_list) if schedule_list else "No Classes Today"
    draw.text((center_x, y), schedule_text, font=header_font, fill="black", anchor="mm")
    y += 100

    workouts = wod_data.get("workouts", [])
    num_workouts = len(workouts)

    if num_workouts == 0:
        draw.text((center_x, y + 400), "No WOD Found", font=title_font, fill=BRAND_RED, anchor="mm")
        img_io = io.BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)
        return img_io

    footer_height = 100
    available_height = 1800 - y - footer_height
    workout_height = available_height // num_workouts
    max_text_width = 900

    # Pass 1: every section must render at the same font size, so fit each
    # workout independently first and use the smallest size any of them
    # needs -- mismatched sizes across sections on the same poster look
    # inconsistent, even though each one individually "fits".
    is_csc_wod_flags = [_is_csc_wod(w) for w in workouts]
    content_heights = [0 if is_csc else 80 for is_csc in is_csc_wod_flags]
    uniform_font_size = min(
        _fit_font_size(
            draw, workout["movements"], content_heights[i], workout_height - 40, max_text_width,
            first_move_is_header=True,
        )
        for i, workout in enumerate(workouts)
    )

    movement_font = _load_font(uniform_font_size)
    line_height = _line_height(movement_font)
    # Section headers shrink alongside the body text instead of staying
    # frozen at a fixed size -- applies both to real titles and to a CSC
    # WOD/Strength section's first movement line standing in for one.
    section_title_font = _load_font(uniform_font_size + TITLE_SIZE_OFFSET)
    header_line_height = _line_height(section_title_font)

    # Pass 2: render every section at that shared size.
    for i, workout in enumerate(workouts):
        workout_start_y = y + (i * workout_height)
        workout_end_y = workout_start_y + workout_height
        is_csc_wod = is_csc_wod_flags[i]

        final_content_height = content_heights[i]
        for move_index, move in enumerate(workout["movements"]):
            is_header_line = move_index == 0
            font_for_line = section_title_font if is_header_line else movement_font
            wrapped = wrap_text(draw, move.upper(), font_for_line, max_text_width)
            final_content_height += len(wrapped) * _line_height(font_for_line) + 15

        center_offset = (workout_height - final_content_height) // 2
        current_y = workout_start_y + center_offset

        if not is_csc_wod:
            draw.text((center_x, current_y), workout["title"].upper(), font=section_title_font, fill="black", anchor="mm")
            current_y += 80

        for move_index, move in enumerate(workout["movements"]):
            is_header_line = move_index == 0
            text_color = "black" if is_header_line else BRAND_RED
            font_for_line = section_title_font if is_header_line else movement_font
            line_height_for_line = header_line_height if is_header_line else line_height
            wrapped_lines = wrap_text(draw, move.upper(), font_for_line, max_text_width)
            for line in wrapped_lines:
                if current_y + line_height_for_line > workout_end_y - 20:
                    break
                draw.text((center_x, current_y), line, font=font_for_line, fill=text_color, anchor="mm")
                current_y += line_height_for_line
            current_y += 15

        if i < num_workouts - 1:
            line_y = workout_end_y - 10
            draw.line([(center_x - 400, line_y), (center_x + 400, line_y)], fill="gray", width=2)

    try:
        wod_date = datetime.strptime(wod_data["date"], "%Y-%m-%d")
        footer_text = f"WORKOUT OF THE DAY {wod_date.strftime('%B %d, %Y')}".upper()
    except Exception:
        footer_text = f"WORKOUT OF THE DAY {wod_data['date']}".upper()

    footer_y = 1850
    footer_font = _load_font(48)
    available_width = 1080 - (border_padding * 2) - 20
    text_width = draw.textlength(footer_text, font=footer_font)
    if text_width > available_width:
        scale_factor = available_width / text_width
        footer_font = _load_font(int(48 * scale_factor))

    draw.text((center_x, footer_y), footer_text, font=footer_font, fill="black", anchor="mm")

    img_io = io.BytesIO()
    img.save(img_io, "PNG")
    img_io.seek(0)
    return img_io
