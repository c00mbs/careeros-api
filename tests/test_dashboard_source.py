"""Static safety checks for the dashboard entrypoint."""

import ast
from pathlib import Path


def test_dashboard_entrypoint_is_valid_python() -> None:
    source = Path(__file__).resolve().parents[1] / "dashboard.py"
    ast.parse(source.read_text(encoding="utf-8"), filename=str(source))


def test_dashboard_uses_existing_authenticated_api_routes() -> None:
    source = (Path(__file__).resolve().parents[1] / "dashboard.py").read_text(encoding="utf-8")
    for route in (
        "/auth/register",
        "/auth/login",
        "/me",
        "/career-summary",
        "/applications",
        "/skills",
        "/career-timeline",
        "/career-dna",
    ):
        assert route in source
