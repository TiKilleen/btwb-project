from flask import Flask, send_file, request, render_template_string
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


def scrape_btwb_wod(widget_html, target_date_str):
    """
    Improved BTWB scraper with better error handling and container compatibility
    """
    # Parse the target date to ensure it's in the correct format
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        # Format the date as BTWB expects it (YYYY-M-D format, not zero-padded)
        formatted_date = f"{target_date.year}-{target_date.month}-{target_date.day}"
    except Exception as e:
        print(f"Error parsing target date: {e}")
        formatted_date = target_date_str
    
    # Replace data-days="0" with data-date="YYYY-M-D"
    updated_widget_html = re.sub(r'data-days="[^"]*"', '', widget_html)
    updated_widget_html = updated_widget_html.replace(
        'data-track_ids=310497',
        f'data-track_ids=310497 data-date="{formatted_date}"'
    )
    
    print(f"=== DEBUG: Widget HTML update ===")
    print(f"Target date: {target_date_str}")
    print(f"Formatted date: {formatted_date}")
    print("=== END WIDGET DEBUG ===")
    
    # Create a more robust HTML page with better error handling
    temp_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>BTWB Widget</title>
        <link rel="stylesheet" href="https://static.btwb.com/libs/webwidgets/2/webwidgets.css">
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/font-awesome/4.3.0/css/font-awesome.min.css">
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .loading {{ color: #666; }}
            .error {{ color: #ff0000; }}
        </style>
    </head>
    <body>
        <div id="loading" class="loading">Loading workout data...</div>
        {updated_widget_html}
        <script type="text/javascript" src="https://static.btwb.com/libs/webwidgets/2/webwidgets.js"></script>
        <script>
            console.log('Widget initialization starting...');
            
            // Monitor for content changes
            var checkCount = 0;
            var maxChecks = 30; // 30 seconds max
            
            function checkWidgetContent() {{
                checkCount++;
                var widget = document.querySelector('.btwb_webwidget');
                var loading = document.getElementById('loading');
                
                if (widget) {{
                    console.log('Widget found, checking content...');
                    console.log('Widget data-date:', widget.getAttribute('data-date'));
                    console.log('Widget innerHTML length:', widget.innerHTML.length);
                    
                    if (widget.innerHTML.trim() && widget.innerHTML.trim() !== '') {{
                        console.log('Widget has content!');
                        if (loading) loading.style.display = 'none';
                        return true;
                    }}
                }}
                
                if (checkCount >= maxChecks) {{
                    console.log('Max checks reached, stopping...');
                    if (loading) loading.innerHTML = 'Error: Widget failed to load';
                    return false;
                }}
                
                setTimeout(checkWidgetContent, 1000);
                return false;
            }}
            
            // Start checking after a brief delay
            setTimeout(checkWidgetContent, 2000);
        </script>
    </body>
    </html>
    """
    
    print(f"Requesting WOD for specific date: {formatted_date}")
    
    try:
        with sync_playwright() as p:
            # Launch browser with more robust settings for containerized environment
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-gpu',
                    '--no-zygote',
                    '--single-process'
                ]
            )
            
            context = browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                viewport={'width': 1280, 'height': 720},
                # Allow external resources
                permissions=['geolocation']
            )
            
            page = context.new_page()
            
            # Enhanced console logging
            def handle_console(msg):
                msg_type = msg.type
                msg_text = msg.text
                print(f"Browser console [{msg_type}]: {msg_text}")
                # Look for specific error patterns
                if 'error' in msg_type.lower() or 'failed' in msg_text.lower():
                    print(f"⚠️  Potential issue: {msg_text}")
            
            page.on("console", handle_console)
            
            # Handle page errors
            page.on("pageerror", lambda err: print(f"Page error: {err}"))
            
            # Handle network failures
            page.on("requestfailed", lambda request: print(f"Network request failed: {request.url}"))
            
            # Set the HTML content
            page.set_content(temp_html, wait_until="networkidle")
            
            # Wait for the widget to appear
            try:
                print("Waiting for widget to appear...")
                page.wait_for_selector(".btwb_webwidget", timeout=30000)
                print("Widget selector found!")
            except Exception as e:
                print(f"Warning: Widget selector not found: {e}")
            
            # Wait for external resources to load
            print("Waiting for network to be idle...")
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except Exception as e:
                print(f"Network idle timeout: {e}")
            
            # Additional wait for JavaScript execution
            print("Waiting for JavaScript to process...")
            page.wait_for_timeout(15000)  # 15 second wait
            
            # Check widget attributes
            try:
                widget_date = page.get_attribute(".btwb_webwidget", "data-date")
                print(f"Widget data-date attribute: {widget_date}")
            except Exception as e:
                print(f"Could not get widget date attribute: {e}")
            
            # Try multiple selectors to get content
            text = ""
            selectors_to_try = [
                ".btwb_webwidget",
                ".btwb_webwidget .wod",
                ".btwb_webwidget .workout",
                "body"
            ]
            
            for selector in selectors_to_try:
                try:
                    text = page.inner_text(selector)
                    if text and text.strip() and "loading" not in text.lower():
                        print(f"Got content from selector: {selector}")
                        break
                except Exception as e:
                    print(f"Failed to get text from {selector}: {e}")
                    continue
            
            # Enhanced debugging
            try:
                html_content = page.inner_html(".btwb_webwidget")
                print(f"=== DEBUG: Widget HTML content ===")
                print(html_content[:1000] + "..." if len(html_content) > 1000 else html_content)
                print("=== END HTML DEBUG ===")
            except Exception as e:
                print(f"Could not get widget HTML: {e}")
                
            # Try to get the full page HTML as fallback
            if not text or text.strip() == "":
                try:
                    full_html = page.content()
                    # Extract any workout-related content from the full HTML
                    if "workout" in full_html.lower() or "wod" in full_html.lower():
                        print("Found workout-related content in full HTML")
                        # You might want to add more sophisticated parsing here
                except Exception as e:
                    print(f"Could not get full page HTML: {e}")
            
            browser.close()
            
            print(f"=== Final scraped text (length: {len(text) if text else 0}) ===")
            print(repr(text[:500]) if text else "No text found")
            print("=== END FINAL TEXT ===")
            
            return text
            
    except Exception as e:
        print(f"Critical error in scraping: {e}")
        import traceback
        traceback.print_exc()
        return ""


def parse_wod_text_to_json(text):
    """
    Enhanced parser to handle multiple workouts with CSC-specific filtering
    """
    print(f"=== DEBUG: Raw scraped text ===")
    print(repr(text))
    print("=== END RAW TEXT DEBUG ===")
    
    # Phrases to filter out from workout text
    filter_phrases = [
        ", pick load", "pick load", "workout brief", ", scale as needed",
        "scale as needed", ", modify as needed", "modify as needed",
        ", rx+", "rx+", ", beginner", "beginner:", ", intermediate",
        "intermediate:", ", advanced", "advanced:"
    ]
    
    # Common prefixes to filter out (case insensitive)
    prefix_filters = [
        "main:", "ft:", "amrap:", "emom:", "tabata:", "strength:",
        "metcon:", "conditioning:", "warmup:", "warm-up:", "cool-down:",
        "cooldown:", "accessory:", "skills:", "mobility:"
    ]
    
    # Clean the text by removing filter phrases (case insensitive)
    cleaned_text = text
    for phrase in filter_phrases:
        cleaned_text = cleaned_text.replace(phrase.lower(), "")
        cleaned_text = cleaned_text.replace(phrase.upper(), "")
        cleaned_text = cleaned_text.replace(phrase.title(), "")
    
    lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]
    
    print(f"=== DEBUG: Cleaned lines ===")
    for i, line in enumerate(lines):
        print(f"{i}: {repr(line)}")
    print("=== END CLEANED LINES DEBUG ===")
    
    if not lines:
        return [{"title": "No WOD Found", "movements": ["Try a different date."]}]
    
    # Skip the first two lines as requested in original code
    if len(lines) > 2:
        lines = lines[2:]
        print(f"Skipped first 2 lines, now have {len(lines)} lines")
    
    # Try to detect multiple workouts
    workouts = []
    current_workout = None
    
    # Patterns that might indicate a new workout section
    workout_indicators = [
        r'^(strength|metcon|conditioning|amrap|emom|tabata|for time|every|rounds?|min|minutes?)',
        r'^\d+\s*(rounds?|min|minutes?|reps?)',
        r'^(part [a-z]|section [a-z]|\d+\)|\d+\.)',
        r'^(wod|workout)',
    ]
    
    for line in lines:
        # === CSC-SPECIFIC FILTERING ===
        
        # CSC WOD: Filter out RemReps patterns
        # Pattern: "5x 4 mins RemReps: Assault Bikes, Alternating Dumbbell Snatch..."
        if "remreps" in line.lower():
            print(f"CSC WOD: Filtering out RemReps line: {line}")
            continue
        
        # Also filter out lines that start with patterns like "5x 4 mins" followed by RemReps
        if re.match(r'^\d+x\s+\d+\s+mins?\s+remreps', line.lower()):
            print(f"CSC WOD: Filtering out RemReps pattern: {line}")
            continue
        
        # === END CSC REMREPS FILTERING ===
        
        # Check if this line starts with any filtered prefix
        should_skip = False
        for prefix in prefix_filters:
            if line.lower().startswith(prefix.lower()):
                should_skip = True
                print(f"Filtering out line with prefix '{prefix}': {line}")
                break
        
        if should_skip:
            continue
        
        # Clean the line
        cleaned_line = line.strip()
        for phrase in filter_phrases:
            cleaned_line = cleaned_line.replace(phrase.lower(), "")
            cleaned_line = cleaned_line.replace(phrase.upper(), "")
            cleaned_line = cleaned_line.replace(phrase.title(), "")
        
        cleaned_line = cleaned_line.strip().strip(',').strip()
        
        if not cleaned_line:
            continue
        
        # === EXISTING CSC-SPECIFIC FILTERING ===
        
        # CSC WOD: Remove everything after "AMRAP X" (including "mins", "min", "minutes")
        if cleaned_line.lower().startswith("amrap"):
            # Look for AMRAP pattern and truncate after the number
            amrap_match = re.search(r'(amrap\s+\d+)', cleaned_line.lower())
            if amrap_match:
                amrap_end = amrap_match.end()
                cleaned_line = cleaned_line[:amrap_end]
                print(f"CSC WOD: Truncated AMRAP line to: {cleaned_line}")
        
        # CSC WOD: Skip lines that start with "Complete as many" or similar
        if (cleaned_line.lower().startswith("complete as many") or
            cleaned_line.lower().startswith("complete as man") or
            cleaned_line.lower().startswith("as many rounds as possible")):
            print(f"CSC WOD: Skipping explanatory line: {cleaned_line}")
            continue
        
        # CSC Strength: Skip header lines that start with patterns like "3RFQ:", "3 RFQ:", etc.
        if (re.match(r'^\d+\s*[a-zA-Z]+:', cleaned_line) and 
            not cleaned_line.lower().startswith("csc")):
            print(f"CSC Strength: Skipping header line: {cleaned_line}")
            continue
        
        # === END EXISTING CSC-SPECIFIC FILTERING ===
        
        # Check if this might be a new workout title
        is_potential_title = False
        for pattern in workout_indicators:
            if re.search(pattern, cleaned_line.lower()):
                is_potential_title = True
                break
        
        # Also check for common title patterns
        title_patterns = [
            r'^[A-Z][A-Z\s]+$',  # All caps titles
            r'^\d+\s*x\s*\d+',   # "5 x 3" patterns
            r'^every\s+\d+',     # "Every 2 min"
            r'^\d+\s*rounds?',   # "5 rounds"
            r'^csc\s+(wod|strength)',  # CSC WOD or CSC Strength
        ]
        
        for pattern in title_patterns:
            if re.search(pattern, cleaned_line, re.IGNORECASE):
                is_potential_title = True
                break
        
        # If we think this is a title and we already have a workout started, save the previous one
        if is_potential_title and current_workout and current_workout.get("movements"):
            workouts.append(current_workout)
            current_workout = None
        
        # Start a new workout if we think this is a title
        if is_potential_title and not current_workout:
            current_workout = {
                "title": cleaned_line,
                "movements": []
            }
            print(f"Starting new workout: {cleaned_line}")
        elif current_workout:
            # Add to current workout movements
            current_workout["movements"].append(cleaned_line)
        else:
            # If we don't have a current workout, start one with generic title
            if not workouts:  # Only if this is the first line
                current_workout = {
                    "title": cleaned_line,
                    "movements": []
                }
    
    # Don't forget the last workout
    if current_workout:
        workouts.append(current_workout)
    
    # If we didn't find any workouts, create a single workout from all lines
    if not workouts and lines:
        workouts = [{
            "title": lines[0] if lines else "WOD",
            "movements": lines[1:] if len(lines) > 1 else []
        }]
    
    print(f"=== DEBUG: Final parsed workouts ===")
    for i, workout in enumerate(workouts):
        print(f"Workout {i+1}: {workout['title']}")
        print(f"  Movements: {workout['movements']}")
    print("=== END WORKOUT DEBUG ===")
    
    return workouts


def generate_image(wod_data):
    """
    Enhanced image generation to handle multiple workouts with CSC WOD special formatting
    """
    img = Image.new('RGB', (1080, 1920), color='white')
    draw = ImageDraw.Draw(img)
    
    # Check for font files and load them
    font_path = "Fonts/Staatliches-Regular.ttf"
    
    # Debug file system
    print(f"Current working directory: {os.getcwd()}")
    print(f"Files in current directory: {os.listdir('.')}")
    print(f"Fonts directory exists: {os.path.exists('fonts')}")
    if os.path.exists('fonts'):
        print(f"Files in fonts directory: {os.listdir('fonts')}")
    
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
    tomorrow = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    return render_template_string(f'''
        <h1>Generate BTWB Workout Poster</h1>
        <form action="/generate" method="get">
            <label for="date">Enter a date (YYYY-MM-DD):</label>
            <input type="text" name="date" id="date" value="{tomorrow}" required>
            <button type="submit">Generate</button>
        </form>
        <p><em>Note: Future dates will be fetched from BTWB if available</em></p>
    ''')


@app.route("/generate")
def generate():
    date_str = request.args.get("date")
    if not date_str:
        date_str = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    # BTWB widget HTML (data-days will be dynamically updated)
    widget_html = '''<div class="btwb_webwidget" data-type="wods" data-sections="main" data-track_ids=310497 data-activity_length="0" data-leaderboard_length="0" data-days="0"></div><script id="btwb_config" data-api_key=apry1ewoh2ssxeanwyne8lldq></script>'''
    
    try:
        print(f"Scraping BTWB widget for date: {date_str}")
        raw_wod_text = scrape_btwb_wod(widget_html, date_str)
        print(f"Raw WOD text: {raw_wod_text}")
        
        if raw_wod_text and raw_wod_text.strip():
            workouts = parse_wod_text_to_json(raw_wod_text)
            wod_data = {
                "date": date_str,
                "workouts": workouts
            }
            print("Successfully parsed BTWB data")
        else:
            print("No WOD text found, using sample data")
            wod_data = get_sample_wod(date_str)
            
    except Exception as e:
        print(f"Error scraping BTWB widget: {e}")
        wod_data = get_sample_wod(date_str)

    img_io = generate_image(wod_data)
    return send_file(img_io, mimetype='image/png', as_attachment=True, download_name='btwb_wod.png')


def get_wod_by_date(date_str):
    # This will eventually pull real WOD data
    return get_sample_wod(date_str)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
