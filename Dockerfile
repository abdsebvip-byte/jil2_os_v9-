FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install system dependencies (if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose any needed ports (optional, e.g., for Flask health check)
# EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command runs the auto scanner
CMD ["python", "auto_scanner.py"]
