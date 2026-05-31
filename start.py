"""VoiceLearn one-command launcher — starts backend + frontend together.

Usage:
    python start.py          # development mode (hot-reload)
    python start.py --prod   # production mode (single port 8000)
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    parser = argparse.ArgumentParser(description="VoiceLearn launcher")
    parser.add_argument(
        "--prod", action="store_true", help="Production mode (build frontend, single port)"
    )
    args = parser.parse_args()

    if args.prod:
        _run_prod()
    else:
        _run_dev()


def _run_dev() -> None:
    backend_dir = os.path.join(ROOT, "backend")
    frontend_dir = os.path.join(ROOT, "frontend")

    print("VoiceLearn 启动中 (开发模式)...")
    print("=" * 50)

    backend = subprocess.Popen(  # noqa: S603
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--reload", "--host", "127.0.0.1", "--port", "8000",
        ],
        cwd=backend_dir,
    )
    frontend = subprocess.Popen(  # noqa: S603
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        shell=os.name == "nt",
    )

    print("后端:  http://127.0.0.1:8000")
    print("前端:  http://localhost:5173")
    print("按 Ctrl+C 停止所有服务")

    def _shutdown(*_args: object) -> None:
        print("\n正在停止...")
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(backend.pid)],  # noqa: S603,S607
                capture_output=True,
            )
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(frontend.pid)],  # noqa: S603,S607
                capture_output=True,
            )
        else:
            backend.terminate()
            frontend.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _shutdown()


def _run_prod() -> None:
    frontend_dir = os.path.join(ROOT, "frontend")
    backend_dir = os.path.join(ROOT, "backend")

    print("VoiceLearn 启动中 (生产模式)...")
    print("=" * 50)

    print("构建前端...")
    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True, shell=os.name == "nt")  # noqa: S603

    print("启动服务...")
    print("打开 http://127.0.0.1:8000")
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=backend_dir,
    )


if __name__ == "__main__":
    main()
