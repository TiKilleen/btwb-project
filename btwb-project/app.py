from flask import Flask, send_file, request, render_template_string
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
import io
import os
import time
from datetime import datetime, timedelta

def get_sample_wod(date_str):
    # Stub test WODs
    wod_library = {
        "2025-07-05": {
            "title": "Every 2 min x 5",
            "movements": [
                "12 Kettlebell Swings",
                "10m Single Arm Front Rack Lunge x2",
                "Max Effort Double Unders"
            ]
        },
        "2025-07-04": {
            "title": "Hero WOD: DT",
            "movements": [
                "5 Rounds for Time:",
                "12 Deadlifts",
                "9 Hang Power Cleans",
                "6 Push Jerks"
            ]
        },
        "2025-07-07": {
           "title": "AMRAP 12",
           "movements": [
           "10 Dumbbell Snatches",
           "20 Box Jump Overs",
           "30 Wall Balls"
    ]
},
         "2025-07-08": {
           "title": "For Time",
           "movements": [
           "21-15-9",
           "Thrusters",
           "Pull-Ups"
    ]
}

    }

    wod = wod_library.get(date_str, {
        "title": "No WOD Found",
        "movements": ["Try a different date."]
    })

    return {
        "date": date_str,
        "title": wod["title"],
        "movements": wod["movements"]
    }


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


app = Flask(__name__)
CLASS_SCHEDULE = {
    "Monday": ["6AM", "9:30AM", "5:30PM", "6:30PM"],
    "Tuesday": ["6AM", "9:30AM", "5:30PM"],
    "Wednesday": ["6AM", "9:30AM", "5:30PM", "6:30PM"],
    "Thursday": ["6AM", "9:30AM", "5:30PM"],
    "Friday": ["6AM", "9:30AM", "5:30PM"],
    "Saturday": ["8AM", "9AM"],
    "Sunday": ["SUNDAY PUMP SWEAT - 10AM"]
}


def scrape_btwb_wod(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Macintosh)")
        page = context.new_page()
        page.goto(url, timeout=60000)
        time.sleep(8)
        text = page.inner_text(".btwb_webwidget")
        browser.close()
        return text

def parse_wod_text_to_json(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0] if lines else "WOD"
    movements = lines[1:] if len(lines) > 1 else []
    return {
        "title": title,
        "movements": movements
    }

    def generate_image(wod_data):
        from PIL import Image

        logo_path = os.path.join(os.path.dirname(__file__), "csc_logo.jpg")  # or .png
        logo_img = Image.open(logo_path).convert("RGBA")  # ✅ Convert for transparency

        img = Image.new('RGB', (1080, 1920), color='white')
        draw = ImageDraw.Draw(img)
        font_path = os.path.join(os.path.dirname(__file__), "Staatliches-Regular.ttf")
        center_x = 1080 // 2  # ✅ Define center X coordinate here
        y = 100


        # Draw WOD Title
        draw.text((center_x, y), wod_data["title"], font=title_font, fill="black", anchor="mm")
        y += 100  # spacing before movements

        try:

            title_font = ImageFont.truetype("/Users/timkilleen/Library/Fonts/Staatliches-Regular.ttf", 54)
            header_font = ImageFont.truetype("/Users/timkilleen/Library/Fonts/Staatliches-Regular.ttf", 42)
            movement_font = ImageFont.truetype("/Users/timkilleen/Library/Fonts/Staatliches-Regular.ttf", 42)
            footer_font = ImageFont.truetype("/Users/timkilleen/Library/Fonts/Staatliches-Regular.ttf", 32)
        except:
            title_font = header_font = movement_font = footer_font = ImageFont.load_default()
            print("Header font loaded:", header_font.getname())


        center_x = 540
        y = 150

        # Load and prepare logo image
        logo_path = os.path.join(os.path.dirname(__file__), "csc_logo.jpg")  # replace with   your  actual filename
    logo_img = Image.open(logo_path).convert("RGBA")

            # Draw Class Schedule based on selected WOD date
        try:
            selected_date = datetime.strptime(wod_data["date"], "%Y-%m-%d")
        except Exception:
            selected_date = datetime.today()

        weekday = selected_date.strftime("%A")
        schedule_list = CLASS_SCHEDULE.get(weekday, [])
        schedule_text = " // ".join(schedule_list) if schedule_list else "No Classes Today"
        draw.text((center_x, y), schedule_text, font=header_font, fill="black", anchor="mm")
            y += 100




        # 🔲 Thicker border with padding
        border_padding = 20
        border_thickness = 30
        draw.rectangle(
        [(border_padding, border_padding), (1080 - border_padding, 1920 - border_padding)],
        outline="black",
        width=border_thickness
    )

        # Header logo (fallback to text if needed)
        try:
            logo = Image.open("csc_logo.jpg").convert("RGBA")
            logo_width = 700
            logo_ratio = logo_width / logo.width
            logo_height = int(logo.height * logo_ratio)
            logo = logo.resize((logo_width, logo_height))
            logo_x = int((1080 - logo_width) / 2)
            img.paste(logo, (logo_x, y), logo if logo.mode == 'RGBA' else None)
            y += logo_height + 5
        except Exception as e:
            print(f"Error loading logo: {e}")
            draw.text((center_x, y), "CSC", font=title_font, fill="red", anchor="mm")
            y += 100

        # Class schedule
        from datetime import datetime

        # ⏰ Get today’s schedule dynamically
            print("Drawing schedule...")

        try:
            selected_date = datetime.strptime(wod_data["date"], "%Y-%m-%d")
        except Exception:
            selected_date = datetime.today()

        weekday = selected_date.strftime("%A")
        schedule_list = CLASS_SCHEDULE.get(weekday, [])
        schedule_text = " // ".join(schedule_list) if schedule_list else "No Classes Today"
        draw.text((center_x, y), schedule_text, font=header_font, fill="black", anchor="mm")
        y += 100


        # 🏋️ Movements: Auto-wrap and auto-scale
        y_start = y = 400
        max_y = 1800
        max_text_width = 900
        font_size = 54

        if wod_data["title"] == "No WOD Found":
            draw.text((center_x, y + 400), "Try a different date.", font=movement_font, fill="red", anchor="mm")

            # Save and return the image early
            img_io = io.BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            return img_io


        while font_size > 20:
            test_font = ImageFont.truetype(font_path, font_size)
            test_y = y_start
            fits = True


            for move in wod_data["movements"]:
                wrapped = wrap_text(draw, move.upper(), test_font, max_text_width)
                line_height = 65
                total_block_height = len(wrapped) * line_height + 25
                test_y += total_block_height
                if test_y > max_y:
                    fits = False
                    break

            if fits:
                break
            font_size -= 2

        # Use final font
        movement_font = ImageFont.truetype(font_path, font_size)
        y = y_start

        for move in wod_data["movements"]:
            wrapped_lines = wrap_text(draw, move.upper(), movement_font, max_text_width)
            for line in wrapped_lines:
                draw.text((center_x, y), line, font=movement_font, fill="red", anchor="mm")
                y += 65
            y += 25

        print("Auto-fit movement font size: {font_size}")




        # Dynamic footer using WOD date
        try:
            wod_date = datetime.strptime(wod_data["date"], "%Y-%m-%d")
            footer_text = f"WORKOUT OF THE DAY {wod_date.strftime('%B %d, %Y')}"
        except:
            footer_text = f"WORKOUT OF THE DAY {wod_data['date']}"


        # Export
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io

@app.route("/")
def home():
    tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    return render_template_string(f'''
        <h1>Generate BTWB Workout Poster</h1>
        <form action="/generate" method="get">
            <label for="date">Enter a date (YYYY-MM-DD):</label>
            <input type="text" name="date" id="date" value="{tomorrow}" required>
            <button type="submit">Generate</button>
        </form>
    ''')

@app.route("/generate")
def generate():
    date_str = request.args.get("date")
    if not date_str:
        date_str = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    wod_data = get_sample_wod(date_str)  # replace with real BTWB scraper later

    img_io = generate_image(wod_data)
    return send_file(img_io, mimetype='image/png', as_attachment=True, download_name='btwb_wod.png')

def get_wod_by_date(date_str):
    # This will eventually pull real WOD data
    return get_sample_wod(date_str)


if __name__ == "__main__":
    app.run(debug=True)
