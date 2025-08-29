# =========
# Dockerfile
# =========
# Base image with Python 3.11 (slim for smaller footprint)
FROM python:3.11-slim-bookworm

# Prevents Python from writing .pyc files and keeps logs unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Set working directory
WORKDIR /app

# Install system dependencies only if needed
# (Most of your requirements are pure-Python wheels and should not need build tools)
# If you later add libs that require compilation, uncomment the apt lines below.
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better layer caching), then install
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the app source
COPY . /app

# Create a non-root user and switch to it
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose Streamlit's default port
EXPOSE 8501

# Environment variables for Streamlit runtime (optional but helpful)
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Default command to run the app
# Note: ensure your main file is named app_fully_customized.py
CMD ["streamlit", "run", "app_fully_customized.py", "--server.port=8501", "--server.address=0.0.0.0"]

