# Use a lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app files
COPY . .

# Expose port
EXPOSE 8050

# Command to run app
CMD ["gunicorn", "app:server", "--bind", "0.0.0.0:8050", "--workers", "2"]
