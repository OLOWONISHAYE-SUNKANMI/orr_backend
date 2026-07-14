FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Create logs directory
RUN mkdir -p /app/logs

# Fix line endings and permissions for entrypoint script
RUN dos2unix /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Start app
ENTRYPOINT ["/app/entrypoint.sh"]
