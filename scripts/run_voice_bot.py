"""Standalone server entry point for AI Voice Bot."""

import argparse
import uvicorn
from config.settings import get_settings


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Launch uvicorn server for the Voice Bot application."""
    print(f"[*] Starting AI Voice Bot Server on {host}:{port}...")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    cfg = get_settings()
    parser = argparse.ArgumentParser(description="AI Voice Bot FastAPI Server")
    parser.add_argument("--host", default=cfg.websocket_host, help="Bind host")
    parser.add_argument("--port", type=int, default=cfg.websocket_port, help="Bind port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    start_server(host=args.host, port=args.port, reload=args.reload)
