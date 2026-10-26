import os
import pytest
from httpx import AsyncClient, ASGITransport

def test_frontend_dist_exists():
    dist_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
    assert os.path.exists(dist_dir), "frontend/dist should exist after build"
    assert os.path.exists(os.path.join(dist_dir, "index.html")), "index.html must exist in dist"

@pytest.mark.asyncio
async def test_serves_spa_index():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")
        assert resp.status_code == 200
        assert "Spotify Downloader Pro" in resp.text
