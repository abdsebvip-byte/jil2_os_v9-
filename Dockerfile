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

# Expose the port Render expects
EXPOSE 10000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

# Default command runs Flask app (which starts scanner in background)
CMD ["python", "app.py"]
