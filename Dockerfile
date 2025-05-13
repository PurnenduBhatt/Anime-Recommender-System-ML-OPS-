FROM python:3.8-slim

# Environment variables to improve Python performance and behavior
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Install package in development mode
RUN pip install --default-timeout=100 --no-cache-dir -e .

# Install Filebeat for logs shipping to ELK stack
RUN curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-7.17.0-amd64.deb \
    && dpkg -i filebeat-7.17.0-amd64.deb \
    && rm filebeat-7.17.0-amd64.deb

# Copy Filebeat configuration
COPY config/filebeat.yml /etc/filebeat/filebeat.yml
RUN chmod go-w /etc/filebeat/filebeat.yml

# Run training pipeline
RUN python pipeline/training_pipeline.py

# Create directory for logs
RUN mkdir -p /app/logs && chmod 777 /app/logs

# Expose application port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start application and Filebeat
CMD service filebeat start && python application.py