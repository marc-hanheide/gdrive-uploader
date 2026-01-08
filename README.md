# Google Drive Uploader

Automated Google Drive uploader with duplicate detection. Only uploads files that don't already exist in your Google Drive (with MD5 checksum verification).

## Features

- ✅ One-time authentication (headless operation after initial setup)
- ✅ Duplicate detection with MD5 checksum comparison
- ✅ Pattern-based file selection (e.g., upload only PDFs)
- ✅ Upload to specific Google Drive folders
- ✅ Docker support for containerised deployment
- ✅ Built with `uv` for fast dependency management

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Google Cloud Project with Drive API enabled
- Docker (optional, for containerised deployment)

## Quick Start

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone/Extract this project

```bash
cd gdrive-uploader
```

### 3. Set up Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **Google Drive API**:
   - Navigate to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Choose "Desktop app"
   - Download the JSON file
   - Save it as `credentials.json` in this directory

### 4. Install dependencies

```bash
uv sync
```

### 5. First-time authentication

Create an `uploads` directory and add some test files:

```bash
mkdir uploads
echo "Test file" > uploads/test.txt
```

Run the uploader (this will open a browser for authentication):

```bash
uv run gdrive-upload
```

Follow the browser prompts to authenticate. A `token.pickle` file will be created for subsequent headless runs.

### 6. Subsequent runs (headless)

```bash
uv run gdrive-upload
```

## Configuration

Configure via environment variables:

```bash
# Upload directory
export UPLOAD_DIR="./uploads"

# Target Google Drive folder (optional - leave empty for root)
export DRIVE_FOLDER_ID="your-folder-id-here"

# File pattern (default: all files)
export FILE_PATTERN="*.pdf"  # Or *.jpg, *.txt, etc.

# MD5 checksum verification (default: true)
export CHECK_MD5="true"

# Force upload even if file exists (default: false)
export FORCE_UPLOAD="false"

# Run
uv run gdrive-upload
```

## Docker Usage

### Build the image

```bash
docker build -t gdrive-uploader .
```

### First-time authentication (requires display)

```bash
docker run -it --rm \
  -v $(pwd)/credentials.json:/app/credentials.json \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/token.pickle:/app/token.pickle \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  gdrive-uploader
```

### Subsequent headless runs

```bash
docker run --rm \
  -v $(pwd)/token.pickle:/app/token.pickle \
  -v $(pwd)/uploads:/app/uploads \
  gdrive-uploader
```

### Using Docker Compose

Edit `docker-compose.yml` to configure your settings, then:

```bash
# First run (with browser authentication)
docker-compose run --rm drive-uploader

# Subsequent runs
docker-compose up
```

## Finding Your Google Drive Folder ID

To upload to a specific folder:

1. Open Google Drive in your browser
2. Navigate to the folder you want to upload to
3. Look at the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`
4. Copy the `FOLDER_ID_HERE` part
5. Set it as `DRIVE_FOLDER_ID` environment variable

## Automated Uploads with Cron

Add to your crontab for automated uploads:

```bash
# Edit crontab
crontab -e

# Add line to run daily at 2 AM
0 2 * * * cd /path/to/gdrive-uploader && /home/user/.local/bin/uv run gdrive-upload >> /var/log/gdrive-uploader.log 2>&1
```

Or with Docker:

```bash
0 2 * * * docker run --rm -v /path/to/token.pickle:/app/token.pickle -v /path/to/uploads:/app/uploads gdrive-uploader >> /var/log/gdrive-uploader.log 2>&1
```

## How It Works

1. **Duplicate Detection**: Before uploading, checks if a file with the same name exists in Google Drive
2. **MD5 Verification**: Compares MD5 checksums to ensure file content matches (can be disabled)
3. **Skip Unchanged Files**: Only uploads files that are new or have changed
4. **Summary Report**: Shows how many files were uploaded vs. skipped

## Troubleshooting

### "File not found: credentials.json"

Make sure you've downloaded your OAuth credentials from Google Cloud Console and saved them as `credentials.json`.

### Browser doesn't open for authentication

If running in a headless environment, you need to perform the first authentication on a machine with a browser, then copy the `token.pickle` file to your server.

### Permission denied errors

The OAuth credentials need the correct scope. This project uses `drive.file` scope which only allows access to files created by this application. To access all files, you'd need to modify the `SCOPES` variable in `gdrive_uploader.py`.

## Development

To modify the code:

```bash
# Make changes to gdrive_uploader.py

# Run without installing
uv run python gdrive_uploader.py

# Or use the CLI entry point
uv run gdrive-upload
```

## License

MIT License - feel free to use and modify as needed.
