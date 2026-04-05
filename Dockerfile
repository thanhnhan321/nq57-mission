# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=core.settings

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget curl nano \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /dist

# Copy project files
COPY . /dist

# Install Python dependencies
RUN pip install -r requirements.txt

RUN chmod +x /dist/linux-start.sh

# Expose port 8000 for the application
EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["/dist/linux-start.sh"]

