FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy all project files
COPY . .

# Expose port (adjust if your app uses a different port)
EXPOSE 5000

# Command to run your application (replace 'app.py' with your main file)
CMD ["python", "app.py"]
