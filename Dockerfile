FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Copy project files
COPY pyproject.toml /app/
COPY gdrive_uploader.py /app/

# Install dependencies
RUN uv sync --frozen

# Create directories for credentials and data
RUN mkdir -p /app/credentials /app/uploads

# Set environment variables
ENV UPLOAD_DIR=/app/uploads
ENV PYTHONUNBUFFERED=1

# Use uv to run the application
CMD ["uv", "run", "gdrive-upload"]
