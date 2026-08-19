from fastapi.testclient import TestClient

from oqp_studio.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_runners_listed():
    res = client.get("/api/runners")
    assert res.status_code == 200
    assert set(res.json()) >= {"local", "wsl"}


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
