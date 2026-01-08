#!/bin/bash
# Convenience script to run the uploader with environment variables

# Load .env file if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Run the uploader
uv run gdrive-upload
