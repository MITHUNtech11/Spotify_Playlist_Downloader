import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_get_and_update_config():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "download_folder" in data
        assert "ffmpeg_available" in data
        assert "max_threads" in data

        # Test updating config
        update_resp = await ac.post("/api/config", json={"max_threads": 4})
        assert update_resp.status_code == 200
        assert update_resp.json()["max_threads"] == 4

@pytest.mark.asyncio
async def test_resolve_empty_or_invalid_url():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/resolve", json={"urls": ["https://invalid.com/track"]})
        assert resp.status_code == 200
        assert resp.json() == []

@pytest.mark.asyncio
async def test_usb_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/usb/drives")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
