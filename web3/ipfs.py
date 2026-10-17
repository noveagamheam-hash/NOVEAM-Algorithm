
import os
import re
from dataclasses import dataclass
from urllib.parse import quote

import httpx


CID_PATTERN = re.compile(
    r"^(Qm[1-9A-HJ-NP-Za-km-z]{44}|"
    r"bafy[a-z2-7]{20,})$"
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "text/plain",
}


class IPFSError(Exception):
    """Raised when IPFS operations fail."""


@dataclass
class IPFSUploadResult:
    cid: str
    filename: str
    size: int
    gateway_url: str


class NoveamIPFS:
    """
    IPFS integration for NOVEAM.

    Requires an IPFS-compatible HTTP API endpoint
    that supports /api/v0/add.

    Intended for public, non-sensitive content only.
    """

    def __init__(self):
        self.api_url = os.getenv(
            "IPFS_API_URL", ""
        ).rstrip("/")

        self.gateway_url = os.getenv(
            "IPFS_GATEWAY_URL",
            "https://ipfs.io/ipfs"
        ).rstrip("/")

        self.api_token = os.getenv(
            "IPFS_API_TOKEN", ""
        )

        if not self.api_url:
            raise IPFSError(
                "IPFS_API_URL is not configured"
            )

        # Require HTTPS for remote providers.
        if not (
            self.api_url.startswith("https://")
            or self.api_url.startswith(
                "http://127.0.0.1:"
            )
            or self.api_url.startswith(
                "http://localhost:"
            )
        ):
            raise IPFSError(
                "IPFS API must use HTTPS or localhost"
            )

    def _headers(self):
        if self.api_token:
            return {
                "Authorization":
                    f"Bearer {self.api_token}"
            }
        return {}

    def get_gateway_url(self, cid: str) -> str:
        if not CID_PATTERN.fullmatch(cid):
            raise IPFSError("Invalid IPFS CID")

        return (
            f"{self.gateway_url}/"
            f"{quote(cid, safe='')}"
        )

    async def upload_bytes(
        self,
        data: bytes,
        filename: str,
        mime_type: str
    ) -> IPFSUploadResult:
        """
        Upload a public file to IPFS.
        """

        if not data:
            raise IPFSError("Empty files are not allowed")

        if len(data) > MAX_FILE_SIZE:
            raise IPFSError(
                "File exceeds 10 MB limit"
            )

        if mime_type not in ALLOWED_MIME_TYPES:
            raise IPFSError(
                "Unsupported file type"
            )

        if not filename or len(filename) > 150:
            raise IPFSError("Invalid filename")

        # Avoid path-based filenames.
        filename = os.path.basename(filename)

        files = {
            "file": (
                filename,
                data,
                mime_type
            )
        }

        params = {
            "pin": "true",
            "cid-version": "1"
        }

        try:
            async with httpx.AsyncClient(
                timeout=60,
                follow_redirects=False
            ) as client:

                response = await client.post(
                    f"{self.api_url}/api/v0/add",
                    params=params,
                    files=files,
                    headers=self._headers()
                )

                response.raise_for_status()

                # Kubo may return newline-delimited JSON.
                lines = response.text.strip().splitlines()
                result = response.json() if len(lines) == 1 else __import__(
                    "json"
                ).loads(lines[-1])

        except (
            httpx.HTTPError,
            ValueError
        ) as exc:
            raise IPFSError(
                "IPFS upload failed"
            ) from exc

        cid = result.get("Hash", "")

        if not CID_PATTERN.fullmatch(cid):
            raise IPFSError(
                "IPFS provider returned invalid CID"
            )

        return IPFSUploadResult(
            cid=cid,
            filename=filename,
            size=len(data),
            gateway_url=self.get_gateway_url(cid)
        )

    async def check_content(self, cid: str) -> bool:
        """
        Check whether content can be retrieved
        from the configured public gateway.
        """

        url = self.get_gateway_url(cid)

        try:
            async with httpx.AsyncClient(
                timeout=15,
                follow_redirects=False
            ) as client:
                response = await client.head(url)

                return response.status_code == 200

        except httpx.HTTPError:
            return False
