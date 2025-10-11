# Use even more lightweight base image
FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install system dependencies for Alpine
RUN apk add --no-cache gcc musl-dev libffi-dev

# Copy requirements first (for caching)
COPY requirements.txt .

# Install dependencies with optimizations
RUN pip install --no-cache-dir --compile -r requirements.txt

# Remove build dependencies to save space
RUN apk del gcc musl-dev libffi-dev

# Copy all app files
COPY . .

# Expose port
EXPOSE 8080

# Optimized command for B1 plan
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "120", "--preload", "app:server"]
