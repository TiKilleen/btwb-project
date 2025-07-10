from flask import Flask, send_file, request, render_template, url_for
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
import io
import os
import time
import re
from datetime import datetime, timedelta

def get_sample_wod(date_str):
    # Stub test WODs - now includes multiple workouts for some dates
    wod_library = {
        "2025-07-05": [
            {
                "title": "Every 2 min x 5",
                "movements": [
                    "12 Kettlebell Swings",
                    "10m Single Arm Front Rack Lunge x2",
                    "Max Effort Double Unders"
                ]
            }
        ],
        "2025-07-04": [
            {
                "title": "Hero WOD: DT",
                "movements": [
                    "5 Rounds for Time:",
                    "12 Deadlifts",
                    "9 Hang Power Cleans",
                    "6 Push Jerks"
                ]
            }
        ],
        "2025-07-07": [
            {
                "title": "Strength",
                "movements": [
                    "Back Squat",
                    "3-3-3-3-3",
                    "Building to heavy triple"
                ]
            },
            {
                "title": "AMRAP 12",
                "movements": [
                    "10 Dumbbell Snatches",
                    "20 Box Jump Overs",
                    "30 Wall Balls"
                ]
            }
        ],
        "2025-07-08": [
            {
                "title": "For Time",
                "movements": [
                    "21-15-9",
                    "Thrusters",
                    "Pull-Ups"
                ]
            }
        ],
        "2025-07-09": [
            {
                "title": "EMOM 20",
                "movements": [
                    "Min 1: 15 Air Squats",
                    "Min 2: 10 Push-Ups",
                    "Min 3: 5 Burpees",
                    "Min 4: 20 Mountain Climbers"
                ]
            }
        ]
    }

    workouts = wod_library.get(date_str, [
        {
            "title": "No WOD Found",
            "movements": ["Try a different date."]
        }
    ])

    return {
        "date": date_str,
        "workouts": workouts
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

def get_wod_by_date(date_str):
    return get_sample_wod(date_str)

def generate_image(wod_data):
    """
    Enhanced image generation to handle multiple workouts with CSC WOD special formatting
    """
    img = Image.new('RGB', (1080, 1920), color='white')
    draw = ImageDraw.Draw(img)
    
    # Check for font files and load them
    font_path = "Fonts/Staatliches-Regular.ttf"
    
    # Load fonts with proper error handling
    try:
        title_font = ImageFont.truetype(font_path, 54)
        header_font = ImageFont.truetype(font_path, 42)
        movement_font = ImageFont.truetype(font_path, 42)
        footer_font = ImageFont.truetype(font_path, 32)
        footer_font_large = ImageFont.truetype(font_path, 48)
    except OSError as e:
        print(f"Font loading error: {e}")
        # Use fallback font
        title_font = header_font = movement_font = footer_font = footer_font_large = ImageFont.load_default()
        print("Using default fonts")

    center_x = 540
    y = 150

    # Thicker border with padding
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

    # Get schedule for the date
    try:
        selected_date = datetime.strptime(wod_data["date"], "%Y-%m-%d")
    except Exception:
        selected_date = datetime.today()

    weekday = selected_date.strftime("%A")
    schedule_list = CLASS_SCHEDULE.get(weekday, [])
    schedule_text = " // ".join(schedule_list) if schedule_list else "No Classes Today"
    draw.text((center_x, y), schedule_text, font=header_font, fill="black", anchor="mm")
    y += 100

    # Handle multiple workouts
    workouts = wod_data.get("workouts", [])
    num_workouts = len(workouts)
    
    if num_workouts == 0:
        draw.text((center_x, y + 400), "No WOD Found", font=title_font, fill="red", anchor="mm")
        img_io = io.BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io
    
    # Calculate available space for workouts
    footer_height = 100
    available_height = 1800 - y - footer_height
    workout_height = available_height // num_workouts
    
    print(f"Generating image for {num_workouts} workouts, {workout_height}px each")
    
    max_text_width = 900
    
    for i, workout in enumerate(workouts):
        workout_start_y = y + (i * workout_height)
        workout_end_y = workout_start_y + workout_height
        
        # Handle CSC WOD special case (also applies to Pump and eWOD)
        workout_title_lower = workout["title"].lower()
        is_csc_wod = (workout_title_lower == "csc wod" or 
                     workout_title_lower == "csc strength" or
                     "pump" in workout_title_lower or 
                     "ewod" in workout_title_lower)
        
        # Handle "No WOD Found" case
        if workout["title"] == "No WOD Found":
            center_y = workout_start_y + (workout_height // 2)
            draw.text((center_x, center_y), "Try a different date.", font=movement_font, fill="red", anchor="mm")
            continue
        
        # Calculate total content height for this workout to center it
        content_height = 0
        if not is_csc_wod:
            content_height += 80  # Title height
        
        # Calculate movement heights with optimal font size
        font_size = 54
        while font_size > 20:
            test_font = ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else ImageFont.load_default()
            test_content_height = content_height
            
            for move in workout["movements"]:
                wrapped = wrap_text(draw, move.upper(), test_font, max_text_width)
                line_height = max(30, font_size - 10)
                total_block_height = len(wrapped) * line_height + 15
                test_content_height += total_block_height
            
            if test_content_height <= workout_height - 40:  # 40px buffer
                break
            font_size -= 2
        
        # Calculate final content height with chosen font
        movement_font = ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else ImageFont.load_default()
        line_height = max(30, font_size - 10)
        
        final_content_height = content_height
        for move in workout["movements"]:
            wrapped = wrap_text(draw, move.upper(), movement_font, max_text_width)
            total_block_height = len(wrapped) * line_height + 15
            final_content_height += total_block_height
        
        # Center the workout content within its allocated space
        center_offset = (workout_height - final_content_height) // 2
        current_y = workout_start_y + center_offset
        
        # Draw workout title (skip for CSC WOD, CSC Strength, Pump, and eWOD)
        if not is_csc_wod:
            draw.text((center_x, current_y), workout["title"], font=title_font, fill="black", anchor="mm")
            current_y += 80
        
        # Draw movements with final font size
        for move_index, move in enumerate(workout["movements"]):
            # For CSC WOD, CSC Strength, Pump, and eWOD: make the first movement black instead of red
            if is_csc_wod and move_index == 0:
                text_color = "black"
                print(f"Special formatting: Making first movement black: {move}")
            else:
                text_color = "red"
            
            wrapped_lines = wrap_text(draw, move.upper(), movement_font, max_text_width)
            for line in wrapped_lines:
                if current_y + line_height > workout_end_y - 20:
                    break  # Don't overflow into next workout space
                draw.text((center_x, current_y), line, font=movement_font, fill=text_color, anchor="mm")
                current_y += line_height
            current_y += 15
        
        # Add separator line between workouts (except for last workout)
        if i < num_workouts - 1:
            line_y = workout_end_y - 10
            draw.line([(center_x - 400, line_y), (center_x + 400, line_y)], fill="gray", width=2)
    
    # Dynamic footer using WOD date
    try:
        wod_date = datetime.strptime(wod_data["date"], "%Y-%m-%d")
        footer_text = f"WORKOUT OF THE DAY {wod_date.strftime('%B %d, %Y')}"
    except:
        footer_text = f"WORKOUT OF THE DAY {wod_data['date']}"

    # Draw footer text at bottom of image
    footer_y = 1850
    footer_font_large = ImageFont.truetype(font_path, 48) if os.path.exists(font_path) else ImageFont.load_default()
    
    # Calculate text width and scale to fit image width minus border padding
    available_width = 1080 - (border_padding * 2) - 20
    text_width = draw.textlength(footer_text, font=footer_font_large)
    
    if text_width > available_width:
        scale_factor = available_width / text_width
        new_font_size = int(48 * scale_factor)
        footer_font_large = ImageFont.truetype(font_path, new_font_size) if os.path.exists(font_path) else ImageFont.load_default()
    
    draw.text((center_x, footer_y), footer_text, font=footer_font_large, fill="black", anchor="mm")

    # Export
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io


@app.route("/")
def home():
    default_date = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    return render_template("home.html", default_date=default_date)


@app.route("/generate")
def generate():
    print("=== DEBUG: /generate route called ===")
    date_str = request.args.get("date")
    if not date_str:
        date_str = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"Date parameter: {date_str}")
    
    wod_data = get_wod_by_date(date_str)
    print(f"WOD data: {wod_data}")

    img_io = generate_image(wod_data)

    # Save image temporarily
    os.makedirs("static", exist_ok=True)
    image_path = os.path.join("static", "preview.png")
    with open(image_path, "wb") as f:
        f.write(img_io.getvalue())
    
    print(f"Image saved to: {image_path}")

    # Reset and return the image
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png', as_attachment=True, download_name=f'wod_{date_str}.png')


@app.route("/debug")
def debug():
    """Debug route to test if Flask is running"""
    return f"<h1>Flask is working!</h1><p>Time: {datetime.now()}</p><p>Debug route successful</p>"


@app.route("/health")
def health():
    """Health check for Render"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# NEW DEBUG ROUTES
@app.route("/routes")
def list_routes():
    """List all available routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': rule.rule
        })
    return {
        "routes": routes,
        "total_routes": len(routes)
    }


@app.route("/template-test")
def template_test():
    """Test template rendering"""
    try:
        # Check if templates directory exists
        templates_dir = os.path.join(os.getcwd(), 'templates')
        home_html_path = os.path.join(templates_dir, 'home.html')
        
        debug_info = {
            "templates_dir_exists": os.path.exists(templates_dir),
            "templates_dir_path": templates_dir,
            "home_html_exists": os.path.exists(home_html_path),
            "home_html_path": home_html_path,
            "current_working_directory": os.getcwd(),
            "files_in_cwd": os.listdir(os.getcwd()) if os.path.exists(os.getcwd()) else "Cannot list files"
        }
        
        if os.path.exists(templates_dir):
            debug_info["files_in_templates"] = os.listdir(templates_dir)
        
        if os.path.exists(home_html_path):
            with open(home_html_path, 'r') as f:
                debug_info["home_html_content_preview"] = f.read()[:500] + "..." if len(f.read()) > 500 else f.read()
        
        # Try to render the template
        try:
            default_date = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
            rendered = render_template("home.html", default_date=default_date)
            debug_info["template_render_success"] = True
            debug_info["rendered_content_preview"] = rendered[:500] + "..." if len(rendered) > 500 else rendered
        except Exception as e:
            debug_info["template_render_success"] = False
            debug_info["template_render_error"] = str(e)
        
        return debug_info
        
    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}


@app.route("/file-system-debug")
def file_system_debug():
    """Debug file system structure"""
    try:
        cwd = os.getcwd()
        debug_info = {
            "current_working_directory": cwd,
            "files_and_dirs": {}
        }
        
        # List all files and directories in current directory
        for item in os.listdir(cwd):
            item_path = os.path.join(cwd, item)
            if os.path.isdir(item_path):
                try:
                    debug_info["files_and_dirs"][item] = {
                        "type": "directory",
                        "contents": os.listdir(item_path)
                    }
                except PermissionError:
                    debug_info["files_and_dirs"][item] = {
                        "type": "directory",
                        "contents": "Permission denied"
                    }
            else:
                debug_info["files_and_dirs"][item] = {
                    "type": "file",
                    "size": os.path.getsize(item_path)
                }
        
        return debug_info
        
    except Exception as e:
        return {"error": str(e), "error_type": type(e).__name__}


if __name__ == '__main__':
    print("=== Starting Flask App ===")
    print(f"Templates folder exists: {os.path.exists('templates')}")
    print(f"home.html exists: {os.path.exists('templates/home.html')}")
    
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
