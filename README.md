# Google Drive Uploader

Automated Google Drive uploader with duplicate detection. Only uploads files that don't already exist in your Google Drive (with MD5 checksum verification).

## Features

- ✅ Headless authentication with manual code entry option
- ✅ One-time authentication (runs headless after initial setup)
- ✅ Duplicate detection with MD5 checksum comparison
- ✅ Pattern-based file selection (e.g., upload only PDFs)
- ✅ Upload to specific Google Drive folders
- ✅ Daemon mode for continuous monitoring
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
   - Choose **"Desktop app"** (or "TVs and Limited Input devices" for pure device flow)
   - Give it a name (e.g., "Drive Uploader")
   - Download the JSON file
   - Save it as `credentials.json` in this directory

   **Note**: Desktop app type supports both authentication modes.

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

Run the uploader. There are two authentication modes:

#### Option A: Automatic Mode (default)

```bash
uv run gdrive-upload
```

This starts a local server and displays a URL. Open that URL in a browser (can be on another machine) to authorize.

#### Option B: Manual Mode (for headless servers)

```bash
MANUAL_AUTH=true uv run gdrive-upload
```

You'll see output like:

```
============================================================
MANUAL AUTHENTICATION (HEADLESS MODE)
============================================================
Please visit this URL in a browser (on any device):

https://accounts.google.com/o/oauth2/auth?client_id=...

After authorizing, you will receive an authorization code.
============================================================
Enter the authorization code here: 
```

**On any device (phone, tablet, computer):**
1. Visit the URL shown
2. Sign in with your Google account and grant permissions
3. Copy the authorization code displayed
4. Paste it into the terminal prompt
5. Press Enter

A `token.pickle` file will be created for subsequent headless runs.

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

## Daemon Mode

Run the uploader continuously to monitor for new files and upload them automatically at regular intervals.

### Enable Daemon Mode

```bash
# Run in daemon mode with 5-minute intervals (default)
export DAEMON_MODE="true"
uv run gdrive-upload
```

### Configure Check Interval

```bash
# Check every 60 seconds (1 minute)
export DAEMON_MODE="true"
export CHECK_INTERVAL="60"
uv run gdrive-upload

# Check every 1800 seconds (30 minutes)
export DAEMON_MODE="true"
export CHECK_INTERVAL="1800"
uv run gdrive-upload
```

The daemon will:
- ✅ Run continuously checking for new/modified files
- ✅ Upload files at the specified interval (default: 300 seconds / 5 minutes)
- ✅ Show timestamped run information for each check
- ✅ Handle errors gracefully and retry on the next interval
- ✅ Respond to Ctrl+C for clean shutdown

### Docker Daemon Mode

Run as a continuous background service:

```bash
docker run -d \
  --name gdrive-uploader-daemon \
  --restart unless-stopped \
  -e DAEMON_MODE="true" \
  -e CHECK_INTERVAL="300" \
  -v $(pwd)/token.pickle:/app/token.pickle \
  -v $(pwd)/uploads:/app/uploads \
  ghcr.io/marc-hanheide/gdrive-uploader:latest
```

View logs:
```bash
docker logs -f gdrive-uploader-daemon
```

Stop the daemon:
```bash
docker stop gdrive-uploader-daemon
```

### Docker Compose Daemon Mode

Update your `docker-compose.yml`:

```yaml
version: '3.8'

services:
  drive-uploader:
    image: ghcr.io/marc-hanheide/gdrive-uploader:latest
    restart: unless-stopped
    volumes:
      - ./credentials.json:/app/credentials.json
      - ./token.pickle:/app/token.pickle
      - ./uploads:/app/uploads
    environment:
      - DAEMON_MODE=true
      - CHECK_INTERVAL=300
      - UPLOAD_DIR=/app/uploads
      - FILE_PATTERN=*
      - CHECK_MD5=true
```

Then run:
```bash
docker-compose up -d
```

## Docker Usage

### Using Pre-built Images (Recommended)

Pre-built Docker images are automatically published to GitHub Container Registry on every release.

```bash
# Pull the latest version
docker pull ghcr.io/marc-hanheide/gdrive-uploader:latest

# Or pull a specific version
docker pull ghcr.io/marc-hanheide/gdrive-uploader:1.0.0
```

Available tags:
- `latest` - Latest stable release from main branch
- `1.0.0`, `1.0`, `1` - Semantic version tags (e.g., for v1.0.0 release)
- `main` - Latest build from main branch
- `main-abc1234` - Specific commit from main branch

### Build the image locally

If you prefer to build locally:

```bash
docker build -t gdrive-uploader .
```

### First-time authentication

#### Option A: Automatic Mode

```bash
docker run -it --rm \
  -v $(pwd)/credentials.json:/app/credentials.json \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/token.pickle:/app/token.pickle \
  -p 8080:8080 \
  ghcr.io/marc-hanheide/gdrive-uploader:latest
```

Open the URL shown in another browser to authorize.

#### Option B: Manual Mode (recommended for servers)

```bash
docker run -it --rm \
  -e MANUAL_AUTH=true \
  -v $(pwd)/credentials.json:/app/credentials.json \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/token.pickle:/app/token.pickle \
  ghcr.io/marc-hanheide/gdrive-uploader:latest
```

Copy the URL to any browser, authorize, and paste the code back into the terminal.

### Subsequent headless runs

```bash
docker run --rm \
  -v $(pwd)/token.pickle:/app/token.pickle \
  -v $(pwd)/uploads:/app/uploads \
  ghcr.io/marc-hanheide/gdrive-uploader:latest
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

For scheduled uploads at specific times, you can use cron jobs. For continuous monitoring, consider using [Daemon Mode](#daemon-mode) instead.

Add to your crontab for automated uploads:

```bash
# Edit crontab
crontab -e

# Add line to run daily at 2 AM
0 2 * * * cd /path/to/gdrive-uploader && /home/user/.local/bin/uv run gdrive-upload >> /var/log/gdrive-uploader.log 2>&1
```

Or with Docker:

```bash
0 2 * * * docker run --rm -v /path/to/token.pickle:/app/token.pickle -v /path/to/uploads:/app/uploads ghcr.io/marc-hanheide/gdrive-uploader:latest >> /var/log/gdrive-uploader.log 2>&1
```

## Creating a Release

To create a new version release and trigger automated Docker builds:

```bash
# Tag the release with semantic versioning
git tag v1.0.0
git push origin v1.0.0
```

This will automatically:
- Build the Docker image
- Push it to GitHub Container Registry with tags: `1.0.0`, `1.0`, `1`, and `latest`
- Make it available at `ghcr.io/marc-hanheide/gdrive-uploader:1.0.0`

## How It Works

1. **Duplicate Detection**: Before uploading, checks if a file with the same name exists in Google Drive
2. **MD5 Verification**: Compares MD5 checksums to ensure file content matches (can be disabled)
3. **Skip Unchanged Files**: Only uploads files that are new or have changed
4. **Summary Report**: Shows how many files were uploaded vs. skipped

## Troubleshooting

### "File not found: credentials.json"

Make sure you've downloaded your OAuth credentials from Google Cloud Console and saved them as `credentials.json`.

### Authentication on headless servers

**Recommended approach** - Use manual auth mode:

```bash
MANUAL_AUTH=true uv run gdrive-upload
```

This displays a URL you can visit on any device (phone, computer, etc.). After authorizing, you'll get a code to paste back into the terminal.

**Alternative** - If you have SSH access with port forwarding, you can use automatic mode and forward the port to access the authorization URL.

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