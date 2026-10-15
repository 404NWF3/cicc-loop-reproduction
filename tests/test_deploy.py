import pytest

from loop_research.config import Settings
from loop_research.deploy import main, validate_deployment


@pytest.fixture
def deployment(tmp_path, monkeypatch):
    for key in ("RAILWAY_SERVICE_ID", "RAILWAY_VOLUME_MOUNT_PATH", "PORT"):
        monkeypatch.delenv(key, raising=False)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>built app</html>")
    return Settings(
        _env_file=None,
        state_dir=tmp_path / "volume" / "runtime",
        data_dir=tmp_path / "volume" / "datasets",
        web_dist=dist,
        auth_required=True,
        auth_username="research",
        auth_password="test-only-long-password",
    )


@pytest.mark.parametrize("port", ["invalid", "0", "65536"])
def test_invalid_port_fails_before_startup(deployment, monkeypatch, port):
    monkeypatch.setenv("PORT", port)
    with pytest.raises(ValueError, match="PORT"):
        validate_deployment(deployment)


def test_railway_supplied_port_is_used(deployment, monkeypatch):
    monkeypatch.setenv("PORT", "8087")
    assert validate_deployment(deployment) == 8087


def test_missing_frontend_fails_before_startup(deployment):
    (deployment.web_dist / "index.html").unlink()
    with pytest.raises(ValueError, match="前端构建产物"):
        validate_deployment(deployment)


def test_railway_requires_volume_and_contained_data_directories(deployment, monkeypatch, tmp_path):
    monkeypatch.setenv("RAILWAY_SERVICE_ID", "test-service")
    with pytest.raises(ValueError, match="持久卷"):
        validate_deployment(deployment)
    volume = tmp_path / "volume"
    volume.mkdir()
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(volume))
    assert validate_deployment(deployment) == 8000
    deployment.data_dir = tmp_path / "ephemeral-data"
    with pytest.raises(ValueError, match="持久卷内"):
        validate_deployment(deployment)


def test_single_service_requires_its_worker(deployment):
    deployment.worker_autostart = False
    with pytest.raises(ValueError, match="WORKER_AUTOSTART"):
        validate_deployment(deployment)


def test_production_cannot_disable_auth_with_an_environment_variable(monkeypatch):
    monkeypatch.setenv("LOOP_AUTH_REQUIRED", "false")
    monkeypatch.setenv("LOOP_AUTH_USERNAME", "")
    monkeypatch.setenv("LOOP_AUTH_PASSWORD", "")
    with pytest.raises(SystemExit, match="LOOP_AUTH_USERNAME"):
        main()
