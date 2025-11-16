FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY src/ ./src/
COPY apim/ ./apim/

# Make both scripts executable
RUN chmod +x src/export_apim_stats.py src/display_stats.py

# Create output directory for JSON files
RUN mkdir -p /app/output

# Set Python path
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default command (can be overridden)
CMD ["python", "src/export_apim_stats.py"]

