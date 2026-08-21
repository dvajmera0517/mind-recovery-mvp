#!/usr/bin/env python3
"""End-to-end MVP demo.

Starts a throwaway server, fires /fill-event for all four seeded medication
classes in sequence, downloads each companion-page PDF into ./output, and
prints a summary table. This is the single command to see the whole MVP
flow work end to end:

    python scripts/demo.py
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
OUTPUT_DIR = Path.cwd() / "output"
MEDICATION_CLASSES = ["metformin", "statins", "diuretics", "ppi"]
SERVER_STARTUP_TIMEOUT_SECONDS = 15
CONTENT_STATUS_DISPLAY_WIDTH = 50
# USDA's public, rate-limited testing key. Used only as a fallback when no
# FDC_API_KEY is configured, so this demo runs out of the box. Get a real
# key: https://fdc.nal.usda.gov/api-key-signup
USDA_DEMO_KEY = "DEMO_KEY"

load_dotenv(REPO_ROOT / ".env")


@dataclass
class DemoResult:
    medication_class: str
    content_status: str
    pdf_rendered: bool
    detail: str = ""


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_health(
    client: httpx.Client, server: subprocess.Popen, timeout: float
) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if server.poll() is not None:
            output = server.stdout.read() if server.stdout is not None else ""
            raise RuntimeError(
                f"Server process exited early (code {server.returncode}) "
                f"during startup:\n{output}"
            )
        try:
            response = client.get("/health", timeout=2)
            if response.status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(0.3)
    raise RuntimeError(f"Server did not become healthy in time: {last_error}")


def _start_server(port: int) -> subprocess.Popen:
    env = os.environ.copy()
    # Use a scratch DB so the demo never touches a real dev DB file, and
    # is repeatable (fresh data every run).
    demo_db_path = OUTPUT_DIR / "demo.db"
    demo_db_path.unlink(missing_ok=True)
    env["DATABASE_URL"] = f"sqlite:///{demo_db_path}"
    # The server fails fast at startup without FDC_API_KEY. Fall back to
    # USDA's public demo key so this script still runs with zero setup.
    if not env.get("FDC_API_KEY"):
        print(
            "No FDC_API_KEY found (env var or .env) — using USDA's public "
            "DEMO_KEY (rate-limited). Get your own free key: "
            "https://fdc.nal.usda.gov/api-key-signup"
        )
        env["FDC_API_KEY"] = USDA_DEMO_KEY
    # Belt-and-suspenders: some shells don't pick up editable installs
    # reliably, so make sure the subprocess can import the package
    # regardless.
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{SRC_DIR}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(SRC_DIR)
    )

    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "mind_recovery_mvp.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _run_one(client: httpx.Client, medication_class: str) -> DemoResult:
    fill_response = client.post(
        "/fill-event", json={"medication_class": medication_class}
    )
    if fill_response.status_code != 200:
        return DemoResult(
            medication_class=medication_class,
            content_status="(unavailable)",
            pdf_rendered=False,
            detail=f"/fill-event returned HTTP {fill_response.status_code}",
        )
    content_status = fill_response.json()["content_status"]

    pdf_response = client.get(f"/companion-page/{medication_class}.pdf")
    pdf_ok = (
        pdf_response.status_code == 200
        and pdf_response.headers.get("content-type") == "application/pdf"
        and pdf_response.content.startswith(b"%PDF")
    )
    detail = ""
    if pdf_ok:
        pdf_path = OUTPUT_DIR / f"{medication_class}.pdf"
        pdf_path.write_bytes(pdf_response.content)
        detail = f"saved to {pdf_path.relative_to(Path.cwd())}"
    else:
        detail = f"/companion-page/{medication_class}.pdf returned HTTP {pdf_response.status_code}"

    return DemoResult(
        medication_class=medication_class,
        content_status=content_status,
        pdf_rendered=pdf_ok,
        detail=detail,
    )


def _print_summary(results: list[DemoResult]) -> None:
    def truncate(text: str, width: int) -> str:
        return text if len(text) <= width else text[: width - 1] + "…"

    class_width = max(len("Medication class"), *(len(r.medication_class) for r in results))
    status_width = CONTENT_STATUS_DISPLAY_WIDTH
    rendered_width = len("PDF rendered")

    header = (
        f"{'Medication class'.ljust(class_width)}  "
        f"{'Content status'.ljust(status_width)}  "
        f"{'PDF rendered'.ljust(rendered_width)}"
    )
    print()
    print(header)
    print("-" * len(header))
    for result in results:
        rendered = "yes" if result.pdf_rendered else "NO"
        print(
            f"{result.medication_class.ljust(class_width)}  "
            f"{truncate(result.content_status, status_width).ljust(status_width)}  "
            f"{rendered.ljust(rendered_width)}"
        )
        if not result.pdf_rendered:
            print(f"{' ' * class_width}  -> {result.detail}")
    print()


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    print(f"Starting demo server on {base_url} ...")
    server = _start_server(port)
    results: list[DemoResult] = []

    try:
        with httpx.Client(base_url=base_url) as client:
            _wait_for_health(client, server, SERVER_STARTUP_TIMEOUT_SECONDS)
            print("Server is up. Running fill-event + companion-page for each class...")
            for medication_class in MEDICATION_CLASSES:
                results.append(_run_one(client, medication_class))
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
        if server.stdout is not None and server.returncode not in (0, None, -15):
            print("--- server output (non-clean shutdown) ---")
            print(server.stdout.read())

    _print_summary(results)
    print(f"PDFs saved under {OUTPUT_DIR}")

    return 0 if all(r.pdf_rendered for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
