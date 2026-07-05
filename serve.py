#!/usr/bin/env python3
"""Small static server for local/NetBird use.

This intentionally serves only the public assets needed by index.html instead of
exposing the whole working tree. In particular, it does not serve .git, dotfiles,
.env files, editor backups, or directory listings.
"""

from __future__ import annotations

import argparse
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent

ALLOWED_FILES = {
    "/": ROOT / "index.html",
    "/index.html": ROOT / "index.html",
    "/favicon.ico": ROOT / "favicon.ico",
    "/complete-8.png": ROOT / "complete-8.png",
    "/assets/icons/favicon.ico": ROOT / "assets" / "icons" / "favicon.ico",
    "/assets/icons/favicon.png": ROOT / "assets" / "icons" / "favicon.png",
    "/roms/zeleste.gba": ROOT / "roms" / "zeleste.gba",
}

CONTENT_TYPES = {
    ".gba": "application/octet-stream",
}


class StaticHandler(BaseHTTPRequestHandler):
    server_version = "ZelesteStatic/1.0"
    sys_version = ""

    def do_GET(self) -> None:
        self._serve_file(send_body=True)

    def do_HEAD(self) -> None:
        self._serve_file(send_body=False)

    def _serve_file(self, *, send_body: bool) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        file_path = ALLOWED_FILES.get(path)

        if file_path is None:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        try:
            resolved = file_path.resolve(strict=True)
            resolved.relative_to(ROOT)
        except (FileNotFoundError, ValueError):
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        if not resolved.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        content_type = CONTENT_TYPES.get(resolved.suffix.lower())
        if content_type is None:
            content_type = (
                mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
            )

        data = resolved.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()

        if send_body:
            self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:
        # Keep the normal client/IP logging, but prefix it so it is easy to spot.
        super().log_message("[zeleste] " + format, *args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Zeleste static files safely")
    parser.add_argument("--host", default="0.0.0.0", help="Host/interface to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), StaticHandler)
    print(f"Serving {ROOT} on http://{args.host}:{args.port}/")
    print("Allowed paths: " + ", ".join(sorted(ALLOWED_FILES)))
    server.serve_forever()


if __name__ == "__main__":
    main()
