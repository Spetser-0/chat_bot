"""
tests/unit/test_docker_packaging.py
───────────────────────────────────
Lesson 12.6 — static validation of Docker/compose/CI artifacts.

Docker itself may be unavailable in the test environment; these tests
assert the files exist and the compose YAML is structurally correct so
CI fails early if someone breaks packaging.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# Repo root = two levels up from backend/tests/unit/
REPO_ROOT = Path(__file__).resolve().parents[3]


class TestDockerfilesExist:
    def test_backend_dockerfile(self):
        path = REPO_ROOT / "backend" / "Dockerfile"
        assert path.is_file(), "backend/Dockerfile missing"
        text = path.read_text(encoding="utf-8")
        assert "FROM python:" in text
        assert "USER app" in text or "USER " in text
        assert "uvicorn" in text
        assert "HEALTHCHECK" in text

    def test_frontend_dockerfile(self):
        path = REPO_ROOT / "frontend" / "Dockerfile"
        assert path.is_file(), "frontend/Dockerfile missing"
        text = path.read_text(encoding="utf-8")
        assert "FROM node:" in text
        assert "FROM nginx:" in text
        assert "npm run build" in text

    def test_nginx_conf(self):
        path = REPO_ROOT / "frontend" / "nginx.conf"
        assert path.is_file()
        text = path.read_text(encoding="utf-8")
        assert "location /api/" in text
        assert "try_files" in text

    def test_dockerignore_files(self):
        assert (REPO_ROOT / "backend" / ".dockerignore").is_file()
        assert (REPO_ROOT / "frontend" / ".dockerignore").is_file()


class TestDockerCompose:
    @pytest.fixture(scope="class")
    def compose(self) -> dict:
        path = REPO_ROOT / "docker-compose.yml"
        assert path.is_file(), "docker-compose.yml missing"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_required_services(self, compose):
        services = compose.get("services", {})
        for name in ("postgres", "redis", "backend", "frontend"):
            assert name in services, f"missing service: {name}"

    def test_backend_depends_on_db_and_redis(self, compose):
        deps = compose["services"]["backend"].get("depends_on", {})
        # depends_on may be list or mapping
        if isinstance(deps, dict):
            assert "postgres" in deps
            assert "redis" in deps
        else:
            assert "postgres" in deps
            assert "redis" in deps

    def test_postgres_not_publicly_exposed(self, compose):
        ports = compose["services"]["postgres"].get("ports", [])
        for p in ports:
            assert str(p).startswith("127.0.0.1:"), (
                f"postgres port {p} must bind to localhost only"
            )

    def test_volumes_declared(self, compose):
        vols = compose.get("volumes", {})
        assert "postgres_data" in vols
        assert "redis_data" in vols

    def test_backend_runs_migrations(self, compose):
        cmd = compose["services"]["backend"].get("command", "")
        assert "alembic upgrade head" in cmd
        assert "uvicorn" in cmd


class TestEnvExamples:
    def test_root_env_example(self):
        text = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        assert "POSTGRES_PASSWORD" in text

    def test_backend_env_has_redis_url(self):
        text = (REPO_ROOT / "backend" / ".env.example").read_text(encoding="utf-8")
        assert "REDIS_URL" in text
        assert "RATE_LIMIT_BACKEND" in text

    def test_frontend_env_example_exists(self):
        path = REPO_ROOT / "frontend" / ".env.example"
        assert path.is_file()
        assert "VITE_API_BASE_URL" in path.read_text(encoding="utf-8")


class TestCIWorkflow:
    def test_ci_workflow_exists_and_runs_tests(self):
        path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        assert path.is_file(), "CI workflow missing"
        text = path.read_text(encoding="utf-8")
        assert "backend-tests" in text
        assert "frontend-lint-build" in text
        assert "docker compose" in text or "docker-compose" in text
        assert "pytest" in text
        assert "npm run build" in text
