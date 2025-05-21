FROM python:3.8-slim

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libatlas-base-dev \
    libhdf5-dev \
    libprotobuf-dev \
    protobuf-compiler \
    python3-dev \
    curl \
    pkg-config \
    adduser \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Update pip and install wheel and gunicorn
RUN pip install --default-timeout=100 --no-cache-dir pip wheel gunicorn -U

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt || { echo "pip install failed"; exit 1; }

# Copy source code
COPY . .

# Install package in development mode
RUN pip install --default-timeout=100 --no-cache-dir -e .

# Install Filebeat for ARM64
RUN curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-7.17.0-arm64.deb \
    && dpkg -i filebeat-7.17.0-arm64.deb || { echo "Filebeat installation failed"; exit 1; } \
    && rm filebeat-7.17.0-arm64.deb

# Copy Filebeat configuration
COPY config/filebeat.yml /etc/filebeat/filebeat.yml
RUN chmod go-w /etc/filebeat/filebeat.yml

# Run training pipeline
RUN python -m pipeline/training_pipeline.py

# Create logs directory
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start application and Filebeat
CMD ["/bin/sh", "-c", "filebeat -e & gunicorn -b 0.0.0.0:5000 application:app"]
