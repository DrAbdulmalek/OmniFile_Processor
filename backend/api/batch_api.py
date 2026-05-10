#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backend/api/batch_api.py
=========================

FastAPI REST API for batch processing management.

Endpoints:
- POST   /api/batch              — Create a new batch
- GET    /api/batch              — List all batches
- GET    /api/batch/{id}         — Get batch details
- DELETE /api/batch/{id}         — Delete a batch
- POST   /api/batch/{id}/files   — Add files to batch
- POST   /api/batch/{id}/process — Start processing
- POST   /api/batch/{id}/retry   — Retry failed files
- GET    /api/batch/{id}/export  — Export results
- WS     /ws/batch/{id}          — Real-time progress
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/batch", tags=["batch"])

# ============================================================================
# Pydantic Models
# ============================================================================

class BatchConfigModel(BaseModel):
    ocr_engine: str = "trocr"
    language: str = "ar"
    quality: str = "medium"
    auto_correct: bool = True
    export_formats: list = ["txt", "json"]
    dpi: int = 300
    max_file_size_mb: int = 50

class CreateBatchRequest(BaseModel):
    name: str
    config: Optional[BatchConfigModel] = None
    created_by: str = "anonymous"

class AddFilesRequest(BaseModel):
    filepaths: list

class ExportRequest(BaseModel):
    format: str = "json"
    output_dir: Optional[str] = None


# ============================================================================
# WebSocket Manager
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, batch_id: str, websocket: WebSocket):
        await websocket.accept()
        if batch_id not in self.active_connections:
            self.active_connections[batch_id] = []
        self.active_connections[batch_id].append(websocket)

    def disconnect(self, batch_id: str, websocket: WebSocket):
        if batch_id in self.active_connections:
            self.active_connections[batch_id].remove(websocket)
            if not self.active_connections[batch_id]:
                del self.active_connections[batch_id]

    async def broadcast(self, batch_id: str, message: dict):
        if batch_id in self.active_connections:
            dead = []
            for ws in self.active_connections[batch_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(batch_id, ws)


ws_manager = ConnectionManager()

# ============================================================================
# Manager Instance (lazy)
# ============================================================================

_manager = None

def get_manager():
    global _manager
    if _manager is None:
        from backend.batch_manager import BatchManager
        _manager = BatchManager()
    return _manager


# ============================================================================
# REST Endpoints
# ============================================================================

@router.post("")
def create_batch(request: CreateBatchRequest):
    """Create a new processing batch."""
    manager = get_manager()
    config = None
    if request.config:
        from backend.batch_manager import BatchConfig
        config = BatchConfig(**request.config.model_dump())

    batch = manager.create_batch(
        name=request.name,
        config=config,
        created_by=request.created_by
    )
    return batch.to_dict()


@router.get("")
def list_batches(
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """List all batches."""
    manager = get_manager()
    return manager.list_batches(status=status)


@router.get("/{batch_id}")
def get_batch(batch_id: str):
    """Get batch details with stats."""
    manager = get_manager()
    batch = manager.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch.to_dict()


@router.delete("/{batch_id}")
def delete_batch(batch_id: str):
    """Delete a batch."""
    manager = get_manager()
    if not manager.delete_batch(batch_id):
        raise HTTPException(status_code=404, detail="Batch not found")
    return {"message": "Batch deleted"}


@router.post("/{batch_id}/files")
async def add_files(batch_id: str, files: list[UploadFile] = File(...)):
    """Upload and add files to a batch."""
    manager = get_manager()
    batch = manager.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    upload_dir = Path(manager.storage_dir) / "uploads" / batch_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    for file in files:
        filepath = upload_dir / file.filename
        content = await file.read()
        filepath.write_bytes(content)
        saved_paths.append(str(filepath))

    added = manager.add_files(batch_id, saved_paths)
    return {"message": f"Added {added} files", "batch_id": batch_id}


@router.post("/{batch_id}/process")
def process_batch(batch_id: str):
    """Start processing a batch (non-blocking)."""
    import threading
    manager = get_manager()

    batch = manager.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    # Progress callback for WebSocket
    async def ws_callback(file_id, progress, message):
        await ws_manager.broadcast(batch_id, {
            "type": "progress",
            "file_id": file_id,
            "progress": progress,
            "message": message,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z",
        })

    def run_processing():
        def sync_callback(file_id, progress, message):
            # Schedule async callback
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(ws_callback(file_id, progress, message))
                loop.close()
            except Exception:
                pass

        summary = manager.process_batch(batch_id, progress_callback=sync_callback)

        # Notify completion
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(ws_manager.broadcast(batch_id, {
                "type": "completed",
                "batch_id": batch_id,
                "summary": summary,
            }))
            loop.close()
        except Exception:
            pass

    thread = threading.Thread(target=run_processing, daemon=True)
    thread.start()

    return {"message": "Processing started", "batch_id": batch_id}


@router.post("/{batch_id}/retry")
def retry_failed(batch_id: str):
    """Retry all failed files."""
    manager = get_manager()
    try:
        result = manager.retry_failed(batch_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{batch_id}/export")
def export_results(batch_id: str, format: str = Query("json")):
    """Export batch results."""
    manager = get_manager()
    try:
        filepath = manager.export_results(batch_id, output_format=format)
        return FileResponse(filepath, filename=Path(filepath).name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@router.websocket("/ws/{batch_id}")
async def batch_websocket(websocket: WebSocket, batch_id: str):
    """Real-time progress updates via WebSocket."""
    await ws_manager.connect(batch_id, websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(batch_id, websocket)
