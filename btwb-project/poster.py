import io
import logging
import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

CLASS_SCHEDULE = {
    "Monday": ["6AM", "9:30AM", "5:30PM", "6:30PM"],
    "Tuesday": ["6AM", "9:30AM", "5:30PM"],
    "Wednesday": ["6AM", "9:30AM", "5:30PM", "6:30PM"],
    "Thursday": ["6AM", "9:30AM", "5:30PM"],
    "Friday": ["6AM", "9:30AM", "5:30PM"],
    "Saturday": ["8AM", "9AM"],
    "Sunday": ["SUNDAY PUMP SWEAT - 10AM"],
}

FONT_PATH = "Fonts/Staatliches-Regular.ttf"
LOGO_PATH = "csc_logo.jpg"


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


def generate_image(wod_data):
    """
    Render the 1080x1920 story-format WOD poster. Handles multiple workouts
    per day (equal vertical split with a separator line) and the CSC WOD /
    CSC Strength / Pump / eWOD special case (no title drawn, first movement
    line black instead of red).
    """
    img = Image.new("RGB", (1080, 1920), color="white")
    draw = ImageDraw.Draw(img)

    title_font = _load_font(54)
    header_font = _load_font(42)

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
        logo_width = 700
        logo_ratio = logo_width / logo.width
        logo_height = int(logo.height * logo_ratio)
        logo = logo.resize((logo_width, logo_height))
        logo_x = int((1080 - logo_width) / 2)
        img.paste(logo, (logo_x, y), logo)
        y += logo_height + 5
    except Exception:
        logger.exception("Could not load logo, falling back to text")
        draw.text((center_x, y), "CSC", font=title_font, fill="red", anchor="mm")
        y += 100

    try:
        selected_date = datetime.strptime(wod_data["date"], "%Y-%m-%d")
    except Exception:
        selected_date = datetime.today()

    weekday = selected_date.strftime("%A")
    schedule_list = CLASS_SCHEDULE.get(weekday, [])
    schedule_text = " // ".join(schedule_list) if schedule_list else "No Classes Today"
    draw.text((center_x, y), schedule_text, font=header_font, fill="black", anchor="mm")
    y += 100

    workouts = wod_data.get("workouts", [])
    num_workouts = len(workouts)

    if num_workouts == 0:
        draw.text((center_x, y + 400), "No WOD Found", font=title_font, fill="red", anchor="mm")
        img_io = io.BytesIO()
        img.save(img_io, "PNG")
        img_io.seek(0)
        return img_io

    footer_height = 100
    available_height = 1800 - y - footer_height
    workout_height = available_height // num_workouts
    max_text_width = 900

    for i, workout in enumerate(workouts):
        workout_start_y = y + (i * workout_height)
        workout_end_y = workout_start_y + workout_height

        workout_title_lower = workout["title"].lower()
        is_csc_wod = (
            workout_title_lower == "csc wod"
            or workout_title_lower == "csc strength"
            or "pump" in workout_title_lower
            or "ewod" in workout_title_lower
        )

        content_height = 0 if is_csc_wod else 80

        # Shrink the movement font until everything fits this workout's slot.
        font_size = 54
        while font_size > 20:
            test_font = _load_font(font_size)
            test_content_height = content_height
            for move in workout["movements"]:
                wrapped = wrap_text(draw, move.upper(), test_font, max_text_width)
                line_height = max(30, font_size - 10)
                test_content_height += len(wrapped) * line_height + 15
            if test_content_height <= workout_height - 40:
                break
            font_size -= 2

        movement_font = _load_font(font_size)
        line_height = max(30, font_size - 10)

        final_content_height = content_height
        for move in workout["movements"]:
            wrapped = wrap_text(draw, move.upper(), movement_font, max_text_width)
            final_content_height += len(wrapped) * line_height + 15

        center_offset = (workout_height - final_content_height) // 2
        current_y = workout_start_y + center_offset

        if not is_csc_wod:
            draw.text((center_x, current_y), workout["title"], font=title_font, fill="black", anchor="mm")
            current_y += 80

        for move_index, move in enumerate(workout["movements"]):
            text_color = "black" if (is_csc_wod and move_index == 0) else "red"
            wrapped_lines = wrap_text(draw, move.upper(), movement_font, max_text_width)
            for line in wrapped_lines:
                if current_y + line_height > workout_end_y - 20:
                    break
                draw.text((center_x, current_y), line, font=movement_font, fill=text_color, anchor="mm")
                current_y += line_height
            current_y += 15

        if i < num_workouts - 1:
            line_y = workout_end_y - 10
            draw.line([(center_x - 400, line_y), (center_x + 400, line_y)], fill="gray", width=2)

    try:
        wod_date = datetime.strptime(wod_data["date"], "%Y-%m-%d")
        footer_text = f"WORKOUT OF THE DAY {wod_date.strftime('%B %d, %Y')}"
    except Exception:
        footer_text = f"WORKOUT OF THE DAY {wod_data['date']}"

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
