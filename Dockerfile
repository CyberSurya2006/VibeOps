# Use a lightweight python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies needed for git checking
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install backend requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files and CLI utility
COPY backend/ ./backend/
COPY vibeops-cli.py .

# Expose backend API port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Command to run FastAPI server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
