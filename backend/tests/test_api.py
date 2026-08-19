from fastapi.testclient import TestClient

from oqp_studio.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_desktop_launcher_degrades_without_pywebview(capsys):
    from oqp_studio import desktop

    # In environments without pywebview the launcher must explain itself
    # and exit cleanly instead of crashing.
    try:
        import webview  # noqa: F401

        has_webview = True
    except ImportError:
        has_webview = False

    if not has_webview:
        assert desktop.main() == 1
        assert "pywebview" in capsys.readouterr().out


def test_runners_listed():
    res = client.get("/api/runners")
    assert res.status_code == 200
    assert set(res.json()) >= {"pyoqp", "local", "wsl"}


def test_submit_without_openqp_fails_gracefully(tmp_path, monkeypatch):
    from oqp_studio import jobs

    monkeypatch.setattr(jobs, "JOBS_ROOT", tmp_path)
    res = client.post(
        "/api/jobs",
        json={"input_text": "[input]\nsystem=O 0 0 0\n", "runner": "local"},
    )
    assert res.status_code == 200
    job_id = res.json()["id"]

    import time

    for _ in range(50):
        info = client.get(f"/api/jobs/{job_id}").json()
        if info["status"] in ("done", "failed"):
            break
        time.sleep(0.1)
    # Without an OpenQP install the job must fail with a clear error,
    # never hang or crash the server.
    assert info["status"] in ("done", "failed")

    files = client.get(f"/api/jobs/{job_id}/files").json()
    names = {f["name"] for f in files}
    assert "input.oqp" in names

    res = client.get(f"/api/jobs/{job_id}/files/input.oqp")
    assert res.status_code == 200
    assert "system=O 0 0 0" in res.text

    # Path escapes must 404, not leak files outside the job directory.
    res = client.get(f"/api/jobs/{job_id}/files/..%2F..%2Fpyproject.toml")
    assert res.status_code == 404
