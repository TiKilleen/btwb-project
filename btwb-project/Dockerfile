FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory
WORKDIR /app

# Set environment variables for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms/playwright
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# Copy requirements file first for better caching
COPY btwb-project/requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Install Playwright browsers with verbose output
RUN python -m playwright install chromium --with-deps

# Verify installation and show browser path
RUN python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); print(f'Browser path: {p.chromium.executable_path}'); p.stop()"

# Copy all project files
COPY btwb-project/ .

# Debug: List files to see what got copied
RUN ls -la
RUN ls -la Fonts/ || echo "Fonts directory not found"
RUN ls -la fonts/ || echo "fonts directory not found"

# Create fonts directory if it doesn't exist and fix case sensitivity
RUN if [ -d "Fonts" ]; then ln -sf Fonts fonts; fi

# Expose port (Render will set the PORT environment variable)
EXPOSE $PORT

# Command to run your application
CMD ["python", "app.py"]