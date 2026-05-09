"""FastAPI web interface for Real-Debrid automation."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional

from config import settings
from rd_api import RealDebridClient, RealDebridError
from download_manager import DownloadManager


# Global instances
rd_client: Optional[RealDebridClient] = None
download_manager: Optional[DownloadManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rd_client, download_manager

    settings.validate()

    rd_client = RealDebridClient(settings.get_token())
    download_manager = DownloadManager(
        output_dir=settings.download_dir,
        max_concurrent=settings.max_concurrent_downloads,
    )

    yield

    if rd_client:
        await rd_client.close()


app = FastAPI(title="Real-Debrid Automation", lifespan=lifespan)


# Request/Response Models

class UnrestrictRequest(BaseModel):
    link: str
    password: Optional[str] = None


class TorrentRequest(BaseModel):
    magnet: Optional[str] = None
    torrent_file: Optional[str] = None  # Base64 encoded
    select_files: Optional[str] = "all"  # "all" or comma-separated IDs


class DownloadRequest(BaseModel):
    url: str
    filename: Optional[str] = None
    password: Optional[str] = None


# User endpoints

@app.get("/api/user")
async def get_user():
    """Get current user info."""
    try:
        return await rd_client.get_user()
    except RealDebridError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Unrestrict endpoints

@app.post("/api/unrestrict/check")
async def check_link(req: UnrestrictRequest):
    """Check if a link is supported."""
    try:
        return await rd_client.check_link(req.link)
    except RealDebridError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/unrestrict/link")
async def unrestrict_link(req: UnrestrictRequest):
    """Unrestrict a link and return download URL."""
    try:
        result = await rd_client.unrestrict_link(req.link, req.password)
        return result
    except RealDebridError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/unrestrict/download")
async def unrestrict_and_download(req: UnrestrictRequest, background_tasks: BackgroundTasks):
    """Unrestrict a link and start downloading the file."""
    try:
        # Unrestrict the link
        result = await rd_client.unrestrict_link(req.link, req.password)

        # Start download
        download_url = result.get("download")
        if not download_url:
            raise HTTPException(status_code=400, detail="No download URL returned")

        filename = result.get("filename", "unknown")
        download_id = await download_manager.download_file(download_url, filename, req.password)

        return {"download_id": download_id, "filename": filename, "url": download_url}
    except RealDebridError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Torrent endpoints

@app.get("/api/torrents")
async def list_torrents(limit: int = 100):
    """List user torrents."""
    try:
        return await rd_client.list_torrents(limit)
    except RealDebridError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/torrents/add")
async def add_torrent(req: TorrentRequest):
    """Add a magnet link or torrent file."""
    try:
        if req.magnet:
            result = await rd_client.add_magnet(req.magnet)
        elif req.torrent_file:
            import base64
            torrent_bytes = base64.b64decode(req.torrent_file)
            result = await rd_client.add_torrent_file(torrent_bytes)
        else:
            raise HTTPException(status_code=400, detail="Either magnet or torrent_file required")

        # Select files if specified
        torrent_id = result.get("id")
        if torrent_id and req.select_files:
            await rd_client.select_files(torrent_id, req.select_files)

        return result
    except RealDebridError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/torrents/{torrent_id}")
async def get_torrent_info(torrent_id: str):
    """Get torrent info."""
    try:
        return await rd_client.get_torrent_info(torrent_id)
    except RealDebridError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/torrents/{torrent_id}/download")
async def download_torrent_files(torrent_id: str, background_tasks: BackgroundTasks):
    """
    Download all files from a torrent.
    First gets torrent info, then starts downloads for each file.
    """
    try:
        info = await rd_client.get_torrent_info(torrent_id)
        links = info.get("links", [])

        if not links:
            raise HTTPException(status_code=400, detail="No downloadable links found")

        download_ids = []
        for i, url in enumerate(links):
            filename = info.get("files", [{}])[i].get("path", f"file_{i}")
            download_id = await download_manager.download_file(url, filename)
            download_ids.append(download_id)

        return {"download_ids": download_ids, "count": len(download_ids)}
    except RealDebridError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Download endpoints

@app.get("/api/downloads")
async def list_downloads():
    """List all active downloads with progress."""
    progress = download_manager.list_progress()
    return {did: p.to_dict() for did, p in progress.items()}


@app.get("/api/downloads/{download_id}")
async def get_download_progress(download_id: str):
    """Get progress for a specific download."""
    progress = download_manager.get_progress(download_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Download not found")
    return progress.to_dict()


@app.post("/api/downloads/{download_id}/cancel")
async def cancel_download(download_id: str):
    """Cancel a download."""
    result = await download_manager.cancel(download_id)
    if not result:
        raise HTTPException(status_code=400, detail="Cannot cancel download")
    return {"status": "cancelled"}


# Hosts endpoints

@app.get("/api/hosts")
async def list_hosts():
    """List supported hosts."""
    try:
        return await rd_client.get_hosts()
    except RealDebridError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/hosts/status")
async def hosts_status():
    """Get hoster status."""
    try:
        return await rd_client.get_hosts_status()
    except RealDebridError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Traffic endpoints

@app.get("/api/traffic")
async def get_traffic():
    """Get traffic info."""
    try:
        return await rd_client.get_traffic()
    except RealDebridError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Health check

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}
