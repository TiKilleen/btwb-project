FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements file first for better caching
COPY btwb-project/requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Install Playwright browsers and dependencies
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy all project files
COPY btwb-project/ .

# Debug: List files to see what got copied
RUN ls -la
RUN ls -la Fonts/ || echo "Fonts directory not found"
RUN ls -la fonts/ || echo "fonts directory not found"

# Create fonts directory if it doesn't exist and fix case sensitivity
RUN if [ -d "Fonts" ]; then ln -sf Fonts fonts; fi

# Set environment variables for Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms/playwright

# Expose port (Render will set the PORT environment variable)
EXPOSE $PORT

# Command to run your application
CMD ["python", "app.py"]