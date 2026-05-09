"""Download manager with progress tracking."""

import asyncio
import httpx
import logging
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime


logger = logging.getLogger("download_manager")


@dataclass
class DownloadProgress:
    """Track download progress."""
    filename: str
    total_size: int = 0
    downloaded: int = 0
    speed: float = 0.0  # bytes/sec
    eta_seconds: float = 0.0
    status: str = "downloading"  # downloading, completed, failed, cancelled
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def percentage(self) -> float:
        if self.total_size == 0:
            return 0.0
        return (self.downloaded / self.total_size) * 100

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "total_size": self.total_size,
            "downloaded": self.downloaded,
            "speed": self.speed,
            "eta_seconds": self.eta_seconds,
            "status": self.status,
            "error": self.error,
            "percentage": round(self.percentage, 2),
        }


class DownloadManager:
    """Manages concurrent downloads with progress tracking."""

    def __init__(self, output_dir: str = "/downloads", max_concurrent: int = 3):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_concurrent = max_concurrent
        self._downloads: dict[str, DownloadProgress] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def get_progress(self, download_id: str) -> Optional[DownloadProgress]:
        return self._downloads.get(download_id)

    def list_progress(self) -> dict[str, DownloadProgress]:
        return dict(self._downloads)

    async def download_file(
        self,
        url: str,
        filename: Optional[str] = None,
        password: Optional[str] = None,
    ) -> str:
        """Download a file and return the download ID."""
        download_id = f"dl_{int(datetime.now().timestamp())}_{os.urandom(4).hex()}"

        if filename is None:
            filename = url.split("/")[-1].split("?")[0] or download_id

        progress = DownloadProgress(
            filename=filename,
            status="queued",
            started_at=datetime.now(),
        )
        self._downloads[download_id] = progress

        # Store task reference to prevent GC
        task = asyncio.create_task(self._download(download_id, url, filename, password))
        self._tasks[download_id] = task
        task.add_done_callback(lambda t: self._tasks.pop(download_id, None))
        return download_id

    async def _download(
        self,
        download_id: str,
        url: str,
        filename: str,
        password: Optional[str],
    ):
        async with self._semaphore:
            progress = self._downloads[download_id]
            progress.status = "downloading"

            output_path = self.output_dir / filename

            headers = {}
            if password:
                headers["Authorization"] = f"Bearer {password}"

            logger.info(f"Starting download: {filename} → {output_path}")

            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
                    async with client.stream("GET", url, headers=headers) as response:
                        response.raise_for_status()

                        progress.total_size = int(response.headers.get("content-length", 0))
                        logger.info(f"File size: {progress.total_size / (1024**2):.1f}MB")

                        with open(output_path, "wb") as f:
                            last_update = datetime.now()
                            last_downloaded = 0

                            async for chunk in response.aiter_bytes(chunk_size=8192 * 16):
                                f.write(chunk)
                                progress.downloaded += len(chunk)

                                now = datetime.now()
                                elapsed = (now - last_update).total_seconds()
                                if elapsed >= 1.0:
                                    delta = progress.downloaded - last_downloaded
                                    progress.speed = delta / elapsed if elapsed > 0 else 0

                                    if progress.speed > 0 and progress.total_size > 0:
                                        remaining = progress.total_size - progress.downloaded
                                        progress.eta_seconds = remaining / progress.speed

                                    last_update = now
                                    last_downloaded = progress.downloaded

                progress.status = "completed"
                progress.completed_at = datetime.now()
                logger.info(f"Download completed: {output_path}")

            except Exception as e:
                progress.status = "failed"
                progress.error = str(e)
                logger.error(f"Download failed for {filename}: {e}")
                if output_path.exists():
                    output_path.unlink()

    async def cancel(self, download_id: str) -> bool:
        progress = self._downloads.get(download_id)
        if progress and progress.status == "downloading":
            progress.status = "cancelled"
            return True
        return False

    def cleanup_completed(self, older_than_seconds: float = 3600):
        """Remove completed downloads older than specified time."""
        now = datetime.now()
        to_remove = []
        for did, progress in self._downloads.items():
            if progress.completed_at and (now - progress.completed_at).total_seconds() > older_than_seconds:
                to_remove.append(did)
        for did in to_remove:
            del self._downloads[did]
