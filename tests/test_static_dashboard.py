from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecommerce.api import mount_dashboard


def test_optional_static_dashboard(tmp_path: Path) -> None:
    application = FastAPI()
    mount_dashboard(application, tmp_path)
    with TestClient(application) as client:
        assert client.get("/").status_code == 404

    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "index-test.js").write_text("console.log('test');", encoding="utf-8")
    (tmp_path / "index.html").write_text("<html>Commerce Intelligence</html>", encoding="utf-8")
    (tmp_path / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
    mount_dashboard(application, tmp_path)

    with TestClient(application) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert home.headers["cache-control"] == "no-cache"
        assert "Commerce Intelligence" in home.text
        assert client.get("/assets/index-test.js").status_code == 200
        assert client.get("/favicon.svg").headers["content-type"] == "image/svg+xml"
        assert client.get("/docs").status_code == 200
        assert client.get("/openapi.json").json()["paths"] == {}
        assert client.get("/api/v1/unknown").json() == {"detail": "Not Found"}
        assert client.get("/assets/missing.js").status_code == 404
