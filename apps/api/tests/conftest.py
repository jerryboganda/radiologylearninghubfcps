from __future__ import annotations

from apps.api.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
