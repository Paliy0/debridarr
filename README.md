# Real-Debrid Download Automation

A Python-based automation tool for downloading via Real-Debrid API, deployable as a Docker container via Portainer.

## Features

- **Unrestrict links**: Convert hoster links to direct download URLs
- **Torrent support**: Add magnet links or torrent files, select files, download
- **Web API**: FastAPI-based REST interface for on-demand usage
- **CLI tool**: Command-line interface for SSH-based usage
- **Progress tracking**: Real-time download progress via API
- **Concurrent downloads**: Configurable parallel downloads

## Quick Start

### 1. Get your Real-Debrid API token

Go to https://real-debrid.com/apitoken and copy your token.

### 2. Deploy via Portainer (Recommended)

1. In Portainer (http://portainer.local:9000), create a new stack
2. Use the `docker-compose.yml` from this repo
3. Set the `RD_TOKEN` environment variable to your API token
4. Deploy the stack

### 3. Or run locally with Docker

```bash
export RD_TOKEN=your_api_token_here
docker compose up -d
```

The web interface will be available at `http://localhost:8080` (or `http://rd-tool.local:8080` if proxied through NPM).

## Usage

### Web API

**Get user info:**
```bash
curl http://localhost:8080/api/user
```

**Unrestrict a link:**
```bash
curl -X POST http://localhost:8080/api/unrestrict/link \
  -H "Content-Type: application/json" \
  -d '{"link": "https://hoster.com/file123"}'
```

**Unrestrict and download:**
```bash
curl -X POST http://localhost:8080/api/unrestrict/download \
  -H "Content-Type: application/json" \
  -d '{"link": "https://hoster.com/file123"}'
```

**Add a magnet:**
```bash
curl -X POST http://localhost:8080/api/torrents/add \
  -H "Content-Type: application/json" \
  -d '{"magnet": "magnet:?xt=urn:btih:..."}'
```

**List torrents:**
```bash
curl http://localhost:8080/api/torrents
```

**Download files from a torrent:**
```bash
curl -X POST http://localhost:8080/api/torrents/{torrent_id}/download
```

**Check download progress:**
```bash
curl http://localhost:8080/downloads
curl http://localhost:8080/downloads/{download_id}
```

**List supported hosts:**
```bash
curl http://localhost:8080/api/hosts
```

### CLI Tool

Run the CLI tool inside the container:

```bash
docker exec -it rd-tool python rd_cli.py --help
```

Or set up an alias:

```bash
alias rd="docker exec -it rd-tool python rd_cli.py"
```

**Commands:**

```bash
# User info
rd user

# Check a link
rd check "https://hoster.com/file123"

# Unrestrict a link
rd unrestrict "https://hoster.com/file123"

# Unrestrict and download
rd unrestrict "https://hoster.com/file123" --download --output-dir /downloads

# Add a magnet
rd magnet "magnet:?xt=urn:btih:..."

# List torrents
rd torrents

# Get torrent info
rd torrent-info <torrent_id>

# List supported hosts
rd hosts

# Show traffic
rd traffic
```

## Configuration

All configuration via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RD_TOKEN` | - | Real-Debrid API token (required) |
| `RD_TOKEN_FILE` | - | Path to file containing token (alternative to RD_TOKEN) |
| `RD_DOWNLOAD_DIR` | `/downloads` | Directory for downloaded files |
| `RD_MAX_CONCURRENT_DOWNLOADS` | `3` | Max parallel downloads |
| `RD_HOST` | `0.0.0.0` | Server bind address |
| `RD_PORT` | `8080` | Server port |

## NAS Integration

To download directly to your NAS media share, uncomment the volume mount in `docker-compose.yml`:

```yaml
volumes:
  - /path/on/nas/Downloads:/downloads:rw
```

For your homelab, this could be:
```yaml
volumes:
  - /storage-pool/media/Downloads:/downloads:rw
```

## API Documentation

Full OpenAPI docs available at `http://localhost:8080/docs` (Swagger UI).

## Project Structure

```
debrid-automation/
├── app.py                 # FastAPI web interface
├── rd_api.py              # Real-Debrid API client
├── download_manager.py    # Download manager with progress tracking
├── config.py              # Configuration settings
├── rd_cli.py              # CLI tool
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image
├── docker-compose.yml     # Portainer stack
└── README.md              # This file
```

## Future Enhancements

- [ ] OAuth2 authentication flow (device code, website)
- [ ] Integration with *arr apps via Prowlarr custom indexer
- [ ] Scheduled downloads / watch folders
- [ ] Download queue with priority
- [ ] Web UI dashboard
