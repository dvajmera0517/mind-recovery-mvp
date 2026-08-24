#!/usr/bin/env python3
"""End-to-end MVP demo: the before/after drafting-and-review story.

Starts a throwaway server, renders all five companion pages exactly as
seeded (./output/before_review/), drafts sample content for the four
still-placeholder classes and runs them through a (simulated) reviewer
approval, re-renders all five companion pages (./output/after_review/),
and prints a before/after content_status comparison. This is the single
command to see the whole MVP flow — including drafting and review — work
end to end:

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
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mind_recovery_mvp.seed_data import NUTRIENT_CONTENT_SEED  # noqa: E402

OUTPUT_DIR = Path.cwd() / "output"
BEFORE_DIR = OUTPUT_DIR / "before_review"
AFTER_DIR = OUTPUT_DIR / "after_review"
# Derived from seed_data.py rather than hardcoded, so adding/removing a
# medication class there doesn't also require remembering to update this.
MEDICATION_CLASSES = [record["medication_class"] for record in NUTRIENT_CONTENT_SEED]
# Everything except metformin, which is already pharmacist-authored and
# was never part of the draft/review pipeline in the first place.
DRAFTABLE_CLASSES = [c for c in MEDICATION_CLASSES if c != "metformin"]
SERVER_STARTUP_TIMEOUT_SECONDS = 15
CONTENT_STATUS_DISPLAY_WIDTH = 42
# USDA's public, rate-limited testing key. Used only as a fallback when no
# FDC_API_KEY is configured, so this demo runs out of the box. Get a real
# key: https://fdc.nal.usda.gov/api-key-signup
USDA_DEMO_KEY = "DEMO_KEY"
# Explicitly NOT a real pharmacist — this demo runs the review step
# non-interactively (approving everything as-is) purely to show what the
# companion page looks like on the other side of a review. It stands in
# for a real review; it does not perform one.
DEMO_REVIEWER_NAME = "Demo Reviewer (not a licensed pharmacist)"

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


def _build_demo_env() -> dict[str, str]:
    """The environment shared by the server subprocess and the
    draft_content.py/review_content.py subprocesses — all three must
    agree on DATABASE_URL to operate on the same scratch DB file."""
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
    # reliably, so make sure every subprocess can import the package
    # regardless.
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{SRC_DIR}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(SRC_DIR)
    )
    return env


def _start_server(port: int, env: dict[str, str]) -> subprocess.Popen:
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


def _run_one(client: httpx.Client, medication_class: str, output_dir: Path) -> DemoResult:
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
        pdf_path = output_dir / f"{medication_class}.pdf"
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


def _render_all(client: httpx.Client, output_dir: Path) -> list[DemoResult]:
    output_dir.mkdir(parents=True, exist_ok=True)
    return [_run_one(client, mc, output_dir) for mc in MEDICATION_CLASSES]


def _run_subprocess_or_raise(
    args: list[str], env: dict[str, str], step_name: str, stdin_input: str | None = None
) -> str:
    result = subprocess.run(
        args,
        cwd=REPO_ROOT,
        env=env,
        input=stdin_input,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{step_name} failed (exit {result.returncode}):\n"
            f"{result.stdout}{result.stderr}"
        )
    return result.stdout


def _draft_sample_content(env: dict[str, str]) -> None:
    print(
        f"Drafting sample content for {', '.join(DRAFTABLE_CLASSES)} "
        "(default mode — no API key needed)..."
    )
    for medication_class in DRAFTABLE_CLASSES:
        _run_subprocess_or_raise(
            [sys.executable, str(REPO_ROOT / "scripts" / "draft_content.py"), medication_class],
            env,
            f"draft_content.py {medication_class}",
        )
        print(f"  drafted: {medication_class}")


def _review_all_drafts(env: dict[str, str]) -> None:
    banner = (
        f'DEMO REVIEW STEP — reviewer name: "{DEMO_REVIEWER_NAME}"\n'
        "    This is a stand-in for a real pharmacist review, run "
        "non-interactively for the demo — it does NOT perform an actual "
        "clinical review of this content."
    )
    print()
    print("!" * 78)
    print(banner)
    print("!" * 78)

    review_env = dict(env)
    review_env["REVIEWER_NAME"] = DEMO_REVIEWER_NAME
    # Approve every pending draft as-is, one "a" per draftable class.
    approve_all_input = "a\n" * len(DRAFTABLE_CLASSES)
    output = _run_subprocess_or_raise(
        [sys.executable, str(REPO_ROOT / "scripts" / "review_content.py")],
        review_env,
        "review_content.py",
        stdin_input=approve_all_input,
    )
    print(output)
    print("!" * 78)
    print(f'End of demo review step — reviewer was "{DEMO_REVIEWER_NAME}", not a real pharmacist.')
    print("!" * 78)


def _print_before_after_summary(
    before_results: list[DemoResult], after_results: list[DemoResult]
) -> None:
    def truncate(text: str, width: int) -> str:
        return text if len(text) <= width else text[: width - 1] + "…"

    before_by_class = {r.medication_class: r for r in before_results}
    after_by_class = {r.medication_class: r for r in after_results}

    class_width = max(len("Medication class"), *(len(c) for c in MEDICATION_CLASSES))
    status_width = CONTENT_STATUS_DISPLAY_WIDTH

    header = (
        f"{'Medication class'.ljust(class_width)}  "
        f"{'Before'.ljust(status_width)}  "
        f"{'After'.ljust(status_width)}"
    )
    print()
    print(header)
    print("-" * len(header))
    for medication_class in MEDICATION_CLASSES:
        before = truncate(before_by_class[medication_class].content_status, status_width)
        after = truncate(after_by_class[medication_class].content_status, status_width)
        print(
            f"{medication_class.ljust(class_width)}  "
            f"{before.ljust(status_width)}  "
            f"{after}"
        )
    print()


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    env = _build_demo_env()
    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    print(f"Starting demo server on {base_url} ...")
    server = _start_server(port, env)

    before_results: list[DemoResult] = []
    after_results: list[DemoResult] = []

    try:
        with httpx.Client(base_url=base_url) as client:
            _wait_for_health(client, server, SERVER_STARTUP_TIMEOUT_SECONDS)
            print("Server is up.")
            print()
            print(
                f"=== BEFORE: rendering all {len(MEDICATION_CLASSES)} companion "
                "pages exactly as originally seeded ==="
            )
            before_results = _render_all(client, BEFORE_DIR)

        print()
        _draft_sample_content(env)
        _review_all_drafts(env)

        with httpx.Client(base_url=base_url) as client:
            print()
            print(
                f"=== AFTER: re-rendering all {len(MEDICATION_CLASSES)} companion pages ==="
            )
            after_results = _render_all(client, AFTER_DIR)
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

    _print_before_after_summary(before_results, after_results)

    all_results = before_results + after_results
    pdf_success_count = sum(1 for r in all_results if r.pdf_rendered)
    print(
        f"{pdf_success_count}/{len(all_results)} companion-page PDFs "
        f"generated successfully ({len(MEDICATION_CLASSES)} classes x before/after)."
    )
    print(f"Before-review PDFs: {BEFORE_DIR}")
    print(f"After-review PDFs:  {AFTER_DIR}")

    return 0 if pdf_success_count == len(all_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
