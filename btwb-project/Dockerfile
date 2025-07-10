FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements file
COPY btwb-project/requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy all project files
COPY btwb-project/ .

# Debug: List files to see what got copied
RUN ls -la
RUN ls -la fonts/ || echo "fonts directory not found"

# Expose port (Render will set the PORT environment variable)
EXPOSE $PORT

# Command to run your application (replace 'app.py' with your main file)
CMD ["python", "app.py"]