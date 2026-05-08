"""Real-Debrid API client."""

import httpx
from typing import Optional
from datetime import datetime


class RealDebridError(Exception):
    """Base exception for Real-Debrid API errors."""
    pass


class RealDebridClient:
    """Client for the Real-brid REST API."""

    BASE_URL = "https://api.real-debrid.com/rest/1.0"

    def __init__(self, token: str, timeout: float = 30.0):
        self.token = token
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=self.timeout,
            headers={"Authorization": f"Bearer {token}"},
        )

    async def close(self):
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make an API request and return JSON response."""
        response = await self._client.request(method, path, **kwargs)

        if response.status_code == 401:
            raise RealDebridError("Authentication failed. Check your API token.")
        elif response.status_code == 429:
            raise RealDebridError("Rate limit exceeded (250 req/min). Try again later.")
        elif response.status_code >= 400:
            error_data = response.json()
            error_msg = error_data.get("error", "Unknown error")
            error_code = error_data.get("error_code")
            raise RealDebridError(f"API error {error_code}: {error_msg}")

        return response.json()

    # User
    async def get_user(self) -> dict:
        """Get current user info."""
        return await self._request("GET", "/user")

    # Unrestrict
    async def check_link(self, link: str) -> dict:
        """Check if a link is supported and available."""
        return await self._request("POST", "/unrestrict/check", data={"link": link})

    async def unrestrict_link(self, link: str, password: Optional[str] = None) -> dict:
        """Unrestrict a single link."""
        data = {"link": link}
        if password:
            data["password"] = password
        return await self._request("POST", "/unrestrict/link", data=data)

    async def unrestrict_folder(self, link: str) -> dict:
        """Unrestrict a folder link."""
        return await self._request("POST", "/unrestrict/folder", data={"link": link})

    # Torrents
    async def list_torrents(self, limit: int = 100) -> list[dict]:
        """Get user torrents list."""
        return await self._request("GET", f"/torrents?limit={limit}")

    async def get_torrent_info(self, torrent_id: str) -> dict:
        """Get info on a specific torrent."""
        return await self._request("GET", f"/torrents/info/{torrent_id}")

    async def get_active_count(self) -> dict:
        """Get currently active torrents number."""
        return await self._request("GET", "/torrents/activeCount")

    async def add_magnet(self, magnet: str) -> dict:
        """Add a magnet link."""
        return await self._request("POST", "/torrents/addMagnet", data={"magnet": magnet})

    async def add_torrent_file(self, torrent_file: bytes) -> dict:
        """Add a torrent file."""
        return await self._request("PUT", "/torrents/addTorrent", files={"file": torrent_file})

    async def select_files(self, torrent_id: str, files: str) -> dict:
        """
        Select files from a torrent.
        files: comma-separated list of file IDs, or "all"
        """
        return await self._request("POST", f"/torrents/selectFiles/{torrent_id}", data={"files": files})

    async def delete_torrent(self, torrent_id: str) -> dict:
        """Delete a torrent."""
        return await self._request("DELETE", f"/torrents/delete/{torrent_id}")

    # Downloads
    async def list_downloads(self) -> list[dict]:
        """Get user downloads list."""
        return await self._request("GET", "/downloads")

    async def delete_download(self, download_id: str) -> dict:
        """Delete a download."""
        return await self._request("DELETE", f"/downloads/delete/{download_id}")

    # Hosts
    async def get_hosts(self) -> list[str]:
        """Get supported hosts."""
        return await self._request("GET", "/hosts")

    async def get_hosts_status(self) -> list[dict]:
        """Get status of hosters."""
        return await self._request("GET", "/hosts/status")

    # Traffic
    async def get_traffic(self) -> dict:
        """Get traffic info for limited hosters."""
        return await self._request("GET", "/traffic")

    async def get_traffic_details(self) -> dict:
        """Get traffic details on used hosters."""
        return await self._request("GET", "/traffic/details")

    # Streaming
    async def get_transcode_links(self, file_id: str) -> dict:
        """Get transcoding links for a file."""
        return await self._request("GET", f"/streaming/transcode/{file_id}")

    async def get_media_info(self, file_id: str) -> dict:
        """Get media info for a file."""
        return await self._request("GET", f"/streaming/mediaInfos/{file_id}")
