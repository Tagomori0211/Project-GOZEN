"""
Project GOZEN Web Interface

FastAPI + WebSocket による御前会議Web UI。
"""

from .server import create_app, start_server

__all__ = ["create_app", "start_server"]
